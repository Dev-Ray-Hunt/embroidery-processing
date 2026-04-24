# POC 1: DST Renderer Bake-Off

## Proof of Concept — Project Document

---

## Objective

Prove that we can take an existing DST file and render it as a realistic visual preview suitable for customer proof approval. Test multiple rendering approaches to find the right quality/speed tradeoff.

## Why This Is First

Everything downstream depends on being able to show what the embroidery looks like. The color-up editor (POC 3) needs a renderer to display the design. The proof approval workflow (POC 4) needs a proof image to send for approval. If we can't render a DST file into something a customer would recognize as "this is what your embroidery will look like," the rest of the system doesn't work.

---

## Background

DST (Tajima) files are the standard format used by Barudan embroidery machines. A DST file contains:

- **Stitch coordinates** — Relative X/Y movements that define each stitch
- **Color-change commands** — Markers that tell the machine to switch to the next needle/thread
- **Jump stitches** — Long moves without stitching (connecting distant parts of the design)
- **Trim commands** — Cut the thread between sections
- **A 512-byte header** — Design metadata (stitch count, extents, etc.)

The renderer's job is to read these stitch coordinates and color changes, then draw them as realistic thread lines on a fabric background. The key challenge is making flat 2D lines look like actual embroidered thread — this means considering thread width, stitch angle, shading to simulate thread luster, and fabric texture underneath.

Straight Down's designs are digitized in Wilcom EmbroideryStudio and exported as DST files. We are **not** generating DST files — we are rendering existing ones.

---

## Global Constraints

| Constraint | Value |
|-----------|-------|
| **Builder** | Brandon + Claude/AI agents |
| **Primary language** | Python 3.10+ (backend rendering) |
| **Frontend** | HTML/CSS/JS (browser-based rendering options) |
| **Input format** | DST (Tajima) files from Wilcom EmbroideryStudio |
| **Thread brand** | Madeira (Classic Rayon 40, Polyneon) |
| **Evaluation priority** | 1. Reliability → 2. Quality → 3. Speed → 4. Flexibility |

---

## Test Inputs

### DST Files

Source real production DST files from Straight Down's existing library. Select at minimum:

1. **Simple text logo** — Text only, 2 colors, < 5,000 stitches. Tests basic rendering and readability of small letterforms.
2. **Multi-color logo with fills** — 3-4 colors, mix of fill regions and satin borders, 10k-20k stitches. Tests color differentiation and fill rendering.
3. **Complex detailed design** — 4+ colors, fine detail, 30k+ stitches. Stress-tests rendering performance and visual clarity at high stitch counts.

If possible, also include:
4. **Hat/cap design** — Smaller format, often has different stitch characteristics
5. **Large back design** — If available, 50k+ stitches for performance benchmarking

### Fabric Backgrounds

Each rendering approach should be tested against at minimum three fabric backgrounds:

1. **White piqué** — Standard polo fabric, light background
2. **Black twill** — Dark background, tests thread color visibility
3. **Navy denim/twill** — Mid-tone background, common garment color

For the POC, fabric backgrounds can be solid colors or simple texture images. Photorealistic fabric rendering is not required — the goal is to see how the design looks on light, dark, and mid-tone garments.

### Validation Reference

Photograph the actual stitched output of at least one test design on a real garment. This becomes the "ground truth" for comparing rendering quality.

---

## Bake-Off: Rendering Approaches

### Option A: pyembroidery Built-in PNG

**Description:** Use pyembroidery's `write_png()` function. Zero custom code — just load the DST and export a PNG.

**What to evaluate:**
- Load DST file with `pyembroidery.read("design.dst")`
- Write to PNG with `pyembroidery.write("output.png")`
- Test with default settings and any available configuration options

**Pros:** Zero effort, well-tested library, handles all DST parsing automatically.
**Cons:** Limited control over rendering quality, likely basic line rendering without thread realism.

**Tech:** Python, pyembroidery

---

### Option B: Pillow 2D with Thread Shading

**Description:** Custom Python renderer using Pillow (PIL). Draw each stitch as a thick line with angle-based brightness shading to simulate how light reflects off embroidery thread at different stitch angles.

**What to build:**
1. Parse DST using pyembroidery to extract stitch coordinates and color changes
2. For each stitch segment, draw a thick line (line width proportional to thread weight)
3. Apply brightness shading based on stitch angle — stitches running left-right appear brighter than stitches running top-bottom (simulating directional light on thread luster)
4. Draw on a fabric-colored background
5. Support configurable thread colors (RGB values from thread catalogue)

**Key implementation details:**
- Line width: ~0.4mm at embroidery scale (map to pixel width based on output DPI)
- Shading: calculate angle of each stitch segment, map to brightness modifier (e.g., 0° = bright, 90° = darker)
- Anti-aliasing: Pillow's line drawing is basic — may need to render at 2x and downsample

**Pros:** Full control over rendering, pure Python, no browser needed, can generate images server-side.
**Cons:** More code to write, Pillow's drawing primitives are basic, may look flat.

**Tech:** Python, Pillow, pyembroidery (for DST parsing)

---

### Option C: Cairo 2D with Antialiasing

**Description:** Use PyCairo (Python bindings for the Cairo 2D graphics library) for high-quality antialiased vector rendering. Cairo supports line caps, gradients, transparency, and sub-pixel rendering.

**What to build:**
1. Parse DST using pyembroidery
2. Create a Cairo surface at target resolution
3. For each stitch, draw with rounded line caps and configurable width
4. Apply per-stitch color with optional transparency for overlapping regions
5. Layer on a fabric background

**Key implementation details:**
- Cairo's `LINE_CAP_ROUND` gives smooth stitch endpoints
- Can layer semi-transparent stitches to show overlap/density
- Vector-based rendering means output can be any resolution
- Can export as PNG, SVG, or PDF

**Pros:** Much better antialiasing than Pillow, smooth lines, professional output, resolution-independent.
**Cons:** PyCairo is an additional dependency, still fundamentally 2D flat rendering.

**Tech:** Python, PyCairo, pyembroidery

---

### Option D: HTML5 Canvas (Browser-Based)

**Description:** Browser-based renderer using HTML5 Canvas API. Render stitches as thick lines with rounded caps. Adds interactivity — user can zoom, pan, and hover over regions.

**What to build:**
1. Python backend parses DST and serves stitch data as JSON (coordinates + color changes)
2. JavaScript frontend draws stitches on a Canvas element
3. Implement zoom/pan with mouse wheel and drag
4. Optionally: hover to highlight a color region, click to select (useful for POC 3)

**Key implementation details:**
- Canvas `lineCap = "round"` for smooth stitch ends
- `lineWidth` mapped to thread weight at current zoom level
- Batch drawing by color for performance (minimize context switches)
- Fabric background as a CSS background or drawn first on canvas
- For large designs (50k+ stitches), consider WebGL fallback or level-of-detail rendering

**Pros:** Interactive (zoom/pan), runs in browser, can be extended for POC 3 editor, good rendering quality.
**Cons:** Requires browser, performance ceiling for very large designs, more code.

**Tech:** JavaScript, HTML5 Canvas, Python backend (FastAPI) for DST parsing

---

### Option E: WebGL / Three.js 2.5D

**Description:** Three.js scene with a flat fabric plane and instanced stitch geometry. Each stitch is a thin 3D cylinder or ribbon placed on the fabric surface. A thread-shading material (Kajiya-Kay or similar) simulates realistic thread luster.

**What to build:**
1. Python backend parses DST and serves stitch data as JSON
2. Three.js scene: fabric plane with texture, camera looking straight down
3. Each stitch as an instanced mesh (thin cylinder or extruded rectangle)
4. Custom shader for thread appearance (anisotropic reflection along stitch direction)
5. Interactive camera: zoom, pan, slight tilt for 2.5D perspective

**Key implementation details:**
- Instanced rendering is critical for performance with thousands of stitches
- Kajiya-Kay shader models how light reflects along a fiber/thread direction
- Can show subtle height variation (stitches slightly raised off fabric)
- Camera default: top-down orthographic; optional slight perspective for depth

**Pros:** Most realistic rendering possible, hardware-accelerated, interactive, impressive visual quality.
**Cons:** Most complex to build, requires WebGL support, shader programming, may be over-engineered for POC.

**Tech:** JavaScript, Three.js, GLSL shaders, Python backend for DST parsing

---

## Evaluation Criteria

| Criterion | Weight | What 5 Looks Like | What 1 Looks Like |
|-----------|--------|-------------------|-------------------|
| **Visual fidelity** | 5 | Preview is nearly indistinguishable from a photo of the stitched product | Looks like colored lines on a white background |
| **Rendering speed** | 4 | < 2 seconds for a 20k-stitch design | > 30 seconds or timeout |
| **Fabric interaction** | 3 | Design looks natural on any fabric color/texture | Only works on white background |
| **Interactivity** | 3 | Zoom, pan, hover-to-highlight, click-to-select regions | Static image only |
| **Implementation effort** | 2 | Under 100 lines of code, works out of the box | Multiple days of coding, fragile |
| **Scalability** | 2 | Handles 100k+ stitches smoothly | Chokes on 10k+ stitches |

**Weighted score formula:** `(Reliability × 4) + (Quality × 3) + (Speed × 2) + (Flexibility × 1)`

Maximum possible score: 50. Minimum viable for MVP selection: 30.

---

## Pass/Fail Criteria

- [ ] At least one approach produces previews that a non-technical person would recognize as "this is what the embroidery will look like"
- [ ] Preview renders in < 10 seconds for a 20k-stitch design
- [ ] Thread colors in the preview visually match the Madeira thread colors
- [ ] Fill stitch direction is visible in the preview (shading changes with angle)
- [ ] Design can be shown on at least 3 different fabric backgrounds
- [ ] DST files from Wilcom parse correctly (stitch counts match Wilcom's reported values)

---

## Measurements To Record

For each rendering approach × each test design:

| Measurement | How |
|-------------|-----|
| Rendering time | Timed from DST load to image/canvas ready |
| Visual quality (1-5) | Side-by-side with stitched photo, rated by Brandon + team |
| Stitch count accuracy | Compare parsed stitch count to Wilcom's reported count |
| File size | Output image file size in KB |
| Max stitches before degradation | Increase design complexity until rendering breaks/lags |
| Fabric background quality | Subjective rating on white, black, navy |

Also collect:
- Side-by-side photos: digital preview vs. photo of actual stitched output
- Team member preference ranking (show all approaches, ask which they'd send to a customer)

---

## Implementation Plan

### Step 1: DST Parsing Foundation
- Install pyembroidery
- Write a utility that loads a DST file and extracts: stitch coordinates, color changes, jump stitches, metadata (stitch count, extents)
- Validate against Wilcom's reported values for the test files
- Output a JSON format that all renderers can consume

### Step 2: Implement Each Renderer
- Build options A through E (or a subset if time is constrained — A, B, and D are the minimum)
- Each renderer takes the same JSON stitch data as input
- Each produces output on the same 3 fabric backgrounds

### Step 3: Evaluation
- Run all renderers against all test designs
- Photograph stitched output for comparison
- Fill out the scorecard
- Get team feedback

### Step 4: Design Recommendation
- Select primary renderer (for proof images — likely a server-side option)
- Select secondary renderer (for interactive use — likely browser-based)
- Document the recommendation with evidence

---

## Deliverables

1. DST parsing utility (Python, reusable across all renderers)
2. Implementation of each rendering approach
3. Gallery of rendered previews (all approaches × all test designs × all fabrics)
4. Side-by-side comparison: digital preview vs. photo of stitched product
5. Evaluation scorecard with weighted scores
6. **Design recommendation document:** Primary renderer for proof images + secondary for interactive/editor use

---

## Estimated Effort

3-4 sessions with Claude

## Dependencies

None — this is the first POC.

## Risk

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| No renderer looks good enough for customer proofs | **High** — blocks proof workflow | Medium | Testing 5 approaches; at least one should be sufficient. Can also fall back to using Wilcom's own preview export. |
| DST parsing fails on some Wilcom files | **Medium** — limits which designs work | Low | pyembroidery is well-tested; Tajima DST is a simple, well-documented format |
| Performance issues with large designs | **Medium** — limits usability | Medium | Browser-based options can use WebGL acceleration; server-side can render in background |

---

## Reference Documents

- [POC PRD: Coloring Up Engine](./POC_PRD_Coloring_Up_Engine.md) — Parent PRD
- [Blue Sky Archive/Embroidery_File_Generation_Deep_Research.md](./Blue Sky Archive/Embroidery_File_Generation_Deep_Research.md) — DST format specification details
