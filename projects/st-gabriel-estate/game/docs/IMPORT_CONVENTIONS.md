# Import conventions

## Transparency

PNG files use straight alpha. Normal alpha blending is the baseline. Glow assets may also be tested as additive overlays; they do not require additive blending. Do not interpret premultiplied RGB as straight alpha. Underlying character/building art is unchanged from batch 01.

## Isometric grid

Runtime tile raster: 256 × 128. Grid-to-screen top anchor:

```text
screen_x = origin_x + (grid_x - grid_y) * 128
screen_y = origin_y + (grid_x + grid_y) * 64
```

The tile image's upper corner is `(128, 0)` and center is `(128, 64)`. For center-based placement use the recorded center pivot. Four-edge masks refer to world-grid directions: N=1 (negative grid y), E=2 (positive grid x), S=4, W=8. They are not literal screen compass headings. Match N to S and E to W when placing adjacent tiles. Original concept road lots are not part of this standardized tileset.

## Layers

Typical order: terrain, road, ground selection, rear effects, building/person, front effects, HUD. For detailed front/back halo occlusion, split the ring in-engine or supply an occlusion mask; this batch provides complete overlay rings. Sort world objects by world footprint/foot anchor, not sprite height.

## Animation

`data/animations.json` contains frame count, fps, loop flag, frame dimensions, columns/rows, source PNG list, atlas path and absolute-pixel pivot. All atlases use 4 columns and 3 rows. Read frames in row-major order. Separate PNG frames are included for engines that perform their own packing. No atlas gutters are included; use clamp mode and avoid mipmap bleeding, or repack with engine-specific extrusion before shipping.

Wingless loops are 224 × 256 with foot anchor (112, 230). They animate bob/luminance, not articulated limbs. Character tint variants are intentional. Effects have fixed canvases; never independently auto-trim frames unless the importer stores the original offset.

## UI

SVG icons have 64 × 64 source viewports. Panels and controls carry `nine_slice` margins in the manifest. Render text and values in the UI layer, not into the PNG. The demo shows all requested indicators without requiring a canvas-baked text panel. Use application-provided fonts; no font files are included.

## Lifespan and spiritual values

Data files contain example fixtures only. Remaining-life estimates are shown as ranges. Neither grace percentage nor estimated life remaining is derived from real-world measurements. Keep display values separate from authoritative simulation state until the actual design and engine are validated.
