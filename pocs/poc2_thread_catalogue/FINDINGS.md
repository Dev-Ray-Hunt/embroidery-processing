# POC 2: Thread Catalogue & Color Matching — Findings

> Fill in as the POC progresses. This document is the deliverable.

## What we built

_TBD_ — catalogue (size, lines covered, source mix), matching algorithms implemented (A–D), palette strategies implemented (A–C), validation UI.

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
