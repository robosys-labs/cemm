# R4.1 Source-Readiness Review Worksheets

> DRAFT — NON-AUTHORITATIVE. No review decision is selected.

Input set: `r4_1_review_input_set_v1:d58246ad137f5bc8ab0ee1eb`

| Worksheet | Ref | Bytes | SHA-256 | Rows |
|---|---|---:|---|---:|
| `PURPOSE_DECISIONS.json` | `review_worksheet:97f4fad536e735e64637ea96` | 822965 | `f254780652dfa6a9f37d760f8f90d40723baf5285c4de853495682246f0f0f42` | 600 |
| `SOURCE_UNIVERSE.json` | `review_worksheet:356325b71584cfc5691633a8` | 520927 | `abdf748ecce386070b56857ea78435e69791e3da9575f2c227ac920f766abfec` | 626 |
| `STRUCTURAL_DECISIONS.json` | `review_worksheet:355bf430e226142624fed132` | 84548 | `cfc35ced8bb3740bf08052b0bdeaee9d3e21a700c472ebd440c3ebf1390f01dc` | 12 |
| `SUPERVISION_DECISIONS.json` | `review_worksheet:e14180d346570a12793aa09c` | 2242356 | `eb02c6781a0560aa40642a3188d6b4b76c8bce6107bd8f91f57d76570da155be` | 1552 |

Current source: 210 scenarios, 400 cases, `r4_source_set_v1:075df6221d6d7f27f6d2f715`.

The candidate structural set contains eight unresolved proposals. The legacy conditional and restart decisions remain unresolved.

There are 1887 explicitly non-selectable authoring requirements. Approval of these draft bytes alone cannot satisfy them; exact ABI records must replace every such placeholder before SR6.

| Conditional branch | Scenarios | Cases | Source universe | Generator SHA-256 |
|---|---:|---:|---|---|
| `retain_typed_proposal_gaps` | 218 | 408 | `r4_source_set_v1:5bef48816cd7eaba655df6ed` | `90ac843cb09dd576ca7abb4b1dffcde9a27f59dd77e71d6db876a059ea6c362c` |
| `retire_with_reserved_indices` | 216 | 404 | `r4_source_set_v1:260851378ebb7d469d3f10f1` | `2b0a6eee5da0cc2624d42766b75d803df3f73aa4892038010ed42ba47ed8252a` |

`data/review/r4_1/` is intentionally absent. These files do not approve or publish reviewed source.
