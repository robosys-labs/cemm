# St. Gabriel Estate — Individual Asset Pack

137 individually named PNG assets, extracted from the approved concept sheets in this conversation.

## Open first

Open **index.html** in a browser after extracting the ZIP. The catalog works offline, includes category/search filters, and can preview assets on light, dark or checkerboard backgrounds. Each image links to its individual PNG.

## Contents

- `buildings/`: 13 files
- `characters/`: 11 files
- `portraits/`: 18 files
- `references/`: 13 files
- `streets/`: 11 files
- `ui/`: 65 files
- `vehicles/`: 6 files

All individual PNGs are under `assets/`. Full original boards and the wingless scene are under `references/source_boards/` for comparison, not as substitutes for the individual assets. `manifest.json` records every asset's original crop coordinates, dimensions, transparency, extraction mode, and SHA-256 checksum.

## Transparency and fidelity

- Residents, the lollipop deceiver, wingless standalone spirits, building lots, vehicles, street modules, and interface glyphs have extracted alpha backgrounds.
- Character portraits, interface panels/buttons, and scene vignettes retain their authored backgrounds. This is intentional.
- Wingless standalone forms are `angel_ribbon_wingless` and `angel_prayer_wingless`. The two source scenes in which a guardian physically overlaps a resident remain paired reference illustrations; hidden pixels were not invented.
- The canonical deceiver is the pale teal lollipop head on a brown wooden body. The inconsistent human-shaped teal influence portrait in the UI source sheet was not exported as a character.
- Glows, contact shadows, landscaping, road foundations and some lighting are already painted into the source images. Alpha extraction may leave edge fringes or small background remnants. Inspect on the target scene before shipping.
- Opaque UI components contain baked-in example text and numbers, including any spelling artifacts from the generated boards. They are visual references, not editable layouts or validated game rules.

## Engine import

Use straight (not premultiplied) alpha blending for cutouts. The spirit and glow layers can also be tested with additive blending, but normal alpha preserves their authored color more closely. Import as 2D textures/sprites. Choose filtering for the target camera and pixel density rather than treating these as pixel art.

Original resolution is preserved: no artificial upscaling, no invented details. Many icon crops are only tens of pixels across. Buildings retain their individual lot footprints; the set is not yet standardized to a common tile scale or pivot. Road pieces are concept modules, not tested seamless tiles. Resident figures contain one pose/direction, not complete animation cycles.

## Scope

This is an **individual concept-art / prototype asset pack**, not a completed production game asset library. It does not include 3D models, rigs, animation sets, layered design originals, audio, code, validated simulation data, or commercial rights clearance. The PNGs are raster extracts from AI-generated artwork already supplied in the conversation; they do not contain separately editable internal layers.

The metrics and religious symbolism in the source art are fictional game-design concepts, not claims about real people's holiness, health, destiny or life expectancy.
