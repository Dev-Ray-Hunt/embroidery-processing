# POC 2: Thread Catalogue & Color Matching

## Proof of Concept — Project Document

---

## Objective

Build a Madeira thread color database and prove that automated color matching produces acceptable thread suggestions from arbitrary input colors. This catalogue becomes the backbone of the color-up editor — every thread selection in the system pulls from this data.

## Why This Is Second

The color-up editor (POC 3) needs a searchable thread catalogue with accurate color data. If the catalogue colors don't match reality, every color-up will be wrong and team members will lose trust in the tool. Building and validating this data first means POC 3 can focus on the editor experience without worrying about whether the underlying color data is accurate.

This POC can run **in parallel with POC 1** (DST Renderer) since they have no dependencies on each other.

---

## Background

Straight Down uses **Madeira** embroidery threads, primarily:

- **Classic Rayon 40** — The main line, viscose rayon, high sheen, ~400+ colors
- **Polyneon** — Polyester, more durable, slightly less sheen, ~400+ colors

Thread colors are identified by **catalog numbers** (e.g., 1000 = Emerald Black, 2332 = Penny). When coloring up a design, the team needs to select specific Madeira catalog numbers for each stitch region. Today this is done from physical thread charts and memory.

The color matching engine serves two purposes:
1. **Suggestion** — Given a color from a logo or PMS spec, suggest the closest Madeira thread(s)
2. **Validation** — Show the Delta-E (perceptual color distance) so the team can judge if a match is "close enough" or needs manual selection

---

## Global Constraints

| Constraint | Value |
|-----------|-------|
| **Builder** | Brandon + Claude/AI agents |
| **Primary language** | Python 3.10+ |
| **Thread brands** | Madeira Classic Rayon 40 (primary), Madeira Polyneon (secondary) |
| **Color science** | CIELAB color space, Delta-E distance metrics |
| **Evaluation priority** | 1. Reliability → 2. Quality → 3. Speed → 4. Flexibility |

---

## What To Build

### Part 1: Thread Catalogue Database

A structured JSON database of Madeira thread colors.

**Required fields per thread:**

| Field | Type | Example | Notes |
|-------|------|---------|-------|
| `catalog_number` | String | "1000" | Madeira catalog number |
| `color_name` | String | "Emerald Black" | Madeira's official color name |
| `brand` | String | "Madeira Classic 40" | Thread line/brand |
| `rgb` | [R, G, B] | [20, 20, 20] | RGB values (0-255) |
| `lab` | [L, a, b] | [7.7, 0.0, 0.0] | CIELAB values (derived from RGB via D65 illuminant) |
| `color_family` | String | "Black" | Grouping for browsing (Red, Blue, Green, Black, White, Gold, etc.) |
| `hex` | String | "#141414" | Hex color code for web display |
| `weight` | String | "40" | Thread weight |
| `fiber` | String | "Rayon" or "Polyester" | Fiber type |

**Optional/future fields:**

| Field | Type | Notes |
|-------|------|-------|
| `pms_match` | String | Closest Pantone PMS number (if known) |
| `in_stock` | Boolean | Whether this color is currently in the thread inventory |
| `on_machine` | Integer | Which machine needle position this is loaded in (if any) |
| `usage_frequency` | Integer | How often this color is used (for "favorites" sorting) |

### Part 2: Color Matching Engine

A Python module that takes an input color (RGB, hex, or PMS) and returns the top-N closest Madeira threads ranked by perceptual distance.

**API:**
```python
# Find closest threads to an arbitrary color
matches = find_closest_threads(rgb=(186, 155, 80), top_n=5)
# Returns: [(catalog_number, color_name, delta_e, rgb), ...]

# Find closest thread to a PMS color
matches = find_closest_to_pms("PMS 465 C", top_n=5)

# Match all colors in a design palette
palette_matches = match_palette(
    design_colors=[(186, 155, 80), (20, 20, 20), (255, 255, 255)],
    max_threads=None  # or limit to N total threads
)
```

### Part 3: Web UI for Validation

A simple web page where the team can:

1. Enter or pick a color (hex input, color picker, or PMS number)
2. See the top-5 closest Madeira threads with color swatches and Delta-E scores
3. Browse the full catalogue by color family
4. Search by catalog number or color name
5. Side-by-side compare: input color swatch vs. matched thread swatch

---

## Data Collection Tasks

### Task 1: Gather Madeira RGB Data

**Primary sources:**
- Metro thread chart digital data (if available in parseable format)
- EZ Stitch thread database (online resource with Madeira RGB values)
- Madeira's official digital color card (if available)
- Wilcom EmbroideryStudio's built-in thread database (may have Madeira data)

**What to do:**
1. Search for and download any available digital Madeira color data
2. Parse into a consistent JSON format
3. Cross-reference at least two sources — if RGB values disagree significantly, flag for manual validation

### Task 2: Isacord Cross-Reference

Isacord (by AMANN) has the best-documented public RGB data of any thread brand. While Straight Down uses Madeira, Isacord data serves as a useful validation reference:

1. Parse Isacord's RGB color chart PDF
2. For threads where Isacord publishes a "Madeira equivalent" catalog number, compare RGB values
3. Flag any Madeira colors where our data disagrees with the cross-reference

### Task 3: Physical Thread Spool Validation

1. Select 10 representative Madeira thread spools from Straight Down's inventory (spanning light, dark, saturated, neutral colors)
2. Photograph each under controlled, consistent lighting (daylight-balanced, white background)
3. Extract the average RGB from the thread area of each photo
4. Compare to the catalogue's RGB values — Delta-E should be < 5 for a "valid" match
5. If any are way off, update the catalogue entry

### Task 4: Build the Catalogue

1. Merge data from all sources
2. Convert all RGB values to CIELAB (using D65 illuminant, sRGB color space)
3. Assign color families based on hue/saturation clustering or manual grouping
4. Generate hex values from RGB
5. Export as `madeira_catalogue.json`

**Target:** ≥ 200 threads in Classic Rayon 40 + Polyneon lines with validated RGB values.

---

## Bake-Off: Color Matching Algorithms

### Option A: CIEDE2000 in CIELAB

**Description:** The current industry standard for perceptual color difference. Accounts for non-uniformity in human color perception across different hue, chroma, and lightness regions. Most complex math, best perceptual accuracy.

**Implementation:** Use the `colormath` Python library or `colour-science` library, both of which implement CIEDE2000.

**What to test:** Compute Delta-E (CIEDE2000) between input color and every thread in the catalogue, return sorted.

---

### Option B: CIE76 (Euclidean in CIELAB)

**Description:** Simple Euclidean distance in CIELAB space. The original Delta-E formula. Much simpler math than CIEDE2000 but less accurate for saturated colors and colors in the blue region.

**Implementation:** `sqrt((L1-L2)² + (a1-a2)² + (b1-b2)²)` — trivial to implement from scratch.

**What to test:** Same as Option A but using CIE76 distance. Compare rankings to CIEDE2000 to see where they diverge.

---

### Option C: Euclidean in RGB

**Description:** Simple Euclidean distance in RGB space. The baseline comparison — fast and simple but perceptually inaccurate (RGB is not perceptually uniform).

**Implementation:** `sqrt((R1-R2)² + (G1-G2)² + (B1-B2)²)` — trivial.

**What to test:** Same ranking exercise. This should perform worst but establishes the floor.

---

### Option D: CMC l:c (Textile Industry Standard)

**Description:** Developed by the Colour Measurement Committee of the Society of Dyers and Colourists specifically for textile color matching. Uses a lightness-to-chroma ratio parameter that can be tuned for textile applications (typically l:c = 2:1 for "acceptability" matching).

**Implementation:** Available in `colormath` library. Slightly more complex than CIE76, less complex than CIEDE2000.

**What to test:** Same ranking exercise. This is specifically designed for textiles — it may outperform CIEDE2000 for our use case even though CIEDE2000 is the newer general-purpose standard.

---

## Bake-Off: Palette Optimization

When a design has multiple colors that need thread assignments, there are different strategies:

### Option A: Greedy Nearest-Match

Match each design color independently to its closest thread. Simple, fast, but may result in using many threads when some design colors are similar enough to share one thread.

### Option B: Constrained Palette Optimization

Limit the total number of threads to N (e.g., "this design should use no more than 6 threads"). Optimize the overall palette to minimize the worst-case Delta-E across all colors. Useful for reducing thread changes and simplifying machine setup.

### Option C: Perceptual Clustering

Group design colors that are perceptually similar (Delta-E < threshold) and assign one thread per cluster. A middle ground — reduces thread count without a hard limit.

---

## Pass/Fail Criteria

- [ ] Madeira catalogue contains ≥ 200 threads with validated RGB values
- [ ] Catalogue covers both Classic Rayon 40 and Polyneon lines
- [ ] Color matching produces Delta-E < 3.5 for 90%+ of common logo colors (test against 50 random colors)
- [ ] Matched thread colors are visually acceptable when compared to physical thread spools (validate 10 spools)
- [ ] System correctly handles edge cases: very dark colors (near-black), very light colors (near-white), neon/fluorescent, metallics
- [ ] Web UI displays input color next to matched thread swatches with Delta-E scores
- [ ] Catalogue search by name and catalog number returns results in < 200ms
- [ ] All four matching algorithms produce results and can be compared side-by-side

---

## Measurements To Record

| Measurement | How |
|-------------|-----|
| Catalogue completeness | Count of threads per line / total available in that line |
| RGB accuracy | Delta-E between catalogue values and photographed physical spools (10 spools) |
| Matching accuracy (per algorithm) | Delta-E distribution across 50 random test colors |
| Real-world accuracy | Delta-E distribution across colors from 10 real Straight Down customer logos |
| Matching speed | Time to match one color against full catalogue |
| Palette matching speed | Time to match a 4-color and 8-color palette |
| Algorithm agreement | How often do all 4 algorithms pick the same top-1 thread? |
| Team validation | Show top-3 matches for 20 colors to team members — what % do they agree with? |

---

## Implementation Plan

### Step 1: Data Collection & Catalogue Build
- Research and download Madeira thread color data from available sources
- Parse, clean, and merge into a consistent JSON format
- Convert RGB → CIELAB for every entry
- Assign color families
- Export `madeira_catalogue.json`

### Step 2: Color Matching Engine
- Implement all four matching algorithms
- Write `find_closest_threads()` function that accepts any algorithm
- Write `match_palette()` function with all three palette strategies
- Unit tests with known color pairs to verify Delta-E calculations

### Step 3: Web UI
- Simple FastAPI backend serving the catalogue and matching endpoint
- HTML/JS frontend with:
  - Color input (hex, RGB sliders, browser color picker)
  - Results display with swatches and Delta-E
  - Catalogue browser by color family
  - Search by name/number
  - Algorithm toggle (show results from different algorithms side-by-side)

### Step 4: Validation
- Photograph 10 physical thread spools
- Compare photographed RGB to catalogue RGB
- Run the 50-color and 10-logo test suites
- Get team feedback on matching quality
- Fill out comparison scorecard

### Step 5: Design Recommendation
- Select the matching algorithm for the MVP
- Select the palette strategy for the MVP
- Document any catalogue entries that need manual correction
- Note any gaps in the catalogue that need to be filled

---

## Deliverables

1. `madeira_catalogue.json` — Complete thread database (≥ 200 threads)
2. Color matching Python module with all four algorithms
3. Palette matching module with all three strategies
4. Web UI for color matching, catalogue browsing, and validation
5. Physical spool validation photos and comparison data
6. Evaluation scorecard for matching algorithms and palette strategies
7. **Design recommendation document:** Which algorithm, which palette strategy, and known catalogue issues to address

---

## Estimated Effort

2-3 sessions with Claude

## Dependencies

None — independent of POC 1. Can run in parallel.

## Risk

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| Madeira RGB data not available digitally | **High** — must build catalogue manually | Medium | Multiple sources exist (EZ Stitch, Metro, Wilcom); worst case, photograph and color-pick from physical chart |
| RGB data inaccurate for many colors | **Medium** — team won't trust suggestions | Medium | Physical spool validation catches worst offenders; allow manual correction in the catalogue |
| No algorithm works well for metallic/fluorescent threads | **Low** — edge case, manual selection is fine | High | Document limitation; metallic/fluorescent threads are special-use and team knows them by number anyway |

---

## Reference Documents

- [POC PRD: Coloring Up Engine](./POC_PRD_Coloring_Up_Engine.md) — Parent PRD
- [Blue Sky Archive/Embroidery_File_Generation_Deep_Research.md](./Blue Sky Archive/Embroidery_File_Generation_Deep_Research.md) — Thread catalogue data source research
