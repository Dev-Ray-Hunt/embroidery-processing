# POC 2: Thread Catalogue & Color Matching — Findings

> Fill in as the POC progresses. This document is the deliverable.

## What we built

**Step 1 (2026-06-11): the catalogue.** 823 threads — 391 Classic Rayon 40 + 432
Polyneon 40 — built by `src/catalogue.py` from six independent sources
(Madeira's own 2023 shade-card PDFs, Madeira USA's official name lists,
Ink/Stitch's GPL palettes, EZ Stitch's RGB chart, CIA Inc.'s chart), merged
under a documented priority rule (official Madeira swatch colors win; see
`src/SCHEMA.md`). Exceeds the ≥200 pass bar 4×.

- 51 entries (6%) conflict-flagged where non-reference sources disagree by
  ΔE76 > 18 — these are the priority queue for spool validation.
- Coverage vs official name lists: Polyneon 406/409 named colors have RGB;
  Classic 377/377 named colors have RGB (217 of them backed by Madeira's own
  published swatch colors, the rest by Ink/Stitch only).
- Notable data findings: Classic Rayon 40 catalog numbers span exactly
  1000–1499 and Polyneon 1500–1999/2000s — no overlap, which makes line
  membership unambiguous. EZ Stitch's "classic_40" chart is actually
  Polyneon (its own title page says so). The Madeira Metro chart appears to
  exist only as a physical card.

Matching algorithms (A–D), palette strategies, validation UI: **not started**
(Step 2 — see NEXT.md).

## What we measured

_TBD_:

- catalogue completeness (% of Classic Rayon 40 + Polyneon covered)
- Delta-E distribution across 50 random test colors per algorithm
- Delta-E distribution across 10 sample logos per algorithm
- match speed per algorithm
- spool-photo RGB vs catalogue RGB (when captured)

## Scorecards

### Color matching algorithms

| Algorithm | R | Q | S | F | Weighted |
|-----------|---|---|---|---|----------|
| A. CIEDE2000 (LAB) | | | | | |
| B. CIE76 (LAB) | | | | | |
| C. RGB Euclidean | | | | | |
| D. CMC l:c | | | | | |

### Palette optimization

| Strategy | R | Q | S | F | Weighted |
|----------|---|---|---|---|----------|
| A. Greedy nearest | | | | | |
| B. Constrained palette | | | | | |
| C. Perceptual clustering | | | | | |

## What we learned

_TBD_ — surprises in the source data, where each algorithm fails (saturated colors? near-blacks? neons?), whether textile-specific CMC actually beats CIEDE2000 in practice for thread colors.

## Recommendation if shipping for real

_TBD_ — winning algorithm + palette strategy + reasoning.

## Open questions / followups

_TBD_ — gaps in catalogue, sources we couldn't access, validation we couldn't do.
