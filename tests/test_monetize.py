"""Tests for the tape_to_cloud.monetize module."""

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from tape_to_cloud.monetize import (
    AccessPolicyError,
    LicenseStore,
    LicenseTag,
    LicenseValidationError,
    PolicyStore,
    RateCard,
    RoyaltyError,
    UsageLedger,
    compute_royalty_report,
    generate_access_policy,
    is_policy_active,
    render_aws_s3_policy,
    render_report_summary,
)
from tape_to_cloud.monetize._audit import read_audit_log
from tape_to_cloud.monetize.cli import main as cli_main

REPO_ROOT = Path(__file__).resolve().parents[1]
SHA = "a" * 64
FUTURE = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
PAST = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()


def make_tag(**overrides):
    defaults = dict(
        asset_id="tape-0001/file-42",
        license_id="COMM-2026-001",
        license_class="commercially-licensable",
        rights=("train", "distribute"),
        territory="worldwide",
        expires_at=FUTURE,
        attribution_required=True,
        source_manifest_sha256=SHA,
        licensor_id="acme-media",
    )
    defaults.update(overrides)
    return LicenseTag(**defaults)


class TestLicenseTagValidation:
    def test_valid_tag_passes(self):
        assert make_tag().validate() is not None

    def test_empty_asset_id_rejected(self):
        with pytest.raises(LicenseValidationError):
            make_tag(asset_id="").validate()

    def test_unknown_license_class_rejected(self):
        with pytest.raises(LicenseValidationError):
            make_tag(license_class="public-domainish").validate()

    def test_bad_sha256_rejected(self):
        with pytest.raises(LicenseValidationError):
            make_tag(source_manifest_sha256="zz").validate()

    def test_naive_expiry_rejected(self):
        with pytest.raises(LicenseValidationError):
            make_tag(expires_at="2030-01-01T00:00:00").validate()

    def test_perpetual_expiry_allowed(self):
        tag = make_tag(expires_at=None).validate()
        assert not tag.is_expired()

    def test_commercial_tag_requires_rights(self):
        with pytest.raises(LicenseValidationError):
            make_tag(rights=()).validate()

    def test_expired_tag_detected(self):
        assert make_tag(expires_at=PAST).is_expired()


class TestLicenseStore:
    def test_round_trip_persistence(self, tmp_path):
        store = LicenseStore(tmp_path)
        tag = make_tag()
        store.add_tag(tag)
        reloaded = LicenseStore(tmp_path).load_tags()
        assert reloaded == [tag]

    def test_append_preserves_existing_tags(self, tmp_path):
        store = LicenseStore(tmp_path)
        t1 = make_tag(asset_id="asset-a")
        t2 = make_tag(asset_id="asset-b", license_class="restricted", rights=())
        store.add_tag(t1)
        store.add_tag(t2)
        assert set(t.asset_id for t in store.load_tags()) == {"asset-a", "asset-b"}

    def test_deterministic_serialization(self, tmp_path):
        store = LicenseStore(tmp_path)
        tag = make_tag()
        store.add_tag(tag)
        first = store.manifest_path.read_bytes()
        store._write(store.load_tags())
        assert store.manifest_path.read_bytes() == first

    def test_invalid_tag_not_persisted(self, tmp_path):
        store = LicenseStore(tmp_path)
        with pytest.raises(LicenseValidationError):
            store.add_tag(make_tag(license_id=""))
        assert store.load_tags() == []

    def test_query_by_license_class(self, tmp_path):
        store = LicenseStore(tmp_path)
        store.add_tag(make_tag(asset_id="a1"))
        store.add_tag(make_tag(asset_id="a2", license_class="restricted", rights=()))
        store.add_tag(make_tag(asset_id="a3", license_class="unknown", rights=()))
        commercial = store.query_by_class("commercially-licensable")
        assert [t.asset_id for t in commercial] == ["a1"]
        assert [t.asset_id for t in store.query_by_class("restricted")] == ["a2"]
        with pytest.raises(LicenseValidationError):
            store.query_by_class("nope")

    def test_add_tag_appends_audit_line(self, tmp_path):
        store = LicenseStore(tmp_path)
        store.add_tag(make_tag(), actor="tester")
        entries = read_audit_log(tmp_path)
        assert len(entries) == 1
        assert entries[0]["action"] == "license.tag"
        assert entries[0]["actor"] == "tester"
        assert len(entries[0]["sha256"]) == 64


class TestAccessPolicy:
    def test_policy_requires_kms_key(self):
        with pytest.raises(AccessPolicyError, match="KMS"):
            generate_access_policy(make_tag(), consumer_id="cust-1", kms_key_id="")

    def test_policy_scopes_prefixes_and_embeds_conditions(self):
        tag = make_tag()
        policy = generate_access_policy(
            tag,
            consumer_id="cust-1",
            kms_key_id="arn:aws:kms:us-east-1:111122223333:key/abc",
            asset_prefixes=["migrated/tape-0001/", "proxies/tape-0001/"],
        )
        assert policy["asset_prefixes"] == ["migrated/tape-0001/", "proxies/tape-0001/"]
        assert policy["conditions"]["license_id"] == tag.license_id
        assert policy["conditions"]["expires_at"] == tag.expires_at
        assert policy["conditions"]["require_customer_kms_key"].endswith("key/abc")
        assert policy["status"] == "active"

    def test_default_prefix_derived_from_asset(self):
        policy = generate_access_policy(make_tag(), "cust-1", "kms-key-1")
        assert policy["asset_prefixes"] == [f"assets/{make_tag().asset_id}/"]

    def test_expired_license_refused(self):
        with pytest.raises(AccessPolicyError, match="expired"):
            generate_access_policy(make_tag(expires_at=PAST), "cust-1", "kms-key-1")

    def test_aws_rendering(self):
        tag = make_tag()
        policy = generate_access_policy(tag, "cust-1", "kms-key-1")
        rendered = render_aws_s3_policy(policy, bucket="training-bucket")
        stmt = rendered["Statement"][0]
        assert stmt["Resource"] == [
            f"arn:aws:s3:::training-bucket/assets/{tag.asset_id}/*"
        ]
        cond = stmt["Condition"]
        assert cond["StringEquals"]["s3:x-amz-server-side-encryption-aws-kms-key-id"] == "kms-key-1"
        assert cond["DateLessThan"]["aws:CurrentTime"] == tag.expires_at

    def test_expiry_based_revocation(self):
        policy = generate_access_policy(make_tag(), "cust-1", "kms-key-1")
        assert is_policy_active(policy)
        after_expiry = datetime.now(timezone.utc) + timedelta(days=400)
        assert not is_policy_active(policy, now=after_expiry)

    def test_explicit_revocation(self, tmp_path):
        policies = PolicyStore(tmp_path)
        policy = policies.issue(make_tag(), "cust-1", "kms-key-1")
        assert is_policy_active(policy)
        revoked = policies.revoke(policy["policy_id"], reason="contract terminated")
        assert revoked["status"] == "revoked"
        assert revoked["revocation_reason"] == "contract terminated"
        assert not is_policy_active(policies.get(policy["policy_id"]))
        with pytest.raises(AccessPolicyError):
            policies.revoke(policy["policy_id"])
        with pytest.raises(AccessPolicyError):
            policies.revoke("no-such-policy")

    def test_issue_and_revoke_audited(self, tmp_path):
        policies = PolicyStore(tmp_path)
        policy = policies.issue(make_tag(), "cust-1", "kms-key-1")
        policies.revoke(policy["policy_id"])
        actions = [e["action"] for e in read_audit_log(tmp_path)]
        assert actions == ["policy.issue", "policy.revoke"]


class TestRoyalties:
    START = "2026-01-01T00:00:00+00:00"
    END = "2026-02-01T00:00:00+00:00"

    def seeded_store(self, tmp_path):
        licenses = LicenseStore(tmp_path)
        licenses.add_tag(make_tag(asset_id="asset-gb", license_id="LIC-GB",
                                  licensor_id="licensor-1"))
        licenses.add_tag(make_tag(asset_id="asset-req", license_id="LIC-REQ",
                                  licensor_id="licensor-1"))
        licenses.add_tag(make_tag(asset_id="asset-flat", license_id="LIC-FLAT",
                                  licensor_id="licensor-2"))
        ledger = UsageLedger(tmp_path)
        ledger.record("asset-gb", "cust-1", bytes_transferred=5_000_000_000,
                      requests=3, timestamp="2026-01-10T12:00:00+00:00")
        ledger.record("asset-req", "cust-1", bytes_transferred=10, requests=250,
                      timestamp="2026-01-11T12:00:00+00:00")
        ledger.record("asset-flat", "cust-2", bytes_transferred=999, requests=1,
                      timestamp="2026-01-12T12:00:00+00:00")
        return licenses, ledger

    def rate_cards(self):
        return [
            RateCard("LIC-GB", "per_gb", Decimal("0.25")),
            RateCard("LIC-REQ", "per_request", Decimal("0.01")),
            RateCard("LIC-FLAT", "flat", Decimal("100.00")),
        ]

    def test_ledger_append_only_jsonl(self, tmp_path):
        ledger = UsageLedger(tmp_path)
        ledger.record("a", "c", bytes_transferred=1, requests=1)
        ledger.record("a", "c", bytes_transferred=2, requests=2)
        lines = ledger.ledger_path.read_text().strip().splitlines()
        assert len(lines) == 2
        assert json.loads(lines[0])["bytes"] == 1
        actions = [e["action"] for e in read_audit_log(tmp_path)]
        assert actions == ["usage.record", "usage.record"]

    def test_period_filtering(self, tmp_path):
        _, ledger = self.seeded_store(tmp_path)
        ledger.record("asset-gb", "cust-1", bytes_transferred=1,
                      timestamp="2026-03-01T00:00:00+00:00")
        events = ledger.read_events(self.START, self.END)
        assert len(events) == 3

    def test_per_gb_per_request_and_flat_rates(self, tmp_path):
        licenses, ledger = self.seeded_store(tmp_path)
        report = compute_royalty_report(
            ledger, licenses, self.rate_cards(), self.START, self.END
        )
        lic1 = report["licensors"]["licensor-1"]["licenses"]
        assert lic1["LIC-GB"]["amount"] == "1.25"
        assert lic1["LIC-REQ"]["amount"] == "2.50"
        lic2 = report["licensors"]["licensor-2"]["licenses"]
        assert lic2["LIC-FLAT"]["amount"] == "100.00"
        assert report["licensors"]["licensor-1"]["total_amount"] == "3.75"
        assert report["total_amount"] == "103.75"
        assert report["unpriced_events"] == 0

    def test_untagged_assets_reported_unpriced(self, tmp_path):
        licenses, ledger = self.seeded_store(tmp_path)
        ledger.record("mystery-asset", "cust-9", bytes_transferred=1,
                      timestamp="2026-01-15T00:00:00+00:00")
        report = compute_royalty_report(
            ledger, licenses, self.rate_cards(), self.START, self.END
        )
        assert report["unpriced_events"] == 1
        assert report["total_amount"] == "103.75"

    def test_rendered_summary(self, tmp_path):
        licenses, ledger = self.seeded_store(tmp_path)
        report = compute_royalty_report(
            ledger, licenses, self.rate_cards(), self.START, self.END
        )
        summary = render_report_summary(report)
        assert "licensor-1" in summary
        assert "TOTAL: 103.75 USD" in summary

    def test_rate_card_validation(self):
        with pytest.raises(RoyaltyError):
            RateCard("L", "per_terabyte", Decimal("1")).validate()
        with pytest.raises(RoyaltyError):
            RateCard("L", "flat", Decimal("-1")).validate()

    def test_negative_usage_rejected(self, tmp_path):
        with pytest.raises(RoyaltyError):
            UsageLedger(tmp_path).record("a", "c", bytes_transferred=-1)


class TestCli:
    def run(self, tmp_path, *argv, capsys=None):
        rc = cli_main(["--store", str(tmp_path), *argv])
        out = capsys.readouterr().out if capsys else ""
        return rc, out

    def test_cli_end_to_end(self, tmp_path, capsys):
        rc, _ = self.run(
            tmp_path, "tag",
            "--asset-id", "asset-1", "--license-id", "LIC-1",
            "--license-class", "commercially-licensable",
            "--right", "train", "--territory", "EU",
            "--expires-at", FUTURE, "--manifest-sha256", SHA,
            "--licensor-id", "licensor-x",
            capsys=capsys,
        )
        assert rc == 0

        rc, out = self.run(tmp_path, "list", "--license-class",
                           "commercially-licensable", capsys=capsys)
        assert rc == 0
        assert [t["asset_id"] for t in json.loads(out)] == ["asset-1"]

        rc, out = self.run(
            tmp_path, "policy",
            "--asset-id", "asset-1", "--consumer-id", "cust-1",
            "--kms-key-id", "kms-key-1", "--prefix", "migrated/asset-1/",
            capsys=capsys,
        )
        assert rc == 0
        policy = json.loads(out)
        assert policy["asset_prefixes"] == ["migrated/asset-1/"]
        policy_id = policy["policy_id"]

        rc, out = self.run(tmp_path, "policy", "--revoke", policy_id,
                           "--reason", "test", capsys=capsys)
        assert rc == 0
        assert json.loads(out)["status"] == "revoked"

        rc, _ = self.run(
            tmp_path, "record-usage",
            "--asset-id", "asset-1", "--consumer-id", "cust-1",
            "--bytes", "2000000000", "--requests", "5",
            "--timestamp", "2026-01-10T00:00:00+00:00",
            capsys=capsys,
        )
        assert rc == 0

        rc, out = self.run(
            tmp_path, "report",
            "--start", "2026-01-01T00:00:00+00:00",
            "--end", "2026-02-01T00:00:00+00:00",
            "--rate-card", "LIC-1:per_gb:0.50", "--json",
            capsys=capsys,
        )
        assert rc == 0
        report = json.loads(out)
        assert report["licensors"]["licensor-x"]["licenses"]["LIC-1"]["amount"] == "1.00"

        actions = [e["action"] for e in read_audit_log(tmp_path)]
        assert actions == ["license.tag", "policy.issue", "policy.revoke", "usage.record"]

    def test_cli_validation_error_exit_code(self, tmp_path, capsys):
        rc, _ = self.run(
            tmp_path, "tag",
            "--asset-id", "a", "--license-id", "L",
            "--license-class", "commercially-licensable",
            "--right", "train", "--manifest-sha256", "not-a-sha",
            capsys=capsys,
        )
        assert rc == 2

    def test_module_invocation_via_subprocess(self, tmp_path):
        result = subprocess.run(
            [sys.executable, "-m", "tape_to_cloud.monetize",
             "--store", str(tmp_path), "list"],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )
        assert result.returncode == 0
        assert json.loads(result.stdout) == []
