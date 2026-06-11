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

### Tier 2 / Tier 3 — Straight Down team-supplied (not committed; gitignored)

Internal Straight Down DSTs supplied by the embroidery team (acquired 2026-05-01). Used as test inputs only — never committed, never redistributed. Filenames preserve their original Wilcom job IDs for provenance.

| Filename | Stitches | Color blocks | Size (mm) | Tier | Notes |
|----------|----------|--------------|-----------|------|-------|
| `000252366-001.dst` | 5,329 | 1 | 76 × 53 | 1/2 boundary | Just over the < 5k tier-1 ceiling. Single-color. Useful as the simplest "real" production design. |
| `000021273.dst` | 9,686 | 5 | 51 × 51 | 2 (low) | 5-color design. Just under the 10k threshold per pyembroidery's count, treat as low end of tier 2. |
| `000001055-007.dst` | 20,623 | 8 | 64 × 66 | 2 (top) | 8-color, mid-density fills. Top of tier-2 range. |
| `000000813-092.dst` | 63,710 | 19 | 165 × 120 | **3** | Large 19-color design, 16.5 × 12 cm. Hits the 30k+ tier-3 requirement. Best stress test in the corpus. |

Stitch / color-block / extent values produced by `pyembroidery.read()` (verified 2026-05-01). These files do NOT have a public re-fetch path — they live only on Brandon's machine and any teammate who supplies them. To re-acquire after a fresh checkout, copy them into `data/sample_dsts/` from wherever you stored them locally.

### How to re-fetch the Tier 1 files

```bash
cd data/sample_dsts/
curl -sfL -o embroidermodder.dst https://raw.githubusercontent.com/Embroidermodder/Embroidermodder/main/test/Embroidermodder.DST
curl -sfL -o star.dst             https://raw.githubusercontent.com/Embroidermodder/Embroidermodder/main/test/Star.DST
curl -sfL -o shamrockin.dst       https://raw.githubusercontent.com/Embroidermodder/Embroidermodder/main/data/samples/shamrockin.dst
```

## madeira_sources/ — Madeira (and Isacord cross-ref) chart data for POC 2

All retrieved 2026-06-11. Used for internal R&D color reference only — none of these files or values are redistributed.

| Filename | Source URL | Format | License/status | Notes |
|----------|-----------|--------|----------------|-------|
| `madeira_official_colour_cards.pdf` | https://www.madeira.com/fileadmin/user_upload/Downloads/Shade_Cards/Colour_Cards.pdf | PDF (vector+JPEG) | Madeira public download | 2023 multi-line shade cards; CLASSIC 40 index parsed |
| `madeira_official_polyneon.pdf` | https://www.madeira.com/fileadmin/user_upload/Downloads/Shade_Cards/MADEIRA_POLYNEON.pdf | PDF (vector) | Madeira public download | Dedicated Polyneon card, 18 panels/page |
| `madeirausa_classic_names.pdf` | https://www.madeirausa.com/_resources/common/userfiles/file/Resources/Madeira%20Color%20names/Classic%20ColorNames2015.pdf | PDF (text) | Madeira USA public download | Official Classic names (377) |
| `madeirausa_polyneon_names.pdf` | https://www.madeirausa.com/_resources/common/userfiles/file/Resources/Madeira%20Color%20names/Polyneon%20ColorNames2015.pdf | PDF (text) | Madeira USA public download | Official Polyneon names (409) |
| `inkstitch_madeira_rayon.gpl` | https://raw.githubusercontent.com/inkstitch/inkstitch/main/palettes/InkStitch%20Madeira%20Rayon.gpl | GIMP palette | GPL (Ink/Stitch) | Full Classic 1000-1499 RGB+names |
| `inkstitch_madeira_polyneon.gpl` | https://raw.githubusercontent.com/inkstitch/inkstitch/main/palettes/InkStitch%20Madeira%20Polyneon.gpl | GIMP palette | GPL (Ink/Stitch) | Polyneon RGB+names |
| `inkstitch_isacord.gpl` | https://raw.githubusercontent.com/inkstitch/inkstitch/main/palettes/InkStitch%20Isacord%20Polyester.gpl | GIMP palette | GPL (Ink/Stitch) | Isacord cross-reference (POC 2 Task 2) |
| `ezstitch_madeira_classic_40.pdf` | https://ezstitchdigitizing.com/madeira_classic_40_colors.pdf | PDF (text) | Public download, no license stated | Despite the filename: Polyneon 40 (per its own title page + 1500-1999 range) |
| `ciainc_polyneon.pdf` | https://www.ciainc.com/pdf/POLYNEON%20THREAD%20CHART.pdf | PDF (vector, CMYK) | Public download, no license stated | Cross-reference only (CMYK, no ICC) |
| `madeirausa_classic_ecard.pdf` / `corporatecasuals_classic40.pdf` | madeirausa.com / corporatecasuals.com | PDF | Public download | Identical files; CID-garbled text — NOT parsed |
| `dakota_alphabetical.pdf`, `dakota_numerical.pdf` | dakotacollectibles.com | PDF (text) | Public download | Cross-reference lists, no RGB — NOT parsed |

One-shot re-fetch of everything that's parsed:

```bash
cd data/madeira_sources/
curl -sfL -o madeira_official_colour_cards.pdf "https://www.madeira.com/fileadmin/user_upload/Downloads/Shade_Cards/Colour_Cards.pdf"
curl -sfL -o madeira_official_polyneon.pdf "https://www.madeira.com/fileadmin/user_upload/Downloads/Shade_Cards/MADEIRA_POLYNEON.pdf"
curl -sfL -o madeirausa_classic_names.pdf "https://www.madeirausa.com/_resources/common/userfiles/file/Resources/Madeira%20Color%20names/Classic%20ColorNames2015.pdf"
curl -sfL -o madeirausa_polyneon_names.pdf "https://www.madeirausa.com/_resources/common/userfiles/file/Resources/Madeira%20Color%20names/Polyneon%20ColorNames2015.pdf"
curl -sfL -o inkstitch_madeira_rayon.gpl "https://raw.githubusercontent.com/inkstitch/inkstitch/main/palettes/InkStitch%20Madeira%20Rayon.gpl"
curl -sfL -o inkstitch_madeira_polyneon.gpl "https://raw.githubusercontent.com/inkstitch/inkstitch/main/palettes/InkStitch%20Madeira%20Polyneon.gpl"
curl -sfL -o inkstitch_isacord.gpl "https://raw.githubusercontent.com/inkstitch/inkstitch/main/palettes/InkStitch%20Isacord%20Polyester.gpl"
curl -sfL -o ezstitch_madeira_classic_40.pdf "https://ezstitchdigitizing.com/madeira_classic_40_colors.pdf"
curl -sfL -o ciainc_polyneon.pdf "https://www.ciainc.com/pdf/POLYNEON%20THREAD%20CHART.pdf"
```

The Madeira Metro chart was not found in a parseable digital form (only physical cards for sale); the Ink/Stitch palettes fill that role.

`madeira_sources/spool_photos/` will hold physical-spool validation photos when captured. Capture protocol: `pocs/poc2_thread_catalogue/src/SPOOL_CAPTURE.md`.
