# St. Gabriel Estate

A 1990s-estate spiritual community simulation **asset repository**, not a finished game.

## Start here

Open `index.html` for the complete searchable asset library. Open `demo/index.html` for a small integration preview with resident selection, composited halos, wingless companions and an editable resident panel. The preview uses fixture data, not a running social simulation.

No JavaScript framework, package installation, hosted service or internet connection is required by the preview. A simple local server is also available:

```bash
python -m http.server 8000
```

Then open `http://localhost:8000`.

## Included

| Set | Count | Status |
|---|---:|---|
| Original individual PNGs | 137 | Original concept extracts, unchanged |
| New standalone PNGs | 106 | Runtime prototype foundations |
| New separate animation frames | 180 | 15 twelve-frame effects / idle loops |
| New animation atlases | 15 | JSON frame, timing and pivot metadata |
| Editable SVG source files | 91 | Icons, UI components, overlays and tiles |
| Total individually addressed PNGs | **438** | Count includes frames and atlases |

The original ZIP is preserved exactly at `releases/St_Gabriel_Estate_Individual_Assets.zip`.

## New batch

- Five resident halo states: faint, fading, bright, radiant and dark.
- Three separate temple aura strengths: dim, healthy and radiant.
- Two approved wingless spirit forms, each with warm and concerned tints; fixed-canvas idle bob/luminance loops.
- Protection, charity-link and targeted-whisper overlay effects.
- Eight 256 × 128 isometric terrain tiles.
- All sixteen four-edge road connectivity masks, plus crosswalk, speed bump, stop-line and pothole variants.
- Blank nine-slice panels, buttons, tabs, notifications and meters; UI text is rendered independently.
- Gold vector glyphs for the resident indicators, faith and parish life, essential needs, assignments, safety and controls.

## Layout

```text
assets/                  Original individually extracted PNGs
assets/runtime/          New components, effects, frames, atlases and tiles
sources/runtime/         Editable SVG sources for the new vector assets
data/                    Manifests, animation records, fixtures and validation
releases/                Exact original ZIP
references/source_boards/Approved concept boards; not production sprites
demo/                    Browser composition and resident-panel preview
tools/                   Rebuild, catalog, validation and GitHub publish tools
docs/                    Art conventions, scope, next asset work and upload guide
previews/                Contact sheets for visual inspection
```

## Rebuild and validate

Rebuilding requires Python and the packages in `requirements-build.txt`. Browsing the pack does not.

```bash
python -m pip install -r requirements-build.txt
python tools/generate_runtime_assets.py
python tools/build_catalog.py
python tools/validate_assets.py
```

Generated effects have straight alpha. Road/terrain tiles use a 2:1 diamond. Asset metadata records absolute pixel pivots. Atlas layout is four columns with row-major frames. No fonts are bundled.

## Publishing to GitHub

**The remote repository was not created in this session.** The available GitHub connector exposed read operations only; this runtime had neither a GitHub CLI login nor a configured push credential. This is a real locally committed Git repository prepared for publishing, not a claim that anything has been uploaded.

The included `tools/publish_github.py` uses your locally authenticated GitHub CLI to create a **private** repository and push the committed pack. It does not ask for or print credentials. It refuses to overwrite an existing origin or force-push.

```bash
gh auth login
python tools/publish_github.py
```

To publish under an organization, add `--owner YOUR_ORGANIZATION`. The default name is `st-gabriel-estate`. See `docs/PUBLISH.md` for bundle/ZIP instructions.

## Scope and limitations

These are prototype materials. The old extracted art has baked-in lighting and some edge remnants; the new procedural tiles and UI are intentionally simplified runtime foundations. They are not a claim of final stylistic parity with the detailed concept art. Characters still need original multi-direction art and articulated action cycles. The spirit loops are not walking animations.

Grace, faith, light, charity credits, destiny and remaining-life figures in the preview are fictional game abstractions. They are not theological judgments or medical estimates. Need, poverty and unhappiness are kept distinct from chosen harmful conduct; a guardian remains present in every resident fixture.

Production gaps and exact status are recorded in `docs/ASSET_STATUS.md`.
