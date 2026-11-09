# Validation performed

- Verified 438 PNG records against their SHA-256 hashes and stored dimensions.
- Verified all 301 new runtime PNGs are non-empty RGBA images with in-canvas pivots.
- Parsed all 91 editable SVG sources.
- Checked all 180 individual animation frames against the corresponding atlas rectangles, pixel-for-pixel.
- Verified coverage of all sixteen road connectivity masks. This is a geometry/registry check, not a claim of exhaustive engine-specific seam testing.
- Verified the original archive CRCs and compared every original asset byte-for-byte.
- Compiled the Python tools and syntax-checked the demo JavaScript.
- Tested initial demo rendering, resident selection, overlay visibility, animation pause, catalog filtering and search in Chromium using local asset bytes embedded in memory. The managed browser blocked direct file/localhost navigation, so that route was not tested here.

Reports: `data/validation_report.json`, `data/browser_validation.json`.

Reproduce asset validation with `python tools/validate_assets.py`. Browser checks additionally require Playwright and an available Chromium installation; run `python tests/browser_smoke.py`.

Visual contact sheets and an integration screenshot are in `previews/`.
