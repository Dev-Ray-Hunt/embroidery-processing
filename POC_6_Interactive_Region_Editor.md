# POC 6: Interactive Region Editor

## Proof of Concept — Project Requirements Document

---

## Objective

Prove that a web-based editor can let a team member click on design regions, modify their stitch properties (type, color, angle, density), and see the preview update.

## Why This Is Sixth

This is the human-in-the-loop step in the production workflow. The auto-generated design gets refined by a team member before going to the customer. If this editor is too slow, too clunky, or doesn't provide enough control, the whole workflow breaks down.

---

## Global Constraints

| Constraint | Value |
|-----------|-------|
| **Builder** | Brandon + Claude/AI agents |
| **Primary language** | Python 3.10+ (backend/engine) |
| **Frontend** | HTML/CSS/JS (where visualization is needed) |
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

A web application with:

- Canvas/SVG rendering of design regions
- Click-to-select regions
- Property panel per region (stitch type, thread color from Madeira palette, fill angle, density)
- Real-time preview re-render when properties change
- Export modified design data

---

## Bake-Off: Frontend Rendering

| Option | Description |
|--------|-------------|
| **A. SVG + vanilla JS** | Regions as SVG paths, click handlers, CSS property panel |
| **B. HTML Canvas + React** | Canvas rendering with React state management |
| **C. Three.js + React** | 3D-capable renderer with React UI |
| **D. Fabric.js** | Canvas library built for interactive object manipulation |

---

## Pass/Fail Criteria

- [ ] User can click any region and see it highlighted
- [ ] Changing stitch type updates the preview within 2 seconds
- [ ] Changing thread color shows the new color immediately
- [ ] Changing fill angle visually changes the stitch direction in preview
- [ ] Design with 10+ regions loads and renders in < 3 seconds
- [ ] Modified design can be exported as updated stitch data

---

## Measurements To Record

- Time to initial render
- Time to re-render after property change
- Maximum region count before UI becomes sluggish
- Team member feedback on usability (informal user testing)

---

## Deliverables

1. Web application (Python backend + JS frontend)
2. Demo with at least 3 test designs
3. Frontend approach comparison scorecard
4. **Design recommendation:** Frontend framework and rendering approach for MVP editor

---

## Estimated Effort

3-4 sessions with Claude

## Dependencies

- **POC 2 (Stitch Generation)** — stitch generation algorithms
- **POC 3 (Image-to-Regions)** — region extraction pipeline
- **POC 4 (Preview Renderer)** — renderer for preview
- **POC 5 (Thread Catalogue)** — thread catalogue for color picker

## Risk

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| Editor too slow for real-time preview | **Medium** — workflow becomes clunky | Medium | Bake-off tests 4 rendering approaches; can fall back to deferred rendering |

---

## Reference Documents

- [Embroidery File Generation Deep Research Brief](./Embroidery_File_Generation_Deep_Research.md)
- [POC 2: Stitch Generation](./POC_2_Stitch_Generation.md) — prerequisite
- [POC 3: Image-to-Regions](./POC_3_Image_to_Regions.md) — prerequisite
- [POC 4: Stitch Preview Renderer](./POC_4_Stitch_Preview_Renderer.md) — prerequisite
- [POC 5: Thread Catalogue](./POC_5_Thread_Catalogue.md) — prerequisite
