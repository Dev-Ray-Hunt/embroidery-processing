# POC 4: Stitch Preview Renderer Bake-Off

## Proof of Concept — Project Requirements Document

---

## Objective

Prove that we can render a DST file as a realistic visual preview suitable for customer proof approval. Test multiple rendering approaches to find the right quality/speed tradeoff.

## Why This Is Fourth

Customer approval requires a visual proof. If the preview doesn't look enough like the real stitched product, customers will either reject good designs or approve bad ones. The preview quality directly impacts business workflow.

---

## Global Constraints

| Constraint | Value |
|-----------|-------|
| **Builder** | Brandon + Claude/AI agents |
| **Primary language** | Python 3.10+ (backend/engine) |
| **Frontend** | HTML/CSS/JS (where visualization is needed) |
| **Target machine** | Barudan embroidery machines via BNet software |
| **Thread brand** | Madeira (Classic Rayon 40, Polyneon) |
| **Evaluation priority** | 1. Reliability → 2. Quality → 3. Speed → 4. Flexibility |

---

## What To Build

Multiple rendering implementations that take a DST file (or stitch coordinate data) and produce a visual preview image.

## Test Inputs

- DST files from POC 1 and POC 2 (machine-validated designs)
- At least one commercially-digitized DST file (as a quality benchmark)
- Multiple fabric backgrounds (white piqué, black twill, navy denim)

---

## Bake-Off: Rendering Approaches

| Option | Description | Tech |
|--------|-------------|------|
| **A. pyembroidery PNG** | Use pyembroidery's built-in PNG writer | Python, zero custom code |
| **B. Pillow 2D with shading** | Custom renderer: thick lines + angle-based brightness shading | Python + Pillow |
| **C. Cairo 2D with antialiasing** | Cairo vector renderer with smooth lines and transparency | Python + PyCairo |
| **D. Canvas 2D (browser)** | HTML5 Canvas renderer with rounded line caps and color shading | JS, browser-based |
| **E. WebGL/Three.js 2.5D** | Three.js scene with fabric plane, instanced stitch geometry, Kajiya-Kay shader | JS + Three.js |
| **F. POV-Ray 3D** | Ray-traced 3D thread geometry using the POV-Ray Thread project approach | POV-Ray scripts |

---

## Evaluation Criteria (specific to rendering)

| Criterion | Weight | Description |
|-----------|--------|-------------|
| **Visual fidelity** | 5 | How close does the preview look to the actual stitched product? |
| **Rendering speed** | 4 | Time from DST input to rendered image output |
| **Fabric interaction** | 3 | Can it show the design on different fabric backgrounds? |
| **Interactivity** | 3 | Can the user zoom, pan, rotate the preview? |
| **Implementation effort** | 2 | How much code/setup is needed? |
| **Scalability** | 2 | Does it handle large designs (50k+ stitches) without choking? |

---

## Pass/Fail Criteria

- [ ] At least one approach produces previews that a non-technical person would recognize as "this is what the embroidery will look like"
- [ ] Preview renders in < 10 seconds for a 20k-stitch design
- [ ] Thread colors in the preview visually match the Madeira thread colors
- [ ] Fill stitch direction is visible in the preview (shading changes with angle)
- [ ] Design can be shown on at least 3 different fabric backgrounds

---

## Measurements To Record

- Rendering time per approach per design
- Side-by-side comparison: preview vs. photo of actual stitched output
- User preference ranking (show previews to team members, get reactions)
- Maximum stitch count before performance degrades
- File size of output image/page

---

## Deliverables

1. Implementation of each rendering approach
2. Gallery of rendered previews (all approaches × all test designs × all fabrics)
3. Side-by-side: digital preview vs. photo of stitched product
4. Comparison scorecard
5. **Design recommendation:** Primary renderer for customer proofs + secondary for internal use

---

## Estimated Effort

3-4 sessions with Claude

## Dependencies

- **POC 1 (DST Smoke Test)** must be complete — need valid DST files
- POC 2 helpful but not required (can use any valid DST)

## Risk

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| Preview doesn't match stitched output | **Medium** — customer approval unreliable | Medium | Side-by-side comparison validates preview fidelity |

---

## Reference Documents

- [Embroidery File Generation Deep Research Brief](./Embroidery_File_Generation_Deep_Research.md)
- [POC 1: DST Smoke Test](./POC_1_DST_Smoke_Test.md) — prerequisite
