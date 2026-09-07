# Monetization Strategy Services: The `monetize` Broker Layer — Architecture and Implementation Blueprint

A deep-dive on the `monetize` module from the tape-to-cloud migration blueprint ([Section 12 mapping](./tape-to-cloud-migration-blueprint.md): "Monetization Strategy Services → `monetize` → Optional broker layer: license tagging, access control, royalty reporting"). This document treats the broker as a piece of software you can build — a licensing, entitlement, and metering layer that sits on top of the migrated corpus and turns it into sellable data products — not a consulting engagement. It assumes the parent pipeline's outputs exist: objects in cloud storage, a per-object chain-of-custody manifest, an append-only audit log, and optionally the LLM-corpus and ML-enrichment derivatives.

---

## 1. Scope and Design Constraints

The migration pipeline ends with bytes in object storage and a verifiable manifest. Monetization begins when a third party — a data buyer, an LLM lab, a research group, an internal business unit with a chargeback model — wants governed access to a slice of that corpus for money. The `monetize` module is the broker in the middle, and it must satisfy three constraints simultaneously:

- **License-first.** No object is distributable until it carries a machine-readable license tag and a resolvable rights chain back to the source tape's owner. The chain-of-custody manifest from the parent pipeline is the provenance root; the license tag extends it. An object without a rights determination is unsellable by construction, not by policy memo.
- **Enforcement at the storage layer, not the portal.** Entitlements must be enforced where the bytes are (STS-scoped credentials, presigned URLs, KMS grants, share revocation), so that a compromised portal cannot leak the corpus. The portal is a UI over the entitlement store; it never proxies bulk data.
- **Metering as an audit artifact.** Every access event feeds both the invoice and the append-only audit log. Royalty statements must be reproducible from raw events — the same replayability posture the parent blueprint demands from Temporal workflow histories.

Two things the module deliberately does not do: it does not process payments itself (it integrates Stripe or a marketplace's billing rails), and it does not make legal rights determinations (it records them, enforces them, and refuses to distribute when they are absent).

---

## 2. License Tagging and the Rights Chain

The parent blueprint's LLM module already calls for "license tagging (per-document, persisted in the manifest)" as step 5 of corpus preparation. This section specifies what that tag is.

### 2.1 The tag schema

Every distributable object (and every derivation of it) carries a license record in the catalog DB:

```json
{
  "asset_id": "sha256:9f2c…",
  "license_id": "CDLA-Permissive-2.0",       // SPDX identifier, or "LicenseRef-acme-commercial-v3"
  "license_uri": "https://spdx.org/licenses/CDLA-Permissive-2.0.html",
  "rights_holder": "org:acme-broadcasting",
  "rights_basis": "contract:2026-014 §4.2",  // pointer to the signed agreement granting resale rights
  "provenance": "manifest:tape-BC0413/file-2281",  // chain-of-custody manifest entry from migration
  "restrictions": ["no-eu-distribution", "no-model-training"],  // ODRL-expressible constraints
  "pii_status": "scrubbed:presidio-2.2+manual-qa",
  "effective": "2026-01-15", "expires": null,
  "tagged_by": "operator:jsmith", "tagged_at": "2026-02-03T14:11:09Z"
}
```

Three identifier regimes cover the real cases:

- **SPDX identifiers** for anything under a standard license. SPDX maintains the canonical license list [1], and data-specific licenses are on it: `CDLA-Permissive-2.0` is the Linux Foundation's permissive data license, with the useful property that "Results" (models, insights computed from the data) carry no downstream restriction [2]. `CC-BY-4.0` and friends cover the archival/media cases. The DataCite `rightsList` pattern — identifier + scheme + resolvable URI — is the reference for how to store it [3].
- **`LicenseRef-` custom licenses** (SPDX's escape hatch) for negotiated commercial terms: the license text lives in the catalog as an immutable blob, the tag points at it. Most migrated corporate corpora end up here, because the rights were never granted under a public license.
- **ODRL policies** when a single license string cannot express the deal. ODRL (W3C Recommendation, Information Model 2.2) models permissions, prohibitions, and duties as machine-readable RDF/JSON-LD — "may use for internal analytics, may not train generative models, must delete after 24 months, must pay per query" is one policy document [4]. The DALICC project demonstrates automated compatibility checking between such policies [5]. The pragmatic split: SPDX string for the 80% case, attached ODRL policy for the negotiated 20% [3].

### 2.2 Rights chain and provenance

The tag's `provenance` field points into the chain-of-custody manifest the migration pipeline already produced (source barcode, drive serial, SHA-256, operator, timestamp — parent blueprint Section 5). The `rights_basis` field points at the contract that authorizes resale. Both are mandatory for a `sellable=true` flag. This is the engineering expression of rights clearance: the software cannot prove the customer owns the copyright, but it can refuse to distribute any object whose rights chain has a hole, and it can produce the full chain — tape → manifest → rights document → license tag → entitlement → access event — in one query when a dispute arrives.

### 2.3 Propagation through derivation

Derivatives are where naive license systems fail. The migration pipeline creates them constantly: video proxies (ProRes/H.264 from a DPX master), OCR text from scanned documents, LLM training shards (deduplicated, PII-scrubbed, tokenized), and ML enrichment outputs (transcripts, face/entity metadata). The rule set:

| Derivation | License inheritance rule |
|---|---|
| Format transcode (proxy, re-wrap) | Inherits the source tag verbatim; same `asset_id` lineage, new object hash |
| Extraction (OCR text, email body) | Inherits source tag; `provenance` gains a derivation edge |
| Aggregation (LLM shard from N documents) | Tag = intersection of the N source licenses; if the intersection is empty (incompatible licenses), the shard is not buildable — the corpus builder must partition by license class first |
| ML enrichment output (transcript, embedding) | Inherits source tag unless the license is CDLA-Permissive-2.0-style with a Results carve-out [2], in which case the output may carry a broader tag |
| Statistical aggregate (counts, dashboards) | Configurable; default inherits the most restrictive source |

The intersection rule for LLM shards is the load-bearing one. It forces the corpus-prep pipeline (parent Section 9) to shard by license class — one Parquet lineage per license bucket — which is exactly what public corpora like Common Corpus do to stay distributable [6]. Lineage edges (source asset → derived asset, with the operation) live in the catalog DB and are append-only.

---

## 3. Access Control and Entitlements

### 3.1 Entitlement model

An **entitlement** is the tuple `(principal, product, license_id, constraints, expiry)`: who may access which published slice of the corpus, under which license, with which limits (row/prefix scope, QPS, byte quota, purpose restriction). A **product** is a published, versioned selection over the catalog — "all 1998–2004 broadcast masters, H.264 proxies only" — defined by a catalog query, frozen into an explicit object list at publish time so that what was sold is exactly reproducible. Entitlements live in their own store (Postgres; same instance class as the parent's catalog DB) and are the single source the enforcement layer reads.

### 3.2 Enforcement primitives per cloud

The broker never builds its own data plane. It vends scoped, short-lived credentials against the storage the migration pipeline already filled:

| Primitive | Mechanism | Fit |
|---|---|---|
| S3 Access Grants | Broker registers grant scopes (bucket/prefix); consumer app calls `GetDataAccess`, receives STS session credentials scoped to the grant, 15 min–12 h TTL; works for IAM principals and directory identities via IAM Identity Center trusted propagation, so CloudTrail records the end user [7][8][9] | Default for programmatic bulk access on AWS; grant scope maps 1:1 to a product's prefix |
| Presigned URLs | Time-limited bearer URL per object, generated by the broker's IAM role; sub-minute expiries practical [10] | Portal downloads of individual objects; avoids STS rate limits for high-fanout small-object access [10] |
| KMS grants | Per-tenant CMK encrypts each product prefix; a KMS grant to the buyer's principal is a second, independent revocation point [11] | Belt-and-braces for high-value corpora: revoking the grant makes bytes unreadable even if object ACLs lag |
| Azure user delegation SAS | SAS token signed with Entra ID credentials rather than account keys; scoped to container/blob with expiry [12] | Same role as presigned URLs on Azure Blob targets |
| GCS signed URLs / IAM conditions | V4 signed URLs, or IAM conditions on prefix [13] | Same role on GCS targets |
| Delta Sharing / marketplace shares | Share objects managed by the marketplace platform (Section 5); revocation via the share, not object storage | When distribution goes through Snowflake/Databricks |

Every credential issuance is an event: `(entitlement_id, principal, scope, ttl, request_id)` appended to the audit log before the credential is returned.

### 3.3 Tenant isolation for the Nexus-style portal

The parent blueprint's v3 is a multi-tenant SaaS portal (`tape-saas`). The monetize module inherits its isolation model and sharpens it, because tenants are now mutually distrusting counterparties (seller and N buyers):

- One KMS CMK per selling tenant; product prefixes encrypted under it; buyer access is always via grant, never via key sharing [11].
- Bucket-per-tenant or prefix-per-tenant with S3 Access Grants locations registered per tenant — no IAM policy that spans tenants [8].
- The portal's backend holds zero long-lived data-plane credentials; it holds the right to call `GetDataAccess`/sign URLs, and every call is attributable to a portal session and an entitlement row.
- Buyer-side delivery into the buyer's own bucket (S3 replication or server-side copy with the buyer's KMS key) is the preferred fulfillment for one-time licenses: after delivery, the broker holds nothing the buyer depends on.

---

## 4. Usage Metering and Royalty Reporting

### 4.1 Metering sources

Three raw feeds, all of which already exist or are one flag away in the parent architecture:

1. **Storage-layer access logs**: CloudTrail S3 data events / S3 server access logs (and Azure/GCS equivalents) give per-object `GetObject` records with principal, bytes, timestamp. With S3 Access Grants + trusted identity propagation, the end-user identity is in the CloudTrail event directly [9].
2. **Broker-issued credential events**: every presigned URL and STS vend from Section 3.2 — this is the intent record that joins a storage access to an entitlement.
3. **Marketplace-side reports**: AWS Data Exchange subscription/disbursement reports [14], Snowflake provider usage views, Databricks provider analytics — ingested as external meters since the platform, not the broker, served the bytes.

### 4.2 Aggregation and rating

Events are normalized to a metering event (`entitlement_id, asset_id, meter {objects|GB|queries|tokens}, quantity, ts`) and fed to a metering engine. Do not build this: **OpenMeter** (Apache-2.0-licensed core, Kafka + ClickHouse, built exactly for high-volume usage events → billable metrics → entitlement balance enforcement) is the metering-only choice that plugs into an existing Stripe stack [15]; **Lago** (AGPLv3, self-hostable) covers the full path — metering, plans, prepaid credits, invoices, payment orchestration via Stripe/Adyen — when the broker owns billing end to end [16]. The MVP recommendation is Lago self-hosted: one system, invoices included, no per-event SaaS fee.

### 4.3 Revenue share and statements

Royalty computation is a deterministic monthly job: for each rights holder, `Σ (rated usage per product × price) − channel fee (Section 5) − broker margin = payout`, with the split percentages versioned in the catalog next to the product definition. The statement generator emits, per rights holder per period: opening balance, per-product usage (objects, GB, queries), gross revenue, channel fees actually charged (from marketplace disbursement reports, not assumptions [14]), broker fee, net payout, and a content hash of the underlying event set. That hash is the audit alignment: the statement is anchored into the same append-only audit log the migration pipeline maintains (parent Section 5), optionally WORM-locked and timestamped alongside the chain-of-custody manifests. Any statement can be recomputed from raw events and must reproduce the hash — disputes are settled by replay, not by negotiation.

---

## 5. Distribution Channels

Where the broker publishes. The channel decides who runs billing, who enforces access, and what fee comes off the top. Verify fees before quoting — they are product configuration, not constants.

| Channel | Technical requirements | Access enforcement | Fees (published, at time of writing) |
|---|---|---|---|
| AWS Data Exchange | Register as AWS Marketplace seller, pass ADX provider qualification, eligible jurisdiction, tax/bank details (W-9/W-8), defined support process [17][14] | ADX-managed: S3 data sets, Redshift datashares, S3 direct access, APIs | 3% listing fee on public offers < $1M TCV, tiered down to 1.5% ≥ $10M and for renewals [18]; data-grant infrastructure billed hourly (~$0.04167/grant-hour) [19] |
| Snowflake Marketplace | Full Snowflake account, approved provider profile, Marketplace Ops/BD approval for paid listings, Stripe Connect payout account [20][21] | Snowflake shares; consumer never copies raw files; usage-based (per-query/monthly) or subscription pricing, USD only [22] | Transaction fee deducted from payout; the binding schedule is published in Snowsight (Admin → Billing & Terms → Fee), inclusive of Stripe charges [21][23]; payout 30 days after full collection [21] |
| Databricks Marketplace | Premium+ account, Unity Catalog-enabled workspace, Marketplace admin role; Data Partner Program for public listings; Delta Sharing does the transfer [24] | Delta Sharing shares; "by request" listings gate on provider approval | No listing fee and no revenue cut — all commercial transactions happen directly between provider and consumer, off-platform [25][26]; the broker must run its own contract + billing rail (Lago/Stripe) |
| Hugging Face Hub | Dataset repo with card metadata (`license:` field, SPDX-style identifiers) [27]; gated access with custom terms (`extra_gated_prompt`), extra fields, manual approval, optional EU-block (`extra_gated_eu_disallowed`) [28] | Gating + HF auth on downloads; no payment rail — commercial licensing is signed off-platform, gate approval is the fulfillment | Free hosting for public datasets; no marketplace billing — pair with direct invoicing |
| Direct S3-with-entitlements | Everything in Section 3; buyer needs only an AWS principal (or an HTTPS client, for presigned URLs) | Broker-enforced: Access Grants / presigned / KMS grants [7][10][11] | No channel fee; broker pays storage + egress and bills via Lago/Stripe [16] |

The channel decision in one sentence each: ADX when the buyers are AWS-native enterprises and 3% is cheaper than building billing [18]; Snowflake when the product is queryable tables and per-query pricing fits [22]; Databricks when reach matters and the broker already has a billing rail, since it takes no cut [25]; Hugging Face when the product is an LLM corpus and the goal is controlled distribution with license gating rather than platform billing [28]; direct S3 when the deal is a handful of large negotiated contracts and every basis point of fee matters.

---

## 6. Pricing Models

The broker must express five models, because real corpora sell under all five. The metering layer (Section 4) already captures the inputs for each.

| Model | Meter | Where it fits | Channel support |
|---|---|---|---|
| Subscription (recurring) | Time | Continuously refreshed products (ongoing enrichment output); the default on ADX and Snowflake [22] | ADX, Snowflake, direct |
| Per-query | Query count | Analyst-facing tabular products; Snowflake bills this natively with a provider-set monthly cap [22] | Snowflake, direct (API products) |
| Per-GB / egress-based | Bytes delivered | Bulk media (video masters, seismic); aligns price with the broker's real egress cost | Direct S3, ADX (S3 access) |
| Revenue share | Downstream revenue report | Media licensing where the buyer resells (footage in a documentary); requires the buyer-reported meter, trued up contractually | Direct only |
| One-time license | Delivery event | LLM training corpora — labs want a frozen snapshot, perpetual rights, delivered into their bucket; price the corpus, not the bytes | Direct, HF-gated fulfillment [28] |

Two judgments. First: LLM corpora sell as one-time snapshot licenses with delivery into the buyer's KMS-encrypted bucket (parent Section 9, step 7) — subscription pricing fails there because the buyer trains once. Second: per-query pricing without a monthly cap is a support burden; Snowflake's "maximum total charge per month" pattern [22] should be copied in the direct channel too.

---

## 7. Legal and Compliance Guardrails (What the Software Must Enforce)

Engineering controls only — this is what the module records and refuses, not legal advice:

- **PII scrub as a publish gate.** An asset may not enter a product unless its `pii_status` shows a completed scrub (the parent LLM module's Presidio + model-based pass [29]) or an explicit `not-applicable` determination with an operator identity attached. The gate is enforced at product-publish time and re-checked at entitlement-grant time (an asset re-flagged after publish blocks new grants).
- **Rights clearance as data, not vibes.** `sellable=true` requires a non-null `rights_basis` (Section 2.2). Bulk-migrated corpora default to `sellable=false`; monetization is opt-in per asset class after a rights review, and the review itself is a recorded catalog event.
- **Jurisdiction enforcement.** Restrictions like `no-eu-distribution` must be enforceable: on Hugging Face via `extra_gated_eu_disallowed` [28], on marketplaces via listing-country configuration and offer targeting, on the direct channel via buyer-declared jurisdiction on the entitlement plus the marketplace-seller jurisdiction rules the channels themselves impose (ADX restricts provider jurisdictions and requires tax registration [17]; regional listing fees vary by buyer country [18]).
- **Deletion and revocation duties.** ODRL duties like "delete after term" [4] become entitlement expiry + KMS grant revocation [11] + a recorded revocation event. For marketplace channels, revocation maps to unpublishing/share revocation. The software cannot delete bytes from a buyer's bucket after one-time delivery — so the statement of what was delivered, when, under which terms, is the artifact that matters, and it is WORM-anchored like everything else.
- **Audit unity.** One append-only log spans migration and monetization. The regulator's question — "who has ever touched this object, and under what authority?" — is answered by a single query joining chain-of-custody, license tags, entitlements, and access events.

---

## 8. Module Architecture

Components, all deployable alongside the parent stack:

- **License tagger** — batch + interactive service that writes license records; bulk rules ("everything from tape set X under contract 2026-014") plus per-asset overrides; validates SPDX identifiers against the license list [1] and ODRL documents against the 2.2 model [4].
- **Rights-chain resolver** — graph walk from any asset to its provenance root and rights basis; the lineage store for derivation edges (Section 2.3).
- **Product catalog** — versioned product definitions (catalog query → frozen object list), price plans, channel bindings. Postgres, same operational posture as the parent's manifest DB.
- **Entitlement store + policy decision point** — the `(principal, product, license, constraints, expiry)` table and the service that answers "may P access A now?"; every decision logged.
- **Credential vendor** — the only component with data-plane power: calls `GetDataAccess` [7], signs URLs [10][12][13], manages KMS grants [11].
- **Metering pipeline** — CloudTrail/access-log ingestion + broker events → OpenMeter or Lago [15][16].
- **Royalty engine + statement generator** — the monthly deterministic job of Section 4.3.
- **Channel adapters** — one per marketplace: ADX (AWS Marketplace Catalog API), Snowflake (listing + share management), Databricks (Marketplace provider console / Delta Sharing), Hugging Face (`huggingface_hub` repo + gating metadata).

Orchestration follows the parent's split exactly: **Temporal** owns the long-lived state machines (product publish → channel review → live; entitlement lifecycle grant → active → expiring → revoked; monthly royalty close), because these span days and must survive worker loss. **Airflow** owns the scheduled loops (nightly metering aggregation, log ingestion, statement runs). **Argo** is rarely needed here — the only burst workload is re-tagging a million-object corpus after a rights review, one pod per prefix.

The job graph for one product, publish to payout:

```
[rights review recorded]            [chain-of-custody manifest]
        ↓                                     ↓
[license tagger: bulk rules + overrides] ←────┘
        ↓
[pii gate check] ──fail──→ [blocked: back to scrub queue]
        ↓ pass
[product definition: catalog query → frozen object list]
        ↓
[price plan + channel binding]
        ↓
[channel adapter publish] ──→ [ADX / Snowflake / Databricks / HF / direct]
        ↓
[entitlement granted (sale / subscription / gate approval)]
        ↓
[credential vendor: Access Grants / presigned / SAS / share]  ──→ [append-only audit log]
        ↓                                                              ↑
[buyer access: storage-layer logs]  ──→  [metering pipeline]  ─────────┘
        ↓
[royalty engine: rate → split → statement + event-set hash]
        ↓
[payout via Lago/Stripe or marketplace disbursement]
        ↓
[statement WORM-anchored beside chain-of-custody manifests]
```

Each box is a Temporal activity or an Airflow task; every arrow that touches money or access writes to the audit log first.

---

## 9. MVP, v2, v3

Mirroring the parent's Section 14 posture:

- **MVP**: license tagger with SPDX + `LicenseRef` support, rights-chain fields on the existing manifest DB, `sellable` gate, direct-S3 channel only (Access Grants + presigned URLs), Lago self-hosted for metering + invoicing, manual product definitions, monthly statement job. This monetizes the first negotiated contracts with zero marketplace dependencies.
- **v2**: ADX and Snowflake channel adapters (they have the billing rails, so they come before portal work), ODRL policy support with derivation-intersection checking for LLM shards, KMS-grant revocation, CloudTrail-based per-end-user metering.
- **v3**: the multi-tenant broker portal (the monetization face of the parent's Nexus-style `tape-saas`), Databricks + Hugging Face adapters, buyer-side delivery automation, revenue-share (buyer-reported meter) contracts, automated license-compatibility checking à la DALICC [5].

---

## 10. Core Judgment

The `monetize` module is an entitlement ledger with a license graph on the front and other people's billing rails on the back. The engineering effort concentrates in three places: license tagging with correct propagation through derivation (the intersection rule for LLM shards is where naive designs silently produce undistributable or, worse, illegally distributable products), storage-layer enforcement (STS/Access Grants/KMS grants, never a data-proxying portal), and reproducible royalty statements anchored to the same append-only audit log the migration built. Everything else — payments, marketplaces, tax — should be bought, not built: Lago or OpenMeter for metering, Stripe or the marketplace for money movement, ADX/Snowflake when their 1.5–3% fee or Snowsight fee schedule is cheaper than owning collections, Databricks and Hugging Face when reach matters more than platform billing. The one thing that cannot be bought is the rights chain — and it is also the only part a court or a regulator will ever ask to see.

---

## References

[1] SPDX License List (canonical identifiers, including data licenses). https://spdx.org/licenses/

[2] SPDX — Community Data License Agreement Permissive 2.0 (full text; "Results" carve-out §3.1). https://spdx.org/licenses/CDLA-Permissive-2.0.html

[3] CASRAI — How to Describe Dataset Reuse Rights (DataCite `rightsList`, SPDX identifiers, when ODRL is warranted). https://casrai.org/guides/how-to-describe-reuse-rights-and-permissions-for-a-shared-dataset

[4] W3C — ODRL Information Model 2.2 (W3C Recommendation: permissions, prohibitions, duties). https://www.w3.org/TR/odrl-model/ and vocabulary https://www.w3.org/TR/2018/PR-odrl-vocab-20180104/

[5] ESWC 2018 — Modeling and Reasoning over Data Licenses (DALICC, ODRL-based license compatibility). https://2018.eswc-conferences.org/files/posters-demos/paper_298.pdf

[6] arXiv — Common Corpus: The Largest Collection of Ethical Data for LLM Pre-Training (license-partitioned distribution). https://arxiv.org/html/2506.01732v1

[7] AWS — Managing access with S3 Access Grants (prefix-scoped grants, directory identities). https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-grants.html

[8] AWS Storage Blog — Scaling data access with Amazon S3 Access Grants (`GetDataAccess`, 15 min–12 h STS sessions, minimal privilege). https://aws.amazon.com/blogs/storage/scaling-data-access-with-amazon-s3-access-grants/

[9] AWS — Request access to S3 data through S3 Access Grants (STS vend flow; trusted identity propagation → end user in CloudTrail). https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-grants-credentials.html

[10] AWS Prescriptive Guidance — Overview of presigned URLs (bearer semantics, sub-minute expiry, STS rate-limit trade-off). https://docs.aws.amazon.com/prescriptive-guidance/latest/presigned-url-best-practices/overview.html

[11] AWS KMS — Grants in AWS KMS (temporary, revocable key permissions). https://docs.aws.amazon.com/kms/latest/developerguide/grants.html

[12] Microsoft Learn — Create a user delegation SAS (Entra-signed, account-key-free SAS for Azure Blob). https://learn.microsoft.com/en-us/rest/api/storageservices/create-user-delegation-sas

[13] Google Cloud — Signed URLs for Cloud Storage. https://cloud.google.com/storage/docs/access-control/signed-urls

[14] AWS — AWS Data Exchange provider financials (Marketplace seller registration, monthly disbursement, seller reports). https://docs.aws.amazon.com/data-exchange/latest/userguide/provider-financials.html

[15] GitHub — openmeterio/openmeter (open-source usage metering: CloudEvents ingestion, real-time aggregation, entitlements, Stripe integration). https://github.com/openmeterio/openmeter

[16] GitHub — getlago/lago (open-source metering + billing: plans, credits, invoices, Stripe/Adyen orchestration). https://github.com/getlago/lago

[17] AWS — Getting started as an AWS Data Exchange provider (qualification, eligible jurisdictions, W-9/W-8 + banking, support-process requirement). https://docs.aws.amazon.com/data-exchange/latest/userguide/provider-getting-started.html

[18] AWS — Understanding listing fees for AWS Marketplace sellers (Data Exchange 3% < $1M TCV, 2% $1–10M, 1.5% ≥ $10M and renewals; regional uplifts). https://docs.aws.amazon.com/marketplace/latest/userguide/listing-fees.html

[19] CloudZero — AWS Data Exchange Guide (data-grant hourly infrastructure pricing, cost structure). https://www.cloudzero.com/blog/aws-data-exchange/

[20] Snowflake Docs — Create and publish a listing (provider profile, paid-listing approval, Stripe Express requirement). https://docs.snowflake.com/en/collaboration/provider-listings-creating-publishing

[21] Snowflake Docs — Marketplace invoicing, collections, and payouts (provider as seller of record, Snowflake invoices in USD, fee deducted from payout, payout 30 days after collection, Snowsight fee schedule). https://docs.snowflake.com/en/collaboration/provider-transactions-invoicing-collections

[22] Snowflake Docs — Paid listings pricing models (usage-based per-query/monthly with max-charge cap; subscription upfront). https://docs.snowflake.com/en/collaboration/provider-listings-pricing-model

[23] Snowflake — Marketplace Provider Playbook, extended version (fee inclusive of Stripe charges; pricing model catalog). https://www.snowflake.com/wp-content/uploads/2023/08/sm-provider-playbook-extended-ver.pdf

[24] Databricks Docs — Become a Databricks Marketplace provider (Premium+ plan, Unity Catalog metastore, Data Partner Program for public listings). https://docs.databricks.com/aws/en/marketplace/become-provider

[25] Databricks Blog — Top 10 Marketplace Questions, Answered (no listing fee, no revenue cut, transactions directly between provider and consumer). https://www.databricks.com/blog/top-10-marketplace-questions-answered

[26] Databricks Docs — Access data products in Databricks Marketplace ("by request" approval flow; no commercial transactions handled on-platform). https://docs.databricks.com/aws/en/marketplace/get-started-consumer

[27] Hugging Face Docs — Dataset Cards (YAML metadata, `license:` identifiers, `license_link` for custom licenses). https://huggingface.co/docs/hub/datasets-cards

[28] Hugging Face Docs — Gated datasets (access requests, `extra_gated_prompt`/`extra_gated_fields`, manual approval, `extra_gated_eu_disallowed`). https://huggingface.co/docs/hub/datasets-gated

[29] GitHub — microsoft/presidio (PII detection and de-identification; the parent LLM module's scrub step). https://github.com/microsoft/presidio
