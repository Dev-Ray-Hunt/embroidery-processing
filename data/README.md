# data/

Test inputs for the POCs. The contents of `sample_dsts/` and `madeira_sources/` are **gitignored** — only this README is committed.

## Sourcing rule

This project is **architecturally isolated** from Straight Down's Wilcom toolchain (no Wilcom integrations, no thread-DB exports, no Production Worksheet parsing). Data sourcing splits by tier:

- **Tier 1 (small, < 5k stitches):** publicly-licensed test DSTs only.
- **Tiers 2 (10k–20k) and 3 (30k+):** internal team-supplied DSTs, kept outside git, used as test inputs only — no Wilcom-format exports, just the DST output. This is the practical fallback because no public-domain corpus exists at these stitch counts (researched 2026-04-27).

For Madeira thread data: non-Wilcom sources only.

Original "pure R&D isolation" (Interpretation B) settled 2026-04-27 was relaxed the same day for tiers 2/3 once it became clear public-domain DSTs at those sizes don't exist.

## sample_dsts/ — DST files for POC 1

### Tier 1 — publicly-licensed (committed to this README; files gitignored)

| Filename | Source | Stitches | Color blocks | Size (mm) | License | Notes |
|----------|--------|----------|--------------|-----------|---------|-------|
| `embroidermodder.dst` | [Embroidermodder/Embroidermodder/test/Embroidermodder.DST](https://github.com/Embroidermodder/Embroidermodder/blob/main/test/Embroidermodder.DST) | 3,407 | 1 | 222 × 51 | zlib | Long single-color text-style logo. Wide aspect ratio. |
| `star.dst` | [Embroidermodder/Embroidermodder/test/Star.DST](https://github.com/Embroidermodder/Embroidermodder/blob/main/test/Star.DST) | 2,550 | 2 | 59 × 62 | zlib | Two-color star — minimal but tests color-change handling. |
| `shamrockin.dst` | [Embroidermodder/Embroidermodder/data/samples/shamrockin.dst](https://github.com/Embroidermodder/Embroidermodder/blob/main/data/samples/shamrockin.dst) | 1,473 | 1 | 50 × 49 | zlib | Single-color shamrock outline. Smallest of the three. |

Stitch / color-block / extent values produced by `pyembroidery.read()` (verified 2026-04-27). "Color blocks" = 1 + count of `COLOR_CHANGE` commands, since DST format itself stores no thread metadata.

### Tier 2 (10k–20k stitches) and Tier 3 (30k+ stitches) — DEFERRED

No publicly-licensed DST corpus exists at these stitch counts (researched 2026-04-27 — checked Embroidermodder, libembroidery, EmbroidePy/samples, Inkstitch, pyembroidery, p5.embroider, StitchView, stitchcode). Brandon is sourcing larger files from the Straight Down team. Those files will land here when supplied; their entries get added to the table above. They remain gitignored either way.

### How to re-fetch the Tier 1 files

```bash
cd data/sample_dsts/
curl -sfL -o embroidermodder.dst https://raw.githubusercontent.com/Embroidermodder/Embroidermodder/main/test/Embroidermodder.DST
curl -sfL -o star.dst             https://raw.githubusercontent.com/Embroidermodder/Embroidermodder/main/test/Star.DST
curl -sfL -o shamrockin.dst       https://raw.githubusercontent.com/Embroidermodder/Embroidermodder/main/data/samples/shamrockin.dst
```

## madeira_sources/ — Madeira (and Isacord cross-ref) chart data for POC 2

When populating, record each file here:

| Filename | Source URL | Format | Retrieved | License | Notes |
|----------|-----------|--------|-----------|---------|-------|
| | | | | | |

Acceptable sources: Madeira's own published charts (web/PDF), EZ Stitch's Madeira data, the Madeira Metro chart, the Isacord PDF (cross-reference only). **Not acceptable:** anything pulled from a Wilcom thread-database export.

`madeira_sources/spool_photos/` will hold physical-spool validation photos when captured. Capture protocol lives at `pocs/poc2_thread_catalogue/src/SPOOL_CAPTURE.md` (to be written when POC 2 starts).
