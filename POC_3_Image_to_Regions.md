# POC 3: Image-to-Regions Pipeline

## Proof of Concept — Project Requirements Document

---

## Objective

Prove that we can take a raster logo image (PNG/JPG), reduce it to a limited color palette, extract vector regions for each color, and classify each region by stitch type.

## Why This Is Third

This is the "input side" of the pipeline. If we can't reliably go from image → regions → stitch type assignments, the auto-generation feature doesn't work.

---

## Global Constraints

| Constraint | Value |
|-----------|-------|
| **Builder** | Brandon + Claude/AI agents |
| **Primary language** | Python 3.10+ (backend/engine) |
| **Input types** | SVG vector files, PNG/JPG raster logos |
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

A Python module that takes an image file and outputs a list of classified vector regions ready for stitch generation.

## Test Images

1. **Simple 2-color logo** — Black text/icon on white background
2. **3-4 color corporate logo** — Clean edges, solid fills
3. **Logo with gradients** — Tests color quantization handling of non-solid areas
4. **Logo with fine detail** — Thin lines, small text, intricate shapes
5. **SVG version of logo #2** — Bypass raster processing, test SVG parsing directly

---

## Bake-Off: Color Quantization

| Option | Description |
|--------|-------------|
| **A. K-Means in LAB space** | scikit-learn KMeans on CIELAB-converted pixels |
| **B. K-Means in RGB space** | Simpler, but perceptually non-uniform |
| **C. Median Cut** | Recursive color space subdivision (PIL/Pillow's `quantize()`) |
| **D. Pre-defined palette matching** | Skip clustering, match every pixel to nearest Madeira thread color directly |

## Bake-Off: Vectorization

| Option | Description |
|--------|-------------|
| **A. OpenCV contour tracing** | `findContours` + Douglas-Peucker simplification → Shapely polygons |
| **B. Potrace (via potracer)** | Bitmap tracing library used by Inkscape, produces smooth Bezier outlines |
| **C. scikit-image marching squares** | `find_contours()` with level-set approach |

## Bake-Off: SVG Parsing (for vector input)

| Option | Description |
|--------|-------------|
| **A. svgpathtools** | Python library for parsing SVG paths to Bezier curves |
| **B. cairosvg + Shapely** | Render SVG to paths via Cairo, convert to Shapely geometries |
| **C. Inkscape CLI** | Use Inkscape's command-line to convert SVG → simplified SVG with just paths |

---

## Pass/Fail Criteria

- [ ] All test images produce valid Shapely polygons for each color region
- [ ] Region boundaries match the original image with < 1mm deviation at embroidery scale
- [ ] Color quantization produces distinct, reasonable color assignments
- [ ] Small regions (< 3mm²) are correctly classified as "running stitch" or filtered out
- [ ] SVG input produces equivalent regions to raster input for the same logo
- [ ] Processing completes in < 30 seconds for a typical logo

---

## Measurements To Record

- Number of regions extracted per image
- Polygon vertex count per region (simpler = better for stitch generation)
- Color accuracy (Delta-E between quantized colors and original)
- Processing time per approach
- Visual overlay comparison (extracted regions vs. original image)

---

## Deliverables

1. Python pipeline module for raster → regions
2. Python pipeline module for SVG → regions
3. Visual comparison outputs (overlay images showing extracted regions)
4. Comparison scorecard per bake-off
5. **Design recommendation:** Best quantization + vectorization + SVG parsing approaches

---

## Estimated Effort

2-3 sessions with Claude

## Dependencies

None — independent of POCs 1 & 2, can run in parallel.

## Risk

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| Color quantization loses important detail | **Medium** — operator must manually fix | Medium | Tests 4 approaches; edge case testing with fine-detail logos |

---

## Reference Documents

- [Embroidery File Generation Deep Research Brief](./Embroidery_File_Generation_Deep_Research.md)
