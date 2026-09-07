# Feature Completeness Matrix — Tape-to-Cloud Migration Tool

A research pass against live vendor menus (Tape Ark, Iron Mountain), AWS Tape Gateway / Snowball, LTO-10, MediaGenie Proteus, and Spectra/GRAU WORM practice. The 16 Iron Mountain-style / Tape Ark menu lines stay first-class modules. Gaps are capabilities those vendors ship **inside** a menu line that the original prompt treated as optional plumbing.

Verdict: keep the 16-module map. Add six **cross-cutting layers** that every module must call. Do not invent a 22-module product; the extra work is capability depth, not a new brochure.

Source of the 16 lines: Tape Ark public solutions (Comprehensive Media Audit, Archive Insight, Virtualization, Restore, Disk Ingest, Email Restore, GroupWise-to-M365, Tape Copy, Video Digitization, Legacy Tape Management, Nexus, Tape Storage, Destruction, LLM, AI/ML, Monetization) plus Iron Mountain DRMS / vaulting / ITAD [11][12][13][14].

---

## 1. Menu Coverage (already mapped)

| Menu line | Module | Vendor confirmation |
|---|---|---|
| Comprehensive Media Audit | `audit` | Tape Ark CMA: QR, 360 photos, RFID volume estimate, degradation 1-10, cloud-cost forecast [15] |
| Archive Insight | `analytics` | Tape Ark Nexus file/server-level view; mixed retention on one tape [16] |
| Tape Migration: Virtualization | `vtl-cloud` | AWS Tape Gateway VTL + iSCSI; Snowball offline path; Tape Ark 1,500-slot VTL [17][18] |
| Tape Migration: Restore | `restore` | Iron Mountain on-demand restore; Tape Ark mid-project restore [11][16] |
| Disk-Based Data Ingest | `disk-ingest` | Tape Ark disk/server/Snowball/Data Box ingest [19] |
| Email Restore From Tape | `email-extract` | PST/EDB/NSF; user/date/keyword; eDiscovery [20] |
| GroupWise to M365 | `email-migrate` | GroupWise + Lotus + Exchange → M365 / Workspace / PST; virus + dedup [21] |
| Tape Copy and Duplication | `tape-duplicate` | 1-to-N; seismic/SEG specialty [12] |
| Video Digitization | `media-ingest` | Broadcast + CCTV + medical; Media2Cloud [12][22] |
| Legacy Tape Management | `tape-ops` | Inventory, catalog, restore testing, onsite mobilization [16] |
| Nexus SaaS | `tape-saas` | Tenant portal, file-level delete, dept billing, air-gap/immutability [16] |
| Tape Storage | `tape-vault` | Residual physical vault + courier CoC; Iron Mountain vaulting / library moves / 24/7 DR [13] |
| Media Destruction | `destroy` | Wipe, degauss, shred, incinerate, certify; ITAD [12][13] |
| Legacy Data for LLM | `llm-corpus` | Private GPT / RAG from liberated tape [12][16] |
| AI and ML Services | `ml-enrich` | Tagging, transcribe, Textract; Versos-style packaging [22] |
| Monetization Strategy | `monetize` | License, access, royalty [22] |

---

## 2. Gaps Closed in This Pass

These were missing or underspecified in the original 16-row table.

### Cross-cutting layers (required, not extra menu items)

| Layer | Why it is required | Concrete deliverable |
|---|---|---|
| `integrity` | Iron Mountain and Tape Ark both sell chain-of-custody + bit-for-bit verification; Tape Ark hashes MD5/SHA-1 in public copy — this tool defaults to SHA-256 [11][18] | Pre/post SHA-256, signed sidecar manifest, optional full tape image (Iron Mountain Media Imaging) [23] |
| `ediscovery` | Litigation restore is a first-class Iron Mountain and Tape Ark SKU; keyword/custodian/date filters; legal hold vs GDPR erasure conflict [11][20] | Hold graph, production package (PST/NSF/load file), defensibility log |
| `kms-kmip` | LTO hardware AES-256; key is never on the cartridge; KMIP cluster; LTO-10 quantum-safe AES-GCM-256 [24][25] | Envelope encrypt, KMIP client, refuse read if key missing |
| `worm` | Tape Gateway Tape Retention Lock; S3 Object Lock; GCS Bucket Lock; Azure Immutable Blob; GRAU FileLock GoBD/SEC 17a-4 [17][26] | Policy engine + stop-and-ask on WORM vs right-to-erasure |
| `format-readers` | NetBackup cannot read TSM; MediaGenie Proteus is the commercial cross-format reference; Cohesity now owns NetBackup; Backup Exec is Arctera [27][28][29] | Plugin table; license-or-wrap default; no half parsers on cheap models |
| `media-rescue` | Stiction, oxide loss, reverse-wound, broken tape, encrypted-without-keys, HDD recovery [11][14][30] | Degraded-media path; HDD rescue; stop-and-ask before inventing crypto bypass |

### Source-matrix gaps (now in the rule)

- **Mainframe / enterprise tape:** 7/9/21-track reel, 3480/3490/3590, IBM 3592 Jaguar TS11xx, StorageTek T9840/T9940/T10000A–E [31].
- **Legacy cartridge:** DLT/SDLT, AIT/SAIT, VXA, QIC/SLR/Travan, Exabyte 8mm, DDS/DAT, Sony DTF [31].
- **LTO-1 through LTO-10.** LTO-10 has **no** backward read/write; a mixed fleet is mandatory if the customer spans generations [24].
- **Libraries:** IBM TS3xxx/TS4xxx/TS7770/Diamondback, Oracle SL150/500/3000/8500, Quantum Scalar, Spectra TFinity [31].
- **Not only tape:** USB/NAS/SAN, RDX, UDO/ODA/Blu-ray, floppy/ZIP/JAZ, flash — `disk-ingest` [31].
- **Broadcast video:** Betacam, VHS, DigiBeta, DVC, DV Cam — `media-ingest` [31].

### Backup-app format gaps (now in the rule)

Tape Ark's published enterprise list: Backup Exec, NetBackup (Cohesity), IBM Spectrum Protect / TSM, Veeam, Catalogic DPX, HPE Data Protector / Omniback, ARCserve, Quest NetVault, CommVault Simpana/Galaxy, NetWorker, Avamar, Data Domain, MTF / NT Backup, TAR/CPIO, Retrospect, plus M&E (StorNext, SAM-FS, XenData, DIVArchive, Atempo, SGL Flashnet) and geophysical SEG* [30][32]. MediaGenie Proteus covers the same core backup apps plus NAS NDMP (NetApp, Celerra, Isilon) [27].

Also name **Cohesity DataProtect** and **Rubrik** as modern sources the VTL must present iSCSI to, even when the *reader* is still NetBackup/TSM.

### Target-matrix gaps

- On-prem S3 default is **SeaweedFS** (MinIO Community Edition archived 2026); Cloudian/Ceph remain valid [33].
- Retrieval tiers: S3 Glacier Flexible (hours) vs Deep Archive (5–12 h); Tape Gateway Tape Pool [17].
- Iron Cloud Object Storage / SOS is a *customer* target, not a hard-coded vendor [11].

### Restore / email / destroy depth

- Email: EDB + PST + NSF; Google Workspace as well as M365; virus/malware quarantine; mailbox consolidation [20][21].
- Delivery: encrypted USB/DVD as well as cloud staging [34].
- Destroy: logical wipe, degauss, shred, incineration; certificate; ITAD of drives and libraries — not tape-only [12][13].
- Audit: RFID/MAM cartridge memory, 360 photography, QR, degradation score, duplicate media, cloud-cost estimate [15].
- Nexus: file-level dispose (physical tape cannot delete part of a cartridge), unlimited users, segregated billing [16].

---

## 3. Explicitly Out of MVP Scope (do not silently add)

- Paper/microfilm scanning (Tape Ark "Archive Insight" marketing also covers paper; this tool's `analytics` is tape/disk catalogs only unless the user asks).
- Iron Mountain InSight DXP as a required UI.
- Versos AI as a hard dependency (integrate via `monetize` adapter, stop-and-ask for paid SaaS).
- Inventing a TSM/NetBackup parser on a cheap model.

---

## 4. Build Rule for Agents

When implementing any menu module, also satisfy the six cross-cutting layers. Point at this file rather than pasting it. Cheap models scaffold RFID/QR/photo JSON, SHA-256 manifests, SeaweedFS/S3 adapters, PST writers, ffmpeg, tesseract, presidio. Frontier models own format readers, KMIP, WORM-vs-erasure, Temporal, Nexus isolation, damaged-media strategy.

---

## References

[11] Iron Mountain — Data restoration and migration services. https://www.ironmountain.com/services/data-restoration-and-migration

[12] Tape Ark — home / service catalog (video, email, destruction, LLM, copy). https://www.tapeark.com/

[13] Iron Mountain — Offsite tape vaulting, library moves, 24/7 DR, ITAD. https://www.ironmountain.com/services/offsite-tape-vaulting

[14] Iron Mountain — HDD recovery called out on DRMS page. https://www.ironmountain.com/services/data-restoration-and-migration

[15] Tape Ark — Comprehensive Media Audit (QR, photos, RFID, degradation 1-10). https://www.tapeark.com/comprehensive-media-audit/

[16] Tape Ark — Nexus SaaS (file-level retention, billing, air-gap, mid-project restore). https://www.tapeark.com/nexus/

[17] AWS — Tape Gateway VTL concepts (iSCSI, Tape Pool, Glacier). https://docs.aws.amazon.com/storagegateway/latest/tgw/StorageGatewayConcepts.html

[18] AWS Storage Blog — Tape Ark + Snowball with Tape Gateway; WORM / Tape Retention Lock. https://aws.amazon.com/blogs/storage/aws-and-tape-ark-partner-to-migrate-petabytes-of-tape-data-using-aws-snowball-with-tape-gateway/

[19] Tape Ark — Disk-based data ingest. https://www.tapeark.com/disk-based-data-ingest/

[20] Tape Ark — Email restore from tape (EDB/PST, keyword, eDiscovery). https://www.tapeark.com/email-recovery/

[21] Tape Ark — GroupWise / Lotus / Exchange to Microsoft 365. https://www.tapeark.com/groupwise-to-microsoft-365-enterprise-platform-migration-service/

[22] Tape Ark — Versos AI monetization + media archive unlock. https://www.tapeark.com/versos-ai-2/

[23] Iron Mountain — Media Imaging Services (bit-image each tape). https://www.ironmountain.com/resources/solution-guides/i/iron-mountain-media-imaging-services

[24] LTO Consortium — LTO-10: no backward compatibility, WORM, AES-GCM-256, LTFS. https://www.lto.org/lto-10/

[25] LTO Consortium — Hardware encryption and KMIP. https://www.lto.org/encryption/

[26] GRAU DATA — FileLock WORM (GoBD, SEC 17a-4). https://openarchive.net/en/products/filelock

[27] Data Strategies — MediaGenie Proteus (NetBackup, Backup Exec, NetWorker, TSM, ARCserve, CommVault, Data Protector). https://go-dsi.com/mediagenie-proteus/

[28] Cohesity — Completes combination with Veritas enterprise data protection (NetBackup), 10 Dec 2024. https://www.cohesity.com/newsroom/press/cohesity-becomes-worlds-largest-data-protection-provider-after-completing-combination-with-veritas-enterprise-data-protection-business/

[29] TechTarget — Backup Exec and InfoScale spun to Arctera. https://www.techtarget.com/data-technologies/news/366617112/Cohesity-completes-acquisition-of-Veritas

[30] Tape Ark — Supported data formats (enterprise, supercomputer, SEG, M&E). https://www.tapeark.com/data-formats/

[31] Tape Ark — Tape media types (reel, 3592, T10000, LTO-10, libraries, optical, broadcast). https://www.tapeark.com/tape-media-types/

[32] Tape Ark — FAQ (StorNext, SAM-FS, XenData, DIVArchive, TSM, Atempo, Flashnet, TAR/LTFS). https://www.tapeark.com/faq/

[33] Sibling inventory / MinIO CE archive 2026 — prefer SeaweedFS for on-prem S3. See `discovery/tape-to-cloud/free-tool-inventory.md` when present; MinIO CE GitHub archive announced 2026.

[34] Iron Mountain restoration datasheet — encrypted USB/DVD delivery, mailbox consolidation. https://www.ironmountain.com/resources/solution-guides/d/data-restoration-and-migration-services-solution-brief
