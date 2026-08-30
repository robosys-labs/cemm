# R4.1 Source-Readiness Review Worksheets

> DRAFT — NON-AUTHORITATIVE. No review decision is selected.

Input set: `r4_1_review_input_set_v1:a3170b29fc5d83642d45e8fa`

| Worksheet | Ref | Bytes | SHA-256 | Rows |
|---|---|---:|---|---:|
| `PURPOSE_DECISIONS.json` | `review_worksheet:5d376630dafc69c0b9c8564f` | 821757 | `c60d07f4857f6be8ec5b046b9d70e675161a2dbca4289fc9544ee8015390f75f` | 600 |
| `SOURCE_UNIVERSE.json` | `review_worksheet:1ccd462f8e9b22a0a7c5a845` | 518699 | `c6eaa2ef0ac8a431099d6bcdde9db3ad1f5f9b6232e6b192eea6b73b88b929a4` | 626 |
| `STRUCTURAL_DECISIONS.json` | `review_worksheet:2ed477ee45216618588b6860` | 83340 | `65bf43669cdf75d74373712c91c9d9d4b51e27505849aa0a41f9441f7b59164d` | 12 |
| `SUPERVISION_DECISIONS.json` | `review_worksheet:93b6d5462f4b7d011237a441` | 1501731 | `260279322bd5f36fe9ef8b6b7a9e87716d7453bebce46f76d2e223dfc64f2b84` | 1552 |

Current source: 210 scenarios, 400 cases, `r4_source_set_v1:1d6a3263c29f384842f0d031`.

The candidate structural set contains eight unresolved proposals. The legacy conditional and restart decisions remain unresolved.

There are 1560 explicitly non-selectable authoring requirements. Approval of these draft bytes alone cannot satisfy them; exact ABI records must replace every such placeholder before SR6.

| Conditional branch | Scenarios | Cases | Source universe | Generator SHA-256 |
|---|---:|---:|---|---|
| `retain_typed_proposal_gaps` | 218 | 408 | `r4_source_set_v1:3e804e10b63482539469f51c` | `ec7377f185d7638b6c9697ce1cfec4eafb7f6cfe3556e9ea3dfaf3c2ed1f591a` |
| `retire_with_reserved_indices` | 216 | 404 | `r4_source_set_v1:491b56385718bd6443ab2e5e` | `07cb6b6a5cac905cdb9da648edf1741dc40982f405c55dce329885fe58d20bef` |

`data/review/r4_1/` is intentionally absent. These files do not approve or publish reviewed source.
