# POC 2: Stitch Generation Algorithm Bake-Off

## Proof of Concept — Project Requirements Document

---

## Objective

Prove that we can take a vector shape (SVG path/polygon) and generate production-quality fill, satin, and running stitch patterns.

## Why This Is Second

Once we know DST writing works (POC 1), the next risk is whether our stitch generation algorithms produce stitches that look good when sewn. Bad algorithms = bad embroidery regardless of file format.

---

## Global Constraints

| Constraint | Value |
|-----------|-------|
| **Builder** | Brandon + Claude/AI agents |
| **Primary language** | Python 3.10+ (backend/engine) |
| **Target machine** | Barudan embroidery machines via BNet software |
| **Primary output format** | DST (Tajima) — universal compatibility |
| **Thread brand** | Madeira (Classic Rayon 40, Polyneon) |
| **Evaluation priority** | 1. Reliability → 2. Quality → 3. Speed → 4. Flexibility |

### Evaluation Scoring Framework

Every bake-off option is scored on four dimensions using a 1-5 scale:

| Score | Reliability | Quality | Speed | Flexibility |
|-------|------------|---------|-------|-------------|
| **5** | Works 100% of the time, no edge-case failures | Indistinguishable from hand-digitized | < 5 seconds | Every parameter is tunable |
| **4** | Works 95%+ with known, manageable edge cases | Professional quality, minor imperfections | 5-30 seconds | Most parameters tunable |
| **3** | Works 80%+ with occasional failures | Acceptable for production, noticeable vs hand-digitized | 30s - 2 min | Key parameters tunable |
| **2** | Works 50-80%, frequent failures need workarounds | Functional but visibly automated | 2-10 min | Limited tunability |
| **1** | Unreliable, < 50% success rate | Not production-worthy | > 10 min | Essentially fixed |

**Weighted score formula:** `(Reliability × 4) + (Quality × 3) + (Speed × 2) + (Flexibility × 1)`

Maximum possible score: 50. Minimum viable for MVP selection: 30.

---

## What To Build

A Python module that accepts Shapely polygons and generates stitch coordinates for three stitch types: fill, satin, and running stitch.

## Test Designs

1. **Large fill region** — Square, 60mm × 60mm, fill stitch at 45°
2. **Small fill region** — Circle, 15mm diameter (tests minimum-area handling)
3. **Narrow column** — 3mm × 40mm rectangle, satin stitch
4. **Curved column** — S-curve path, 4mm wide, satin stitch
5. **Outline** — Star shape perimeter, running stitch
6. **Multi-region** — Simple logo with 3 colors, mixed stitch types

---

## Bake-Off: Fill Stitch Algorithms

| Option | Description | Source |
|--------|-------------|--------|
| **A. Custom scanline fill** | Build our own using the algorithm from the research doc (parallel lines clipped to polygon) | Research doc Section 8.1 |
| **B. Ink/Stitch auto-fill** | Extract and use Ink/Stitch's `auto_fill.py` module (Shapely + NetworkX graph-based) | `inkstitch/lib/stitches/auto_fill.py` |
| **C. stitch-generator library** | Use `stitch-generator`'s path-based fill effects | PyPI `stitch-generator` |
| **D. PEmbroider-style parallel** | Port PEmbroider's PARALLEL hatch algorithm from Java to Python | PEmbroider API reference |

## Bake-Off: Satin Stitch Algorithms

| Option | Description | Source |
|--------|-------------|--------|
| **A. Custom dual-rail zigzag** | Our own implementation from research doc Section 8.2 | Research doc |
| **B. Ink/Stitch satin column** | Extract Ink/Stitch's satin_column.py | GitHub |
| **C. stitch-generator satin** | Use `stitch-generator`'s satin path effect | PyPI |

---

## Pass/Fail Criteria

- [ ] All designs stitch cleanly on Barudan (no thread breaks from bad stitch sequences)
- [ ] Fill stitch covers the target region completely (no visible gaps)
- [ ] Satin stitch produces clean, even columns (no irregular zigzags)
- [ ] Running stitch follows the path accurately
- [ ] Multi-region design has correct stitch sequencing and color changes

---

## Measurements To Record

- Total stitch count per algorithm per design
- Processing time per algorithm per design
- Visual quality assessment (1-5, with photos)
- Edge coverage quality (gaps at polygon boundaries)
- Jump stitch count (fewer = better)
- Stitched output photos (side-by-side comparison)

---

## Deliverables

1. Python module with all algorithm implementations
2. DST files for every algorithm × design combination
3. Side-by-side photos of stitched output
4. Comparison scorecard with weighted scores
5. **Design recommendation:** Which algorithm(s) to use for each stitch type in the MVP

---

## Estimated Effort

2-3 sessions with Claude

## Dependencies

- **POC 1 (DST Smoke Test)** must be complete — need validated DST writer

## Risk

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| Fill stitch quality too low for production | **High** — auto-generation becomes unusable | Medium | Bake-off tests 4 algorithms; fallback is Ink/Stitch's proven approach |

---

## Reference Documents

- [Embroidery File Generation Deep Research Brief](./Embroidery_File_Generation_Deep_Research.md)
- [POC 1: DST Smoke Test](./POC_1_DST_Smoke_Test.md) — prerequisite
