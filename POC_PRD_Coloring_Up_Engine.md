# Coloring Up Engine: Proof of Concept PRD

## Product Requirements Document — POC Phase

---

## Executive Summary

This document defines a series of **4 proof-of-concept projects** that validate the core technical capabilities needed to build a coloring-up and proof approval system for Straight Down's embroidery operation.

**What this is:** The backend engine and tooling for rendering existing embroidery designs, managing thread colors, building an interactive color-up editor, and running a lightweight order-to-approval workflow.

**What this is NOT:** This does not generate embroidery files. DST files come from Wilcom EmbroideryStudio and/or third-party digitizers. These POCs take those existing DST files as input and build the tooling around them — rendering, coloring, proofing, and approving.

**Why POCs first:** Each POC isolates a specific technical risk and tests competing approaches via scored bake-offs. The winning approaches from each POC become the building blocks for the full application, which will add customer data management, order management, and production tracking in a subsequent phase.

**Broader Vision:** These POCs produce the proven technical components that will power a future end-to-end coloring-up application. That application will manage customers and their logos, track orders with line items, generate trim sheets, handle customer proof approval, and integrate with NetSuite. The full app PRD will be written after these POCs are validated.

---

## Global Constraints

| Constraint | Value |
|-----------|-------|
| **Builder** | Brandon + Claude/AI agents |
| **Primary language** | Python 3.10+ (backend/engine) |
| **Frontend** | HTML/CSS/JS (where visualization is needed) |
| **Target machines** | Barudan embroidery machines via BNet software |
| **Input files** | Existing DST files (Tajima format) from Wilcom or digitizers |
| **Thread brand** | Madeira (Classic Rayon 40, Polyneon) |
| **Existing systems** | NetSuite (future), Microsoft stack (email), Wilcom EmbroideryStudio |
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

## POC 1: DST Renderer Bake-Off

### Objective

Prove that we can take an existing DST file and render it as a realistic visual preview suitable for customer proof approval. Test multiple rendering approaches to find the right quality/speed tradeoff.

### Why This Is First

Everything downstream depends on being able to show what the embroidery looks like. The color-up editor (POC 3) needs a renderer. The proof approval workflow (POC 4) needs a proof image. If we can't render a DST file into something a customer would recognize as "this is what your embroidery will look like," the rest doesn't work.

### What To Build

Multiple rendering implementations that take a DST file and produce a visual preview image. The DST file contains stitch coordinates and color-change commands — the renderer needs to draw the stitches with realistic thread colors on a fabric background.

### Test Inputs

- Commercially-digitized DST files from Wilcom (real production designs currently in use at Straight Down)
- At least 3 different designs: a simple text-only logo, a multi-color logo with fills, and a complex detailed design
- Multiple fabric backgrounds (white piqué, black twill, navy denim)

### Bake-Off: Rendering Approaches

| Option | Description | Tech |
|--------|-------------|------|
| **A. pyembroidery PNG** | Use pyembroidery's built-in PNG writer — baseline zero-effort approach | Python, zero custom code |
| **B. Pillow 2D with shading** | Custom renderer: thick lines with angle-based brightness shading to simulate thread luster | Python + Pillow |
| **C. Cairo 2D with antialiasing** | Cairo vector renderer with smooth antialiased lines and transparency | Python + PyCairo |
| **D. Canvas 2D (browser)** | HTML5 Canvas renderer with rounded line caps and color shading — interactive zoom/pan | JS, browser-based |
| **E. WebGL/Three.js 2.5D** | Three.js scene with fabric plane, instanced stitch geometry, and thread shading | JS + Three.js |

### Evaluation Criteria

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
- File size of output image

### Deliverables

1. Implementation of each rendering approach
2. Gallery of rendered previews (all approaches × all test designs × all fabrics)
3. Side-by-side: digital preview vs. photo of stitched product
4. Comparison scorecard
5. **Design recommendation:** Primary renderer for customer proofs + secondary for internal/interactive use

### Estimated Effort

3-4 sessions with Claude

---

## POC 2: Thread Catalogue & Color Matching

### Objective

Build a Madeira thread color database and prove that automated color matching produces acceptable thread suggestions. This catalogue becomes the backbone of the color-up editor — every thread selection in the system comes from this data.

### Why This Is Second

The color-up editor (POC 3) needs a searchable thread catalogue with accurate color data. Building and validating the catalogue first means POC 3 can focus on the editor UI without worrying about whether the underlying color data is right.

### What To Build

1. **Madeira thread catalogue** — A structured database of Madeira thread colors with catalog numbers, color names, RGB values, color families, and brand/line info (Classic Rayon 40, Polyneon, etc.)
2. **Color matching engine** — Given an arbitrary color (from a logo, a PMS spec, or a customer request), find the closest Madeira thread(s) using perceptually accurate color distance
3. **Simple web UI** — Show a design's colors, the matched threads, and the Delta-E scores so a team member can validate or override the suggestions

### Data Collection Tasks

1. **Parse Madeira RGB data** from Metro chart, EZ Stitch resources, and any available Madeira digital color charts
2. **Parse Isacord RGB PDF** as a cross-reference validation source (best documented thread brand)
3. **Cross-reference** Madeira catalog numbers against at least one other source
4. **Photograph 10 Madeira thread spools** under controlled lighting to validate RGB accuracy against physical spools

### Bake-Off: Color Matching Algorithms

| Option | Description |
|--------|-------------|
| **A. CIEDE2000 in CIELAB** | Industry standard, perceptually uniform, handles hue/chroma/lightness weighting |
| **B. CIE76 (Euclidean in LAB)** | Simpler math, less accurate for saturated colors |
| **C. Euclidean in RGB** | Simplest possible, worst perceptual accuracy (baseline comparison) |
| **D. CMC l:c (textile industry)** | Developed specifically for textile color matching — may be best fit |

### Bake-Off: Palette Optimization

When a design has multiple colors that need thread assignments:

| Option | Description |
|--------|-------------|
| **A. Greedy nearest-match** | Match each design color independently to its closest thread |
| **B. Constrained palette optimization** | Limit to N total threads, optimize overall palette to minimize worst-case Delta-E |
| **C. Perceptual clustering** | Group similar design colors and assign one thread per cluster |

### Pass/Fail Criteria

- [ ] Madeira catalogue contains ≥ 200 threads with validated RGB values
- [ ] Color matching produces Delta-E < 3.5 for 90%+ of common logo colors
- [ ] Matched thread colors are visually acceptable when compared to physical thread spools
- [ ] System correctly handles edge cases: very dark colors, very light colors, neon/fluorescent
- [ ] Web UI displays design colors next to matched thread swatches with Delta-E scores

### Measurements To Record

- Catalogue completeness (% of Madeira Classic Rayon 40 + Polyneon lines covered)
- Delta-E distribution across 50 random test colors
- Delta-E distribution across 10 real Straight Down customer logos
- Time to match a full design palette
- User validation: do team members agree with the auto-selected threads?

### Deliverables

1. `madeira_catalogue.json` — Complete thread database
2. Color matching Python module
3. Web UI for color matching visualization and validation
4. Comparison scorecard for matching algorithms and palette strategies
5. **Design recommendation:** Which matching algorithm + palette strategy for MVP

### Estimated Effort

2-3 sessions with Claude

---

## POC 3: Interactive Color-Up Editor

### Objective

Prove that a web-based editor can load a DST design, display its stitch regions by color, let a team member reassign thread colors from the Madeira catalogue per region, and see the preview update in real time. This is the core tool the embroidery team will use daily.

### Why This Is Third

This is the human-in-the-loop tool — where a team member takes a digitized design and selects the actual thread colors for a specific order/garment. It depends on the renderer (POC 1) to show the design and the thread catalogue (POC 2) to provide the color options. If this editor is too slow, too clunky, or doesn't provide enough control, the whole workflow breaks down.

### What To Build

A web application where:

1. **Load a DST file** — Parse the DST, identify distinct color regions (each color-change command in the DST defines a region/stop)
2. **Render the design** — Display the design using the winning renderer from POC 1
3. **Click to select a color region** — Clicking a stitch region highlights it and opens a color picker panel
4. **Thread color picker** — Search the Madeira catalogue (from POC 2) by name, catalog number, or visual color browsing; see suggested matches based on the current color
5. **Assign thread color** — Select a Madeira thread for the region; the preview re-renders with the new color
6. **Export the color-up** — Save the complete thread sequence (stop #, needle position, Madeira catalog number, thread name) as a reusable color-up record

### Key Design Consideration

A DST file doesn't name its colors — it only has color-change commands between stitch blocks. The "regions" in this editor correspond to those stitch blocks (stops). The editor shows each stop as a selectable region. The team member's job is to assign a specific Madeira thread to each stop.

### Bake-Off: Frontend Rendering & Interaction

| Option | Description |
|--------|-------------|
| **A. SVG + vanilla JS** | Render stitch regions as SVG path groups, click handlers, CSS property panel. Lightweight, no framework. |
| **B. HTML Canvas + React** | Canvas rendering with React state management and UI components. More powerful interaction model. |
| **C. Fabric.js** | Canvas library built specifically for interactive object selection and manipulation. Built-in click-to-select. |
| **D. Three.js + React** | If POC 1 picks the WebGL renderer, extend it with click-to-select regions and a React color picker UI. |

### Pass/Fail Criteria

- [ ] DST file loads and displays all stitch regions with distinct colors
- [ ] User can click any color region and see it highlighted
- [ ] Changing a region's thread color updates the preview within 2 seconds
- [ ] Madeira catalogue search returns results within 500ms
- [ ] Color-up with 4+ color regions can be fully assigned and exported
- [ ] Exported color-up data contains: stop sequence, Madeira catalog numbers, thread names, and color swatches
- [ ] Design with 10+ color stops loads and renders in < 3 seconds

### Measurements To Record

- Time to initial render (DST parse + display)
- Time to re-render after color change
- Maximum stop count before UI becomes sluggish
- Team member feedback on usability (informal user testing with embroidery team)
- Comparison: time to color-up a design in this editor vs. current manual process

### Deliverables

1. Web application (Python backend + JS frontend)
2. Demo with at least 3 real Straight Down DST files
3. Frontend approach comparison scorecard
4. **Design recommendation:** Frontend framework and rendering approach for MVP color-up editor

### Estimated Effort

3-4 sessions with Claude

---

## POC 4: Order-to-Approval Workflow

### Objective

Prove the full order workflow end-to-end: an order comes in with a DST file, a team member creates a color-up using the editor, a proof is generated, the proof is presented for approval on a local approval page, and the order status is tracked through to "approved." All local — no email integration yet.

### Why This Is Last

This POC ties everything together. It's the lowest technical risk (standard web app development) but validates that the tools from POCs 1-3 can be assembled into a real production workflow. It also establishes the data model and state machine that the full application will build on.

### What To Build

A lightweight web application with these pages:

1. **Order Entry** — Create an order: enter customer name, order/PO number, garment type, quantity, placement instructions, and upload a DST file
2. **Color-Up** — Open the interactive color-up editor (POC 3) for the order's DST file. Assign thread colors. Save the color-up.
3. **Proof Preview** — Render the design with the assigned colors (POC 1 renderer) and generate a proof image. Display it for internal review.
4. **Approval Page** — A local web page (simulating what a customer would see) showing the proof with "Approve" and "Reject" buttons. Rejections capture feedback text.
5. **Order Dashboard** — A simple list of all orders with their current status: New → Color-Up In Progress → Proof Ready → Sent for Approval → Approved / Rejected

### Workflow States

```
New → Color-Up In Progress → Proof Ready → Sent for Approval → Approved
                                                              → Rejected → Color-Up In Progress (revision)
```

### Bake-Off: Data Storage

| Option | Description |
|--------|-------------|
| **A. SQLite** | File-based, zero setup, good for POC, easy to inspect |
| **B. PostgreSQL** | Production-grade from the start, no migration needed later |
| **C. JSON flat files** | Absolute simplest for POC. Not scalable but fastest to build. |

### Bake-Off: Web Framework

| Option | Description |
|--------|-------------|
| **A. FastAPI + HTMX** | Python backend, server-rendered HTML with HTMX for interactivity. Minimal JS. |
| **B. FastAPI + React** | Python API backend, React SPA frontend. More complex but richer UI. |
| **C. Flask + Jinja** | Classic Python web app. Simple, well-documented, lots of examples. |

### What's NOT in This POC (Saved for Full App)

- Customer management (customers with approvers, logos, reusable color-ups)
- NetSuite integration
- Email delivery of proofs
- Trim sheet generation
- Line items with size grids
- Production tracking and completion
- Multi-user auth

These are all documented in the [Coloring Up Order Management PRD](./PRD_Coloring_Up_Order_Management.md) and will be built after the POCs prove out the core tools.

### Pass/Fail Criteria

- [ ] Team member can create an order and upload a DST file
- [ ] Color-up editor loads the DST and allows thread color assignment for all regions
- [ ] Proof image is generated with the assigned colors and looks professional
- [ ] Approval page correctly displays the proof with approve/reject functionality
- [ ] Rejecting an order captures feedback and resets status to allow revision
- [ ] Dashboard shows all orders with correct statuses
- [ ] At least 5 test orders can be processed through the full workflow without data loss

### Measurements To Record

- Time from order entry to proof ready (color-up + rendering)
- Number of clicks/steps to complete the full workflow
- Data integrity: do all 5 test orders maintain correct state?
- Team member feedback on the overall workflow
- Bottleneck identification: which step is slowest or most awkward?

### Deliverables

1. Web application (Python backend + frontend)
2. Demo with 5 test orders through the complete workflow
3. Framework and storage comparison scorecard
4. **Design recommendation:** Tech stack and architecture for the full application build

### Estimated Effort

2-3 sessions with Claude

---

## POC Dependency Graph

```
POC 1: DST Renderer ─────────┐
                              │
POC 2: Thread Catalogue ──────┤
       (can run parallel      │
        with POC 1)           │
                              ▼
                    POC 3: Color-Up Editor
                              │
                              ▼
                    POC 4: Order Workflow
```

**Parallelization:** POC 1 (Renderer) and POC 2 (Thread Catalogue) have no dependencies on each other and can be built in parallel. POC 3 needs both. POC 4 needs POC 3.

---

## Timeline Estimate

| POC | Sessions | Depends On | Can Parallel With |
|-----|----------|-----------|-------------------|
| **1. DST Renderer** | 3-4 | None | POC 2 |
| **2. Thread Catalogue** | 2-3 | None | POC 1 |
| **3. Color-Up Editor** | 3-4 | POCs 1 & 2 | — |
| **4. Order Workflow** | 2-3 | POC 3 | — |
| **Total** | **10-14 sessions** | | |

**Critical path:** POC 1 → POC 3 → POC 4 (8-11 sessions)

**Fastest completion:** Run POC 2 in parallel with POC 1. As soon as both are done, start POC 3.

---

## Risk Register

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| DST renderer quality too low for customer proofs | **High** — proofs become unreliable | Medium | Bake-off tests 5 approaches; at least one should be sufficient |
| Madeira RGB data inaccurate | **Medium** — color matching unreliable | Low-Medium | Validate against physical thread spools; allow manual correction |
| DST color-change parsing unreliable | **Medium** — editor can't identify regions | Low | DST format is well-specified; pyembroidery handles parsing |
| Color-up editor too slow for real-time preview | **Medium** — workflow becomes clunky | Medium | Bake-off tests 4 rendering approaches; can fall back to deferred rendering |
| Team doesn't find editor intuitive | **High** — adoption fails | Medium | Build with team feedback; keep it simpler than Wilcom, not more complex |

---

## Success Criteria for POC Phase

The POC phase is successful if:

1. **Rendering works** — At least one renderer produces previews that team members rate as "acceptable for customer proofs" for ≥ 80% of test designs
2. **Thread data is solid** — Madeira catalogue has ≥ 200 threads with validated RGB values and auto-matching produces acceptable results for ≥ 90% of common logo colors
3. **Color-up editor is usable** — A team member can color-up a 4-stop design in under 5 minutes using the editor (faster than the current process)
4. **Workflow holds together** — 5 test orders can go from entry to approval without data loss or broken state transitions
5. **Design documents produced** — Each POC outputs a clear recommendation with evidence for what to use in the full app build

---

## What Comes After the POCs

Once these POCs validate the core tools, the next step is building the full **Coloring Up Application**. That PRD will cover:

- **Customer management** — Customers with approvers, logos, and reusable approved color-ups per product
- **Order management** — Orders with line items, garment styles, size grids, logo/color-up assignments
- **Trim sheet generation** — Consolidated production document merging Wilcom data + order data + color-up data
- **Proof email delivery** — Microsoft Graph API integration for sending proofs to customer approvers
- **Customer approval portal** — Web-based approve/reject with feedback capture
- **Production handoff** — Production queue, completion tracking, basic reporting
- **NetSuite integration** — Pull order data, push approval status

The preliminary thinking for this application is documented in [PRD_Coloring_Up_Order_Management.md](./PRD_Coloring_Up_Order_Management.md).

---

## Appendix: Reference Documents

- [Coloring Up Order Management PRD](./PRD_Coloring_Up_Order_Management.md) — Full application PRD (to be refined after POCs)
- [Blue Sky Archive/](./Blue Sky Archive/) — Original embroidery file generation POC plans
- [Trim Sheet Examples/](./Trim Sheet Examples/) — Example Wilcom Production Worksheet and Compact Trim Sheet PDFs
