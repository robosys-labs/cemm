# R4.1 Source-Readiness Review Worksheets

> DRAFT — NON-AUTHORITATIVE. No review decision is selected.

Input set: `r4_1_review_input_set_v1:41d041eb4458de20f51ff602`

| Worksheet | Ref | Bytes | SHA-256 | Rows |
|---|---|---:|---|---:|
| `PURPOSE_DECISIONS.json` | `review_worksheet:f57b5ab7e567ba53f635021d` | 823128 | `d156135b12aef8883a8e2cb103f754ecaa512ec6a66af1c24c53528e1a7879de` | 600 |
| `SOURCE_UNIVERSE.json` | `review_worksheet:add177309fdc2935643385aa` | 521090 | `f9220df8fe04fa446665b9b41e6d1dd2c583877906017cbaacc1ead0893033d5` | 626 |
| `STRUCTURAL_DECISIONS.json` | `review_worksheet:e3161f278dcc3b934d1f8752` | 84711 | `40f49dc48aa6ef0969ff89c1a27a21e40fa20217d3c4f4a26129b353ce45b64b` | 12 |
| `SUPERVISION_DECISIONS.json` | `review_worksheet:846d7d9ff7f98473a65c06d0` | 2455140 | `dd2f1bd1822cf974493fd10f96c138abf93f31a7655388b8e22d2e2fd58635d8` | 1552 |

Current source: 210 scenarios, 400 cases, `r4_source_set_v1:075df6221d6d7f27f6d2f715`.

The candidate structural set contains eight unresolved proposals. The legacy conditional and restart decisions remain unresolved.

There are 1887 explicitly non-selectable authoring requirements. Approval of these draft bytes alone cannot satisfy them; exact ABI records must replace every such placeholder before SR6.

| Conditional branch | Scenarios | Cases | Source universe | Generator SHA-256 |
|---|---:|---:|---|---|
| `retain_typed_proposal_gaps` | 218 | 408 | `r4_source_set_v1:5bef48816cd7eaba655df6ed` | `90ac843cb09dd576ca7abb4b1dffcde9a27f59dd77e71d6db876a059ea6c362c` |
| `retire_with_reserved_indices` | 216 | 404 | `r4_source_set_v1:260851378ebb7d469d3f10f1` | `2b0a6eee5da0cc2624d42766b75d803df3f73aa4892038010ed42ba47ed8252a` |

`data/review/r4_1/` is intentionally absent. These files do not approve or publish reviewed source.
