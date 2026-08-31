# R4.1 Source-Readiness Review Worksheets

> DRAFT — NON-AUTHORITATIVE. No review decision is selected.

Input set: `r4_1_review_input_set_v1:2de6468ad3d8401a80793581`

| Worksheet | Ref | Bytes | SHA-256 | Rows |
|---|---|---:|---|---:|
| `PURPOSE_DECISIONS.json` | `review_worksheet:5f5416add695be9967b526a8` | 823128 | `a35556104ef7a40fe24373533fac6455d9e4a8a4506a50ffae79e0ac301832f2` | 600 |
| `SOURCE_UNIVERSE.json` | `review_worksheet:04e0443655829dd0a4f7b625` | 521090 | `6b3d3ed25c0cfb43d40700121d6b07c12ed7abf88ce6655b02cde3bdae02fd1d` | 626 |
| `STRUCTURAL_DECISIONS.json` | `review_worksheet:05326a30370bc25ff1fc7767` | 84711 | `f5561919e03e729cb23ff3f65851df1c285663b18a8dde46a3c21723a9bfa7dc` | 12 |
| `SUPERVISION_DECISIONS.json` | `review_worksheet:c1a208dbe2dbf9ee2d740699` | 2455140 | `6e7d63b2dc49c075abbc2d721909e8716696e86c26801f99b9c2c2a3c5c535ce` | 1552 |

Current source: 210 scenarios, 400 cases, `r4_source_set_v1:075df6221d6d7f27f6d2f715`.

The candidate structural set contains eight unresolved proposals. The legacy conditional and restart decisions remain unresolved.

There are 1887 explicitly non-selectable authoring requirements. Approval of these draft bytes alone cannot satisfy them; exact ABI records must replace every such placeholder before SR6.

| Conditional branch | Scenarios | Cases | Source universe | Generator SHA-256 |
|---|---:|---:|---|---|
| `retain_typed_proposal_gaps` | 218 | 408 | `r4_source_set_v1:5bef48816cd7eaba655df6ed` | `90ac843cb09dd576ca7abb4b1dffcde9a27f59dd77e71d6db876a059ea6c362c` |
| `retire_with_reserved_indices` | 216 | 404 | `r4_source_set_v1:260851378ebb7d469d3f10f1` | `2b0a6eee5da0cc2624d42766b75d803df3f73aa4892038010ed42ba47ed8252a` |

`data/review/r4_1/` is intentionally absent. These files do not approve or publish reviewed source.
