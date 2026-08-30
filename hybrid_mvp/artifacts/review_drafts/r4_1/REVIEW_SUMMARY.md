# R4.1 Source-Readiness Review Worksheets

> DRAFT — NON-AUTHORITATIVE. No review decision is selected.

Input set: `r4_1_review_input_set_v1:043f6c738f65cb782e1a9530`

| Worksheet | Ref | Bytes | SHA-256 | Rows |
|---|---|---:|---|---:|
| `PURPOSE_DECISIONS.json` | `review_worksheet:264a46732c5f076e0464075a` | 822965 | `3b00e1310c00ad48babff178299c6c834c1605667f70a1b75bddb1c85f417d27` | 600 |
| `SOURCE_UNIVERSE.json` | `review_worksheet:514b27a7f630332675759c71` | 520927 | `129612357caeeacdfdde547ee0ca80c2f6853e66e0d23593215df431491907b0` | 626 |
| `STRUCTURAL_DECISIONS.json` | `review_worksheet:6d8f50d6457e7d9d617ace04` | 84548 | `03ed70ce0f4f3b72b100228e6c68f19b232687b9e124d14ced12e76ada280ba8` | 12 |
| `SUPERVISION_DECISIONS.json` | `review_worksheet:3caaf8b8c9bad7c653820105` | 2122448 | `934c7f529c46ce6045b2b8eddb0b2604acaf923087cffd594b5b52abf897ec95` | 1552 |

Current source: 210 scenarios, 400 cases, `r4_source_set_v1:075df6221d6d7f27f6d2f715`.

The candidate structural set contains eight unresolved proposals. The legacy conditional and restart decisions remain unresolved.

There are 1887 explicitly non-selectable authoring requirements. Approval of these draft bytes alone cannot satisfy them; exact ABI records must replace every such placeholder before SR6.

| Conditional branch | Scenarios | Cases | Source universe | Generator SHA-256 |
|---|---:|---:|---|---|
| `retain_typed_proposal_gaps` | 218 | 408 | `r4_source_set_v1:5bef48816cd7eaba655df6ed` | `90ac843cb09dd576ca7abb4b1dffcde9a27f59dd77e71d6db876a059ea6c362c` |
| `retire_with_reserved_indices` | 216 | 404 | `r4_source_set_v1:260851378ebb7d469d3f10f1` | `2b0a6eee5da0cc2624d42766b75d803df3f73aa4892038010ed42ba47ed8252a` |

`data/review/r4_1/` is intentionally absent. These files do not approve or publish reviewed source.
