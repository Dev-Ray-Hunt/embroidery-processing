# POC 3: Interactive Color-Up Editor

## Proof of Concept — Project Document

---

## Objective

Prove that a web-based editor can load a DST design, display its stitch regions by color stop, let a team member reassign Madeira thread colors to each region, and see the preview update in real time. This is the core tool the embroidery team will use daily — it must be fast, intuitive, and produce a complete color-up record.

## Why This Is Third

This is the human-in-the-loop tool where the real work happens. A team member takes a digitized design and makes the creative/technical decisions about which thread colors to use for each stitch region on a specific garment. The renderer (POC 1) provides the visual feedback. The thread catalogue (POC 2) provides the color options. This editor brings them together into a usable tool.

If the editor is slow, confusing, or doesn't give enough control, the team will abandon it and go back to the manual process. Usability is the critical success factor here — not just "does it work" but "is it faster and better than what we do today."

---

## Background

### How Coloring Up Works Today

When a new embroidery order comes in, a team member:
1. Looks at the customer's logo/design
2. Refers to the DST file (which has color-change commands defining stitch regions)
3. Decides which Madeira thread to use for each color region based on the customer's brand colors, the garment color, and experience
4. Records the thread selections (catalog numbers) — currently tracked in the VRLink system or on paper
5. This information goes on the trim sheet for the machine operator

This process happens for every new logo/garment color combination. Repeat orders reuse the previous color-up.

### How a DST File Defines Color Regions

A DST file doesn't store color names or RGB values — it only contains stitch coordinates and **color-change commands** (also called "stops"). Each color-change tells the machine to pause so the operator can switch to the next thread. The sequence of stops defines the color regions:

```
Stop 1: Stitches 1-776      → Needle 4 (first thread color)
Stop 2: Stitches 777-1976   → Needle 5 (second thread color)
Stop 3: Stitches 1977-2075  → Needle 4 (back to first color)
Stop 4: Stitches 2076-3386  → Needle 5 (back to second color)
```

The editor's job is to render each stop as a visually distinct, selectable region and let the user assign a specific Madeira thread to each one.

---

## Global Constraints

| Constraint | Value |
|-----------|-------|
| **Builder** | Brandon + Claude/AI agents |
| **Backend** | Python 3.10+ (FastAPI) |
| **Frontend** | HTML/CSS/JS |
| **Input** | DST files (parsed by pyembroidery) |
| **Thread data** | Madeira catalogue from POC 2 |
| **Rendering** | Winning approach from POC 1 |
| **Evaluation priority** | 1. Usability → 2. Speed → 3. Reliability → 4. Flexibility |

Note: Evaluation priority shifts for this POC — **usability** is the top concern since this is an interactive team tool.

---

## What To Build

### Core Editor Features

**1. DST Loader**
- Upload or select a DST file
- Parse using pyembroidery to extract stitch coordinates and color-change commands
- Identify each color stop as a distinct "region"
- Display a summary: design name, total stitches, number of stops/regions, dimensions

**2. Design Renderer**
- Display the full design using the winning renderer from POC 1
- Each color region rendered in a distinct default color (so regions are visually distinguishable before thread assignment)
- Support zoom and pan for detailed inspection

**3. Region Selection**
- Click on any stitch region in the design to select it
- Selected region highlights (brighter, outlined, or pulsing)
- Region info panel shows: stop number, stitch count, current assigned thread (if any)
- Option to cycle through regions with next/previous buttons (for keyboard-driven workflow)

**4. Thread Color Picker**
- Opens when a region is selected
- **Search:** Type to search by Madeira catalog number or color name
- **Browse:** Grid of color swatches organized by color family (Reds, Blues, Greens, etc.)
- **Suggested matches:** If the DST has embedded color hints or the region has a previously used color, show the closest Madeira matches (using POC 2's matching engine)
- **Recently used:** Show threads used elsewhere in this design and recently used threads across designs
- Each thread option shows: color swatch, catalog number, color name, brand/line

**5. Real-Time Preview Update**
- When a thread is selected for a region, the design preview re-renders with the new color
- Re-render should complete in < 2 seconds
- All other regions maintain their assigned (or default) colors

**6. Color-Up Summary Panel**
- Side panel showing the complete color-up:
  - Each stop number with its assigned thread (swatch + catalog number + name)
  - Unassigned regions highlighted as needing attention
  - Total thread count (number of unique threads)
- This panel is essentially a live preview of what will go on the trim sheet

**7. Export / Save**
- Save the color-up as a JSON record:
  ```json
  {
    "design_number": "000001767-091",
    "stops": [
      {"stop": 1, "needle": 4, "stitch_count": 776, "thread_code": "1000", "thread_name": "Emerald Black", "brand": "Madeira Classic 40"},
      {"stop": 2, "needle": 5, "stitch_count": 1200, "thread_code": "2332", "thread_name": "Penny", "brand": "R-A SSR 6"}
    ],
    "total_stitches": 3386,
    "created_by": "brandon",
    "created_at": "2026-04-24T10:00:00"
  }
  ```
- Export a printable color-up sheet (summary with swatches — simple HTML or PDF)

---

## Bake-Off: Frontend Rendering & Interaction

### Option A: SVG + Vanilla JS

**Description:** Render each stitch region as a group of SVG path elements. Click handlers on SVG groups for region selection. Property panel built with plain HTML/CSS.

**Pros:** Lightweight, no framework dependency, SVG is resolution-independent, native click detection on shapes.
**Cons:** SVG performance degrades with thousands of path elements; may struggle with 20k+ stitch designs.

**Best for:** Smaller designs, simpler interaction needs.

---

### Option B: HTML Canvas + React

**Description:** Render the design on an HTML5 Canvas element. React manages the UI state (selected region, thread assignments, catalogue search). Hit-testing for click-to-select is done by rendering a hidden "ID map" canvas where each region is a unique color.

**Pros:** Canvas handles large stitch counts well, React provides clean state management, ID-map hit testing is efficient.
**Cons:** More code (React build step), Canvas hit-testing requires the ID-map pattern, more complex architecture.

**Best for:** Larger designs, complex UI state.

---

### Option C: Fabric.js

**Description:** Fabric.js is a Canvas library specifically designed for interactive object selection and manipulation. Each stitch region becomes a Fabric.js object with built-in click-to-select, highlighting, and grouping.

**Pros:** Built-in selection, highlighting, grouping, zoom/pan. Purpose-built for this kind of interactive canvas application.
**Cons:** Another library dependency, may have performance overhead for very large stitch counts, learning curve for Fabric.js API.

**Best for:** Getting interactive selection working quickly without building it from scratch.

---

### Option D: Extend POC 1 Winner

**Description:** If POC 1 selects a browser-based renderer (Canvas or Three.js), extend it directly with click-to-select regions and a thread picker UI. Avoids rebuilding the renderer.

**Pros:** Reuses proven rendering code, consistent visual quality, no rendering duplication.
**Cons:** Depends entirely on POC 1 outcome, may require architectural changes to the renderer.

**Best for:** If the POC 1 winner is already browser-based and well-structured.

---

## Evaluation Criteria

| Criterion | Weight | What 5 Looks Like | What 1 Looks Like |
|-----------|--------|-------------------|-------------------|
| **Usability** | 5 | Team member can color-up a design without instructions | Confusing, team needs training for basic tasks |
| **Render speed** | 4 | Re-render after color change < 500ms | > 5 seconds, feels broken |
| **Selection accuracy** | 4 | Clicking a region always selects the right one | Misclicks, wrong region selected often |
| **Search speed** | 3 | Thread catalogue search results appear as you type | Noticeable delay, > 1 second lag |
| **Implementation effort** | 2 | Clean architecture, easy to extend for full app | Tangled code, hard to maintain |

---

## Pass/Fail Criteria

- [ ] DST file loads and displays all stitch regions with distinct default colors
- [ ] User can click any color region and see it highlighted
- [ ] Changing a region's thread color updates the preview within 2 seconds
- [ ] Madeira catalogue search returns results within 500ms as user types
- [ ] A 4-stop design can be fully colored up and exported in under 5 minutes
- [ ] Exported color-up JSON contains all required fields (stop, thread code, name, brand)
- [ ] Design with 10+ color stops loads and renders in < 3 seconds
- [ ] Color-up summary panel correctly reflects all assignments and flags unassigned regions

---

## Measurements To Record

| Measurement | How |
|-------------|-----|
| Time to initial render | From DST upload to design displayed |
| Time to re-render after color change | From thread selection click to preview updated |
| Region selection accuracy | % of clicks that select the intended region (test with 20 clicks) |
| Catalogue search latency | Time from keystroke to results displayed |
| Full color-up time | Time for a team member to fully color-up a 4-stop design |
| Comparison to current process | How long does the same color-up take with the current manual process? |
| Max stops before UI degrades | Test with designs of increasing stop counts |
| Team usability feedback | Informal user testing — can the team use it without help? |

---

## Implementation Plan

### Step 1: Backend API
- FastAPI endpoint: `POST /api/parse-dst` — accepts DST file upload, returns parsed stitch data as JSON (coordinates, color changes, stop boundaries, metadata)
- FastAPI endpoint: `GET /api/threads` — returns the Madeira catalogue (from POC 2)
- FastAPI endpoint: `GET /api/threads/search?q=` — search threads by name or catalog number
- FastAPI endpoint: `GET /api/threads/match?rgb=` — find closest threads to a color (from POC 2 matching engine)
- FastAPI endpoint: `POST /api/colorup/save` — save a color-up record

### Step 2: Build Each Frontend Option
- Implement at least options A, B, and C (or B, C, and D depending on POC 1 outcome)
- Each option must support: render, click-to-select, highlight, color picker, re-render
- Share the same backend API

### Step 3: Thread Picker UI
- Search input with autocomplete
- Color family grid browser
- Recently used section
- Suggested matches section (using POC 2 matching)
- Each option shows swatch + catalog number + name

### Step 4: Color-Up Summary & Export
- Live summary panel showing all stops and their assignments
- Unassigned indicator
- Export button → JSON save
- Export button → printable color-up sheet

### Step 5: Evaluation
- Test all frontend options with the same 3 DST files
- Get team members to try coloring up a design with each option
- Record measurements
- Fill out scorecard

---

## Test Scenarios

1. **Simple 2-color design** (e.g., Alpha Omega logo — 4 stops, 2 unique threads) — Basic workflow validation
2. **Multi-color logo** (6+ stops, 4+ unique threads) — Tests region selection with many stops, thread picker usage
3. **Complex design** (10+ stops) — Stress test for rendering and selection performance
4. **Re-color scenario** — Load a design, assign colors, then change one region's color — verify re-render and summary update
5. **Export and reload** — Save a color-up, verify the JSON is complete and correctly structured

---

## Deliverables

1. Web application (FastAPI backend + JS frontend)
2. Implementation of each frontend rendering approach
3. Demo with at least 3 real Straight Down DST files
4. Exported color-up JSON examples
5. Printable color-up sheet example
6. Frontend approach comparison scorecard
7. Team usability feedback notes
8. **Design recommendation:** Frontend framework and rendering approach for MVP color-up editor

---

## Estimated Effort

3-4 sessions with Claude

## Dependencies

- **POC 1 (DST Renderer)** — Need the winning rendering approach (or at minimum, the DST parsing utility)
- **POC 2 (Thread Catalogue)** — Need the Madeira catalogue JSON and matching engine

## Risk

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| Editor too slow for real-time preview | **High** — workflow becomes clunky, team won't use it | Medium | Bake-off tests multiple approaches; can fall back to "click apply to re-render" instead of instant |
| Click-to-select regions is unreliable | **Medium** — frustrating UX | Medium | ID-map hit-testing is proven; SVG has native hit detection |
| Team finds it harder than current process | **High** — adoption fails | Medium | Keep it simple; test with team early; iterate on feedback before finalizing |
| DST stop boundaries don't map cleanly to visual regions | **Medium** — confusing display | Low | DST stops are well-defined; pyembroidery parses them reliably |

---

## Reference Documents

- [POC PRD: Coloring Up Engine](./POC_PRD_Coloring_Up_Engine.md) — Parent PRD
- [POC 1: DST Renderer](./POC_1_DST_Renderer.md) — Prerequisite (rendering approach)
- [POC 2: Thread Catalogue](./POC_2_Thread_Catalogue.md) — Prerequisite (thread data and matching)
- [Trim Sheet Examples/](./Trim Sheet Examples/) — Example of the current trim sheet showing stop sequences
