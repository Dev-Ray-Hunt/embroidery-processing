# POC 1: DST Renderer — Findings

> Fill in as the POC progresses. This document is the deliverable, not a side note.

## What we built

_TBD_ — list each rendering approach actually implemented (A through E), with a one-line description of how each one draws stitches and any deviations from the original spec.

## What we measured

_TBD_ — for each (renderer × test design × fabric background):

- rendering time (cold and warm)
- output file size
- max stitch count before performance degrades
- visual side-by-side vs. reference photos (where available — note Interpretation B means no Straight Down stitch-out photos)

## Scorecard

_TBD_ — table scoring each renderer 1–5 on Reliability / Quality / Speed / Flexibility, with the weighted formula `(R × 4) + (Q × 3) + (S × 2) + (F × 1)`. Max 50, MVP-viable threshold 30.

| Renderer | R | Q | S | F | Weighted |
|----------|---|---|---|---|----------|
| A. pyembroidery PNG | | | | | |
| B. Pillow 2D | | | | | |
| C. Cairo 2D | | | | | |
| D. HTML5 Canvas | | | | | |
| E. WebGL/Three.js | | | | | |

## What we learned

_TBD_ — surprises, things the spec under-specified, things that turned out easier or harder than expected. Include findings from the Kajiya-Kay shader paper if the Three.js renderer used it.

## Recommendation if shipping for real

_TBD_ — primary renderer (for customer proofs) + secondary (for interactive use), with the reasoning. If none crossed the MVP threshold, say so.

## Open questions / followups

_TBD_ — what would be worth pursuing if this were a real product build, and what got deferred.
