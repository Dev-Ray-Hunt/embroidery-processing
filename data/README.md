# data/

Test inputs for the POCs. The contents of `sample_dsts/` and `madeira_sources/` are **gitignored** — only this README is committed.

## Sourcing rule (Interpretation B)

This project is **source-isolated** from Straight Down's Wilcom toolchain. Test inputs come from public, openly-licensed sources only:

- No production DSTs from Straight Down's library.
- No exports from Wilcom (no thread DB exports, no Production Worksheet PDFs).
- Public sample DSTs and publicly-published Madeira / Isacord chart data only.

Settled 2026-04-27. See memory `project_tool_independence.md` for context.

## sample_dsts/ — public DST files for POC 1

When populating, record each file here:

| Filename | Source URL | Stitch count | Color count | License | Notes |
|----------|-----------|--------------|-------------|---------|-------|
| _e.g._ `pyembroidery_test_simple.dst` | https://github.com/EmbroidePy/pyembroidery/tree/main/test/assets | | | (verify) | simple text logo |
| | | | | | |

Need at least 3 covering: simple text-only (< 5k stitches), multi-color with fills (10k–20k), complex detailed (30k+).

Primary source: [`pyembroidery` test corpus](https://github.com/EmbroidePy/pyembroidery/tree/main/test/assets). Add others as found.

## madeira_sources/ — Madeira (and Isacord cross-ref) chart data for POC 2

When populating, record each file here:

| Filename | Source URL | Format | Retrieved | License | Notes |
|----------|-----------|--------|-----------|---------|-------|
| | | | | | |

Acceptable sources: Madeira's own published charts (web/PDF), EZ Stitch's Madeira data, the Madeira Metro chart, the Isacord PDF (cross-reference only). **Not acceptable:** anything pulled from a Wilcom thread-database export.

`madeira_sources/spool_photos/` will hold physical-spool validation photos when captured. Capture protocol lives at `pocs/poc2_thread_catalogue/src/SPOOL_CAPTURE.md` (to be written when POC 2 starts).
