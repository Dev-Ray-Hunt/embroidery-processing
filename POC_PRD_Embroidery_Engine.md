# Embroidery Engine: Proof of Concept PRD

## Product Requirements Document — POC Phase

---

## Executive Summary

This document defines a series of 8 proof-of-concept projects that systematically validate the technical feasibility of building a custom embroidery file generation and management system for Straight Down's Barudan machine operation. Each POC is designed to prove a specific capability, **bake-off competing implementation approaches** with scored evaluations, and produce a design document that blueprints the corresponding MVP module.

The POCs are sequenced by risk — the highest-uncertainty items are tested first so that fatal blockers are discovered before downstream effort is invested. Each POC is a self-contained, runnable Python project with clear inputs, outputs, and pass/fail criteria.

**Broader Vision:** These POCs form the technical core of a future end-to-end embroidery production platform that integrates with NetSuite for order management, provides customer-facing proof approval, supports team-member design adjustment, and manages production dispatch to Barudan machines via BNet software.

---

## Global Constraints

| Constraint | Value |
|-----------|-------|
| **Builder** | Brandon + Claude/AI agents |
| **Primary language** | Python 3.10+ (backend/engine) |
| **Frontend** | HTML/CSS/JS (where visualization is needed) |
| **Target machine** | Barudan embroidery machines via BNet software |
| **Primary output format** | DST (Tajima) — universal compatibility |
| **Thread brand** | Madeira (Classic Rayon 40, Polyneon) |
| **Input types** | SVG vector files, PNG/JPG raster logos |
| **Hardware validation** | Barudan machines available in-house for live stitch testing |
| **Evaluation priority** | 1. Reliability → 2. Quality → 3. Speed → 4. Flexibility |

### Evaluation Scoring Framework

Every bake-off option in every POC is scored on these four dimensions using a 1-5 scale:

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

## POC 1: DST Smoke Test

### Objective
Prove that we can programmatically generate a DST file that a Barudan machine will accept, load, and stitch correctly.

### Why This Is First
If we can't write a valid DST file that the machine accepts, nothing else matters. This is the single highest-risk validation.

### What To Build
A Python script that generates hardcoded geometric shapes as stitch patterns and writes them to DST files.

### Test Designs
1. **Filled rectangle** (50mm × 30mm) — Tests fill stitch generation and DST encoding
2. **Filled circle** (40mm diameter) — Tests curved-boundary fill handling
3. **Satin-stitched border** (2mm wide rectangle outline) — Tests satin stitch encoding
4. **Multi-color design** (two rectangles, different colors) — Tests color-change commands
5. **Running stitch outline** (star shape) — Tests running stitch encoding

### Bake-Off: DST Writing Approaches

| Option | Description | What To Test |
|--------|-------------|-------------|
| **A. pyembroidery** | Use pyembroidery's `write()` function with `EmbPattern` objects | Generate all 5 test designs, write to DST, validate on machine |
| **B. libembroidery (via Python wrapper)** | Use libembroidery's C library through ctypes/cffi | Same 5 designs, compare output file byte-for-byte with Option A |
| **C. Custom DST writer** | Write our own DST encoder following the spec from the research doc | Same 5 designs, validate header/body structure, test on machine |

### Pass/Fail Criteria
- [ ] All 5 DST files load without error on Barudan machine
- [ ] All 5 designs stitch correctly (correct shapes, no thread breaks from bad encoding)
- [ ] Color changes occur at the correct points in the multi-color design
- [ ] Stitch count in header matches actual stitch records in body
- [ ] File passes `(file_size - 512) % 3 == 0` validation

### Measurements To Record
- File size per design
- Processing time per design
- Machine load time (subjective: instant / noticeable delay / slow)
- Any machine errors or warnings displayed
- Stitch quality assessment (photo the stitched output)

### Deliverables
1. Python script(s) for each approach
2. 5 DST files per approach (15 total)
3. Photos of stitched output from each approach
4. Comparison scorecard (Reliability / Quality / Speed / Flexibility)
5. **Design recommendation:** Which DST writing approach to use for MVP

### Estimated Effort
1-2 sessions with Claude

---

## POC 2: Stitch Generation Algorithm Bake-Off

### Objective
Prove that we can take a vector shape (SVG path/polygon) and generate production-quality fill, satin, and running stitch patterns.

### Why This Is Second
Once we know DST writing works (POC 1), the next risk is whether our stitch generation algorithms produce stitches that look good when sewn. Bad algorithms = bad embroidery regardless of file format.

### What To Build
A Python module that accepts Shapely polygons and generates stitch coordinates for three stitch types: fill, satin, and running stitch.

### Test Designs
1. **Large fill region** — Square, 60mm × 60mm, fill stitch at 45°
2. **Small fill region** — Circle, 15mm diameter (tests minimum-area handling)
3. **Narrow column** — 3mm × 40mm rectangle, satin stitch
4. **Curved column** — S-curve path, 4mm wide, satin stitch
5. **Outline** — Star shape perimeter, running stitch
6. **Multi-region** — Simple logo with 3 colors, mixed stitch types

### Bake-Off: Fill Stitch Algorithms

| Option | Description | Source |
|--------|-------------|--------|
| **A. Custom scanline fill** | Build our own using the algorithm from the research doc (parallel lines clipped to polygon) | Research doc Section 8.1 |
| **B. Ink/Stitch auto-fill** | Extract and use Ink/Stitch's `auto_fill.py` module (Shapely + NetworkX graph-based) | `inkstitch/lib/stitches/auto_fill.py` |
| **C. stitch-generator library** | Use `stitch-generator`'s path-based fill effects | PyPI `stitch-generator` |
| **D. PEmbroider-style parallel** | Port PEmbroider's PARALLEL hatch algorithm from Java to Python | PEmbroider API reference |

### Bake-Off: Satin Stitch Algorithms

| Option | Description | Source |
|--------|-------------|--------|
| **A. Custom dual-rail zigzag** | Our own implementation from research doc Section 8.2 | Research doc |
| **B. Ink/Stitch satin column** | Extract Ink/Stitch's satin_column.py | GitHub |
| **C. stitch-generator satin** | Use `stitch-generator`'s satin path effect | PyPI |

### Pass/Fail Criteria
- [ ] All designs stitch cleanly on Barudan (no thread breaks from bad stitch sequences)
- [ ] Fill stitch covers the target region completely (no visible gaps)
- [ ] Satin stitch produces clean, even columns (no irregular zigzags)
- [ ] Running stitch follows the path accurately
- [ ] Multi-region design has correct stitch sequencing and color changes

### Measurements To Record
- Total stitch count per algorithm per design
- Processing time per algorithm per design
- Visual quality assessment (1-5, with photos)
- Edge coverage quality (gaps at polygon boundaries)
- Jump stitch count (fewer = better)
- Stitched output photos (side-by-side comparison)

### Deliverables
1. Python module with all algorithm implementations
2. DST files for every algorithm × design combination
3. Side-by-side photos of stitched output
4. Comparison scorecard with weighted scores
5. **Design recommendation:** Which algorithm(s) to use for each stitch type in the MVP

### Estimated Effort
2-3 sessions with Claude

### Dependencies
- POC 1 complete (need validated DST writer)

---

## POC 3: Image-to-Regions Pipeline

### Objective
Prove that we can take a raster logo image (PNG/JPG), reduce it to a limited color palette, extract vector regions for each color, and classify each region by stitch type.

### Why This Is Third
This is the "input side" of the pipeline. If we can't reliably go from image → regions → stitch type assignments, the auto-generation feature doesn't work.

### What To Build
A Python module that takes an image file and outputs a list of classified vector regions ready for stitch generation.

### Test Images
1. **Simple 2-color logo** — Black text/icon on white background
2. **3-4 color corporate logo** — Clean edges, solid fills
3. **Logo with gradients** — Tests color quantization handling of non-solid areas
4. **Logo with fine detail** — Thin lines, small text, intricate shapes
5. **SVG version of logo #2** — Bypass raster processing, test SVG parsing directly

### Bake-Off: Color Quantization

| Option | Description |
|--------|-------------|
| **A. K-Means in LAB space** | scikit-learn KMeans on CIELAB-converted pixels |
| **B. K-Means in RGB space** | Simpler, but perceptually non-uniform |
| **C. Median Cut** | Recursive color space subdivision (PIL/Pillow's `quantize()`) |
| **D. Pre-defined palette matching** | Skip clustering, match every pixel to nearest Madeira thread color directly |

### Bake-Off: Vectorization

| Option | Description |
|--------|-------------|
| **A. OpenCV contour tracing** | `findContours` + Douglas-Peucker simplification → Shapely polygons |
| **B. Potrace (via potracer)** | Bitmap tracing library used by Inkscape, produces smooth Bezier outlines |
| **C. scikit-image marching squares** | `find_contours()` with level-set approach |

### Bake-Off: SVG Parsing (for vector input)

| Option | Description |
|--------|-------------|
| **A. svgpathtools** | Python library for parsing SVG paths to Bezier curves |
| **B. cairosvg + Shapely** | Render SVG to paths via Cairo, convert to Shapely geometries |
| **C. Inkscape CLI** | Use Inkscape's command-line to convert SVG → simplified SVG with just paths |

### Pass/Fail Criteria
- [ ] All test images produce valid Shapely polygons for each color region
- [ ] Region boundaries match the original image with < 1mm deviation at embroidery scale
- [ ] Color quantization produces distinct, reasonable color assignments
- [ ] Small regions (< 3mm²) are correctly classified as "running stitch" or filtered out
- [ ] SVG input produces equivalent regions to raster input for the same logo
- [ ] Processing completes in < 30 seconds for a typical logo

### Measurements To Record
- Number of regions extracted per image
- Polygon vertex count per region (simpler = better for stitch generation)
- Color accuracy (Delta-E between quantized colors and original)
- Processing time per approach
- Visual overlay comparison (extracted regions vs. original image)

### Deliverables
1. Python pipeline module for raster → regions
2. Python pipeline module for SVG → regions
3. Visual comparison outputs (overlay images showing extracted regions)
4. Comparison scorecard per bake-off
5. **Design recommendation:** Best quantization + vectorization + SVG parsing approaches

### Estimated Effort
2-3 sessions with Claude

### Dependencies
- None (independent of POC 1 & 2, can run in parallel if desired)

---

## POC 4: Stitch Preview Renderer Bake-Off

### Objective
Prove that we can render a DST file as a realistic visual preview suitable for customer proof approval. Test multiple rendering approaches to find the right quality/speed tradeoff.

### Why This Is Fourth
Customer approval requires a visual proof. If the preview doesn't look enough like the real stitched product, customers will either reject good designs or approve bad ones. The preview quality directly impacts business workflow.

### What To Build
Multiple rendering implementations that take a DST file (or stitch coordinate data) and produce a visual preview image.

### Test Inputs
- DST files from POC 1 and POC 2 (machine-validated designs)
- At least one commercially-digitized DST file (as a quality benchmark)
- Multiple fabric backgrounds (white piqué, black twill, navy denim)

### Bake-Off: Rendering Approaches

| Option | Description | Tech |
|--------|-------------|------|
| **A. pyembroidery PNG** | Use pyembroidery's built-in PNG writer | Python, zero custom code |
| **B. Pillow 2D with shading** | Custom renderer: thick lines + angle-based brightness shading | Python + Pillow |
| **C. Cairo 2D with antialiasing** | Cairo vector renderer with smooth lines and transparency | Python + PyCairo |
| **D. Canvas 2D (browser)** | HTML5 Canvas renderer with rounded line caps and color shading | JS, browser-based |
| **E. WebGL/Three.js 2.5D** | Three.js scene with fabric plane, instanced stitch geometry, Kajiya-Kay shader | JS + Three.js |
| **F. POV-Ray 3D** | Ray-traced 3D thread geometry using the POV-Ray Thread project approach | POV-Ray scripts |

### Evaluation Criteria (specific to rendering)

| Criterion | Weight | Description |
|-----------|--------|-------------|
| **Visual fidelity** | 5 | How close does the preview look to the actual stitched product? |
| **Rendering speed** | 4 | Time from DST input to rendered image output |
| **Fabric interaction** | 3 | Can it show the design on different fabric backgrounds? |
| **Interactivity** | 3 | Can the user zoom, pan, rotate the preview? |
| **Implementation effort** | 2 | How much code/setup is needed? |
| **Scalability** | 2 | Does it handle large designs (50k+ stitches) without choking? |

### Pass/Fail Criteria
- [ ] At least one approach produces previews that a non-technical person would recognize as "this is what the embroidery will look like"
- [ ] Preview renders in < 10 seconds for a 20k-stitch design
- [ ] Thread colors in the preview visually match the Madeira thread colors
- [ ] Fill stitch direction is visible in the preview (shading changes with angle)
- [ ] Design can be shown on at least 3 different fabric backgrounds

### Measurements To Record
- Rendering time per approach per design
- Side-by-side comparison: preview vs. photo of actual stitched output
- User preference ranking (show previews to team members, get reactions)
- Maximum stitch count before performance degrades
- File size of output image/page

### Deliverables
1. Implementation of each rendering approach
2. Gallery of rendered previews (all approaches × all test designs × all fabrics)
3. Side-by-side: digital preview vs. photo of stitched product
4. Comparison scorecard
5. **Design recommendation:** Primary renderer for customer proofs + secondary for internal use

### Estimated Effort
3-4 sessions with Claude

### Dependencies
- POC 1 complete (need valid DST files)
- POC 2 helpful but not required (can use any valid DST)

---

## POC 5: Thread Catalogue + Color Matching

### Objective
Build a Madeira thread color database and prove that automated color matching (Delta-E in CIELAB) produces acceptable thread selections from arbitrary design colors.

### Why This Is Fifth
Color management underpins the entire system. If the auto-selected thread colors don't match customer expectations, every proof will need manual color correction.

### What To Build
1. A JSON-based Madeira thread catalogue with RGB values, catalog numbers, color names, and optical properties
2. A color matching engine using CIEDE2000 Delta-E in CIELAB space
3. A simple web UI showing the design colors, matched threads, and Delta-E scores

### Data Collection Tasks
1. **Parse Isacord RGB PDF** (as validation reference — best documented brand)
2. **Parse Madeira RGB data** from Metro chart and EZ Stitch resources
3. **Cross-reference** Madeira catalog numbers against at least one other source for validation
4. **Photograph 10 Madeira thread spools** under controlled lighting for RGB validation

### Bake-Off: Color Matching Algorithms

| Option | Description |
|--------|-------------|
| **A. CIEDE2000 in CIELAB** | Industry standard, perceptually uniform, handles hue/chroma/lightness |
| **B. CIE76 (simple Euclidean in LAB)** | Simpler math, less accurate for saturated colors |
| **C. Euclidean in RGB** | Simplest, worst perceptual accuracy (baseline comparison) |
| **D. CMC l:c (textile industry)** | Developed specifically for textile color matching |

### Bake-Off: Palette Optimization

| Option | Description |
|--------|-------------|
| **A. Greedy nearest-match** | Match each design color independently to closest thread |
| **B. Constrained palette optimization** | Limit to N threads total, optimize overall palette to minimize worst-case Delta-E |
| **C. Perceptual clustering** | Group similar design colors and assign one thread per cluster |

### Pass/Fail Criteria
- [ ] Madeira catalogue contains ≥ 200 threads with validated RGB values
- [ ] Color matching produces Delta-E < 3.5 for 90%+ of common logo colors
- [ ] Matched thread colors are visually acceptable when compared to physical thread spools
- [ ] System correctly handles edge cases: very dark colors, very light colors, neon/fluorescent
- [ ] Web UI displays design colors next to matched thread swatches

### Measurements To Record
- Catalogue completeness (% of Madeira Classic Rayon 40 + Polyneon covered)
- Delta-E distribution across 50 random test colors
- Delta-E distribution across 10 real customer logos
- Time to match a full design palette
- User validation: do team members agree with the auto-selected threads?

### Deliverables
1. `madeira_catalogue.json` — Complete thread database
2. Color matching Python module
3. Web UI for color matching visualization
4. Comparison scorecard for matching algorithms
5. **Design recommendation:** Which matching algorithm + palette strategy for MVP

### Estimated Effort
2-3 sessions with Claude

### Dependencies
- None (independent, can run in parallel with POCs 1-4)

---

## POC 6: Interactive Region Editor

### Objective
Prove that a web-based editor can let a team member click on design regions, modify their stitch properties (type, color, angle, density), and see the preview update.

### Why This Is Sixth
This is the human-in-the-loop step in the production workflow. The auto-generated design gets refined by a team member before going to the customer. If this editor is too slow, too clunky, or doesn't provide enough control, the whole workflow breaks down.

### What To Build
A web application with:
- Canvas/SVG rendering of design regions
- Click-to-select regions
- Property panel per region (stitch type, thread color from Madeira palette, fill angle, density)
- Real-time preview re-render when properties change
- Export modified design data

### Bake-Off: Frontend Rendering

| Option | Description |
|--------|-------------|
| **A. SVG + vanilla JS** | Regions as SVG paths, click handlers, CSS property panel |
| **B. HTML Canvas + React** | Canvas rendering with React state management |
| **C. Three.js + React** | 3D-capable renderer with React UI |
| **D. Fabric.js** | Canvas library built for interactive object manipulation |

### Pass/Fail Criteria
- [ ] User can click any region and see it highlighted
- [ ] Changing stitch type updates the preview within 2 seconds
- [ ] Changing thread color shows the new color immediately
- [ ] Changing fill angle visually changes the stitch direction in preview
- [ ] Design with 10+ regions loads and renders in < 3 seconds
- [ ] Modified design can be exported as updated stitch data

### Measurements To Record
- Time to initial render
- Time to re-render after property change
- Maximum region count before UI becomes sluggish
- Team member feedback on usability (informal user testing)

### Deliverables
1. Web application (Python backend + JS frontend)
2. Demo with at least 3 test designs
3. Frontend approach comparison scorecard
4. **Design recommendation:** Frontend framework and rendering approach for MVP editor

### Estimated Effort
3-4 sessions with Claude

### Dependencies
- POC 2 (stitch generation algorithms)
- POC 3 (region extraction pipeline)
- POC 4 (renderer for preview)
- POC 5 (thread catalogue for color picker)

---

## POC 7: End-to-End Pipeline Integration

### Objective
Prove the entire chain works: image input → auto-generation → preview → adjustment → DST export + proof image — as one continuous process.

### Why This Is Seventh
Individual components working in isolation doesn't guarantee they integrate smoothly. This POC stress-tests the interfaces between every module and measures end-to-end performance.

### What To Build
A single web application that orchestrates the full pipeline:

1. **Upload** — User uploads a PNG/JPG/SVG logo
2. **Process** — Backend runs: image preprocessing → color quantization → vectorization → stitch type classification → stitch generation → DST creation → preview rendering
3. **Preview** — Frontend displays the rendered preview with fabric background
4. **Adjust** — Team member can modify regions (from POC 6 editor)
5. **Export** — Generate final DST file + high-quality proof image (PNG/PDF)

### Test Scenarios
1. **Happy path** — Clean 3-color SVG logo → DST + preview in under 60 seconds
2. **Raster logo** — 4-color PNG logo with transparent background
3. **Edge case: many colors** — Logo with 8+ colors that need reduction
4. **Edge case: fine detail** — Logo with thin lines and small text
5. **Edge case: large design** — 200mm × 200mm design (max common hoop size)

### Pass/Fail Criteria
- [ ] End-to-end processing completes for all 5 test scenarios
- [ ] Total time from upload to preview display < 120 seconds
- [ ] Generated DST files stitch correctly on Barudan machine
- [ ] Preview image matches stitched output at an acceptable level
- [ ] Proof export produces a shareable PNG or PDF suitable for customer email
- [ ] No data loss or corruption when passing data between pipeline stages

### Measurements To Record
- End-to-end processing time (broken down by stage)
- Memory usage peak during processing
- File sizes (input image, intermediate data, DST output, preview image)
- Error rate across test scenarios
- Bottleneck identification (which stage is slowest?)

### Deliverables
1. Integrated web application
2. Performance profiling report (time per pipeline stage)
3. Stitched output photos for all 5 test scenarios
4. Side-by-side: preview vs. stitched photo
5. **Design recommendation:** Architecture for MVP pipeline (what to optimize, what to parallelize, what to cache)

### Estimated Effort
3-4 sessions with Claude

### Dependencies
- All previous POCs (1-6) complete

---

## POC 8: Lightweight Order Workflow

### Objective
Prove that the embroidery engine can be wrapped in a basic order-driven workflow: receive an order with artwork, generate a proof, email it for approval, and track the approval status.

### Why This Is Last
This is the lowest-risk POC — it's standard web application development. The business logic is straightforward. But it validates that the technical engine can be embedded in a production business workflow.

### What To Build
A simple web application with:

1. **Order entry form** — Customer name, order number, product type, artwork upload, placement instructions
2. **Auto-generation trigger** — On upload, run the embroidery pipeline (POC 7) to generate DST + preview
3. **Team review page** — Show generated preview, allow region adjustments, approve for customer
4. **Proof email** — Send proof image to customer email with approve/reject links
5. **Approval tracking** — Dashboard showing order status (pending / approved / rejected / in production)

### Bake-Off: Email/Notification Approach

| Option | Description |
|--------|-------------|
| **A. SMTP direct** | Send emails directly via Python `smtplib` |
| **B. SendGrid/Mailgun API** | Transactional email service for reliable delivery |
| **C. Microsoft Graph API** | Send via Outlook (aligns with existing Microsoft stack) |

### Bake-Off: Data Storage

| Option | Description |
|--------|-------------|
| **A. SQLite** | Simplest, file-based, zero setup. Good for POC. |
| **B. PostgreSQL** | Production-grade, ready for MVP without migration |
| **C. JSON flat files** | Absolute simplest for POC. Not scalable. |

### Future Integration Notes (Not POC Scope)
- **NetSuite integration:** Orders currently live in NetSuite. Future MVP will pull order data from NetSuite API or push approval status back. For the POC, order data is entered manually.
- **BNet dispatch:** Future MVP will send approved DSTs to BNet for machine dispatch. For POC, DST is downloaded manually and loaded via BNet's normal workflow.

### Pass/Fail Criteria
- [ ] Team member can enter an order and upload artwork
- [ ] System auto-generates preview and DST within 2 minutes
- [ ] Proof email is delivered to a test email address with preview image
- [ ] Customer can click "approve" in email and status updates in the dashboard
- [ ] Dashboard correctly shows all orders and their current status
- [ ] At least 5 test orders can be processed without data corruption

### Deliverables
1. Web application (Flask/FastAPI backend + simple HTML frontend)
2. Demo with 5 test orders through the complete workflow
3. Email template for customer proof approval
4. Comparison scorecard for email and storage approaches
5. **Design recommendation:** Tech stack for MVP workflow layer

### Estimated Effort
2-3 sessions with Claude

### Dependencies
- POC 7 complete (integrated pipeline)

---

## POC Dependency Graph

```
                    POC 1: DST Smoke Test
                           │
                    POC 2: Stitch Generation ──────┐
                           │                       │
   POC 3: Image Pipeline ──┤       POC 5: Thread   │
          (parallel)       │       Catalogue        │
                           │       (parallel)       │
                    POC 4: Preview Renderer ────────┤
                           │                       │
                    POC 6: Region Editor ───────────┘
                           │
                    POC 7: End-to-End Integration
                           │
                    POC 8: Order Workflow
```

**Parallelization opportunities:**
- POC 3 (Image Pipeline) and POC 5 (Thread Catalogue) can run in parallel with POCs 1-2 since they have no dependencies
- POC 4 (Renderer) can begin as soon as POC 1 produces valid DST files
- POCs 1 and 2 are strictly sequential (2 needs 1's validated DST writer)

---

## Timeline Estimate

| POC | Sessions | Depends On | Can Parallel With |
|-----|----------|-----------|-------------------|
| **1. DST Smoke Test** | 1-2 | None | 3, 5 |
| **2. Stitch Generation** | 2-3 | POC 1 | 3, 5 |
| **3. Image Pipeline** | 2-3 | None | 1, 2, 4, 5 |
| **4. Preview Renderer** | 3-4 | POC 1 | 3, 5 |
| **5. Thread Catalogue** | 2-3 | None | 1, 2, 3, 4 |
| **6. Region Editor** | 3-4 | POCs 2-5 | — |
| **7. End-to-End** | 3-4 | POCs 1-6 | — |
| **8. Order Workflow** | 2-3 | POC 7 | — |
| **Total** | **18-26 sessions** | | |

**Critical path:** POC 1 → POC 2 → POC 6 → POC 7 → POC 8 (12-16 sessions)

**Fastest completion:** Run POCs 3 and 5 in parallel with POCs 1-2, then POC 4 in parallel with POC 3's later stages. This compresses the timeline by overlapping independent work.

---

## Risk Register

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| DST files rejected by Barudan | **Critical** — blocks everything | Low (format is well-spec'd) | POC 1 is first; use pyembroidery's battle-tested writer |
| Fill stitch quality too low for production | **High** — auto-generation becomes unusable | Medium | POC 2 bake-off tests 4 algorithms; fallback is Ink/Stitch's proven approach |
| Color quantization loses important detail | **Medium** — operator must manually fix | Medium | POC 3 tests 4 approaches; edge case testing with fine-detail logos |
| Preview doesn't match stitched output | **Medium** — customer approval unreliable | Medium | POC 4 side-by-side comparison validates preview fidelity |
| Madeira RGB data inaccurate | **Medium** — color matching unreliable | Low-Medium | POC 5 validates against physical thread spools |
| End-to-end too slow | **High** — blocks production use | Unknown (POC measures) | POC 7 profiles each stage; optimize bottleneck identified |
| Pipeline integration failures | **High** — components don't fit together | Medium | POC 7 explicitly tests integration; standardize data formats between modules early |

---

## Success Criteria for POC Phase

The POC phase is successful if:

1. **At least one approach per component** scores ≥ 30/50 on the weighted evaluation
2. **End-to-end processing** (POC 7) completes in < 3 minutes for a typical 3-color logo
3. **Machine validation** — generated DST files stitch correctly on Barudan for ≥ 90% of test designs
4. **Preview accuracy** — team members rate the preview as "acceptable for customer proofs" for ≥ 80% of designs
5. **Color matching** — auto-selected threads have Delta-E < 3.5 for ≥ 90% of design colors against Madeira palette
6. **Design documents produced** — each POC outputs a clear recommendation with evidence for the MVP build

---

## Appendix: Reference Documents

- [Embroidery File Generation Deep Research Brief](./Embroidery_File_Generation_Deep_Research.md) — Technical research covering DST format specification, open-source libraries, stitch generation algorithms, visualization approaches, and thread catalogue data sources
