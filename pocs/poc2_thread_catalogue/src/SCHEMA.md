# madeira_catalogue.json schema (v1)

Produced by `uv run python -m pocs.poc2_thread_catalogue.src.catalogue` into
`outputs/poc2/madeira_catalogue.json` (gitignored — regenerate from the
sources in `data/madeira_sources/`; re-fetch script in `data/README.md`).

```jsonc
{
  "schema_version": 1,
  "threads": [
    {
      "catalog_number": "1147",
      "color_name": "Christmas Red",       // official Madeira USA name; null if unknown
      "brand": "Madeira Classic Rayon 40",
      "line": "Classic Rayon 40",          // or "Polyneon 40"
      "rgb": [182, 15, 47],                // winning source's value, 0-255
      "hex": "#b60f2f",
      "lab": [39.3, 62.4, 27.5],           // CIELAB, D65, via colour-science
      "color_family": "red",               // white/yellow/orange/red/pink/purple/
                                           //   blue/green/brown/neutral/black
      "weight": "40",
      "fiber": "Rayon",                    // Rayon | Polyester
      "rgb_source": "inkstitch_rayon",     // which source won (priority below)
      "source_rgb": {                      // every source's value, for audit
        "inkstitch_rayon": [182, 15, 47],
        "official_classic": [185, 18, 50]
      },
      "in_official_names": true,           // appears in Madeira USA's ColorNames list
      "conflict": false,                   // sources disagree by ΔE76 > 18 (ciainc excluded)
      "max_source_delta_e": 3.1
    }
  ],
  "stats": { "total": 823, "per_line": {...}, "conflicts": 51, "sources": {...} }
}
```

## Reconciliation rule (documented per NEXT.md step 3)

RGB winner = highest-priority source holding the code:

1. `official_classic` / `official_polyneon` — Madeira's own published shade
   cards (swatch fills / thumbnails extracted from the PDFs)
2. `inkstitch_rayon` / `inkstitch_polyneon` — Ink/Stitch open-source palettes
   (the only full-coverage Classic source)
3. `ezstitch_polyneon` — explicit RGB text chart
4. `ciainc_polyneon` — CMYK converted without ICC: audit-only, never wins,
   excluded from conflict flagging

`conflict: true` is a **review queue**, not an exclusion — flagged entries
ship with the winning value and are the priority list for physical spool
validation (see `SPOOL_CAPTURE.md`).

## Known limitations

- All RGB values are publishers' screen approximations of physical thread;
  the POC 2 spool-photo validation is what grounds them in reality.
- Madeira's 2023 brochure index only carries swatches for ~217 of 377+
  Classic colors; the rest come from Ink/Stitch alone (single-source, so
  they can never be conflict-flagged — listed via `len(source_rgb) == 1`).
- Metallic/fluorescent lines (FS, Supertwist) are out of scope for now.
