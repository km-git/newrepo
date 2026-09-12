from pathlib import Path

from dspm.models import Finding
from dspm.risk.service import score_findings, score_from_fixture


def test_risk_scoring_known_fixture():
    root = Path(__file__).resolve().parents[1]
    scores = score_from_fixture(root / "fixtures" / "risk_fixture.json")
    assert len(scores) >= 1
    assert scores[0].score > 0
    assert scores[0].score <= 100


def test_public_s3_pii_scores_high():
    findings = [
        Finding(
            source="s3://public-bucket",
            location="email",
            type="PII",
            confidence=0.95,
            verdict="public",
        )
    ]
    scores = score_findings(findings, exposures=[{"type": "public_s3"}])
    assert scores[0].score >= 90
