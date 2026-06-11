# Canonical DST JSON schema

The shape `dst_parser.parse()` produces and every POC 1 renderer consumes.
Parse once, render five ways — no renderer touches `pyembroidery` directly.

Coordinates and `extents` are in **native DST units (0.1 mm)**. The
millimeter values in `metadata` are the only human-facing conversions.

```jsonc
{
  "source": "embroidermodder.dst",      // original filename
  "metadata": {
    "stitch_count": 3407,        // STITCH commands only (matches Wilcom et al.)
    "command_count": 3420,       // every entry incl. jumps/trims/color-changes/end
    "jump_count": 13,
    "trim_count": 0,
    "color_change_count": 0,
    "color_block_count": 1,      // color_change_count + 1 (DST stores no thread data)
    "width_mm": 222.0,
    "height_mm": 51.0
  },
  "extents": [min_x, min_y, max_x, max_y],   // bounding box, 0.1mm units
  "color_change_indices": [1203, 2410],      // indices into `stitches` where a
                                             //   COLOR_CHANGE entry sits; renderers
                                             //   use these as color-block boundaries
  "stitches": [                              // ordered command stream
    [x, y, "STITCH"],
    [x, y, "JUMP"],
    [x, y, "COLOR_CHANGE"],
    [x, y, "END"]
  ]
}
```

## `stitches` command names

Decoded from the low byte of pyembroidery's command int (masked with
`COMMAND_MASK`):

`STITCH` · `JUMP` · `TRIM` · `STOP` · `END` · `COLOR_CHANGE` · `SEQUIN_MODE` ·
`SEQUIN_EJECT` · `NEEDLE_SET`

Any unrecognized command is emitted as `CMD_<n>` (the masked integer) rather
than dropped, so renderers can decide how to handle the long tail. For most DST
designs the only commands present are `STITCH`, `JUMP`, `COLOR_CHANGE`, and a
trailing `END`.

## Renderer contract

- Draw `STITCH` entries as thread; the segment runs from the previous point to
  this one.
- `JUMP` is travel, not thread — most renderers skip drawing it (it may still
  move the "pen").
- Split the design into color blocks at `color_change_indices` (or by scanning
  for `COLOR_CHANGE` entries). DST carries no actual thread colors, so blocks
  get assigned palette colors by the renderer / editor downstream.
- `extents` gives the bounding box for sizing the canvas without scanning every
  point.

## Producing it

```bash
uv run python -m pocs.poc1_dst_renderer.src.dst_parser <path-to-dst>            # full JSON
uv run python -m pocs.poc1_dst_renderer.src.dst_parser <path-to-dst> --summary  # metadata only
```
