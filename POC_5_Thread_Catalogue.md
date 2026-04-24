# POC 5: Thread Catalogue + Color Matching

## Proof of Concept — Project Requirements Document

---

## Objective

Build a Madeira thread color database and prove that automated color matching (Delta-E in CIELAB) produces acceptable thread selections from arbitrary design colors.

## Why This Is Fifth

Color management underpins the entire system. If the auto-selected thread colors don't match customer expectations, every proof will need manual color correction.

---

## Global Constraints

| Constraint | Value |
|-----------|-------|
| **Builder** | Brandon + Claude/AI agents |
| **Primary language** | Python 3.10+ (backend/engine) |
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

1. A JSON-based Madeira thread catalogue with RGB values, catalog numbers, color names, and optical properties
2. A color matching engine using CIEDE2000 Delta-E in CIELAB space
3. A simple web UI showing the design colors, matched threads, and Delta-E scores

## Data Collection Tasks

1. **Parse Isacord RGB PDF** (as validation reference — best documented brand)
2. **Parse Madeira RGB data** from Metro chart and EZ Stitch resources
3. **Cross-reference** Madeira catalog numbers against at least one other source for validation
4. **Photograph 10 Madeira thread spools** under controlled lighting for RGB validation

---

## Bake-Off: Color Matching Algorithms

| Option | Description |
|--------|-------------|
| **A. CIEDE2000 in CIELAB** | Industry standard, perceptually uniform, handles hue/chroma/lightness |
| **B. CIE76 (simple Euclidean in LAB)** | Simpler math, less accurate for saturated colors |
| **C. Euclidean in RGB** | Simplest, worst perceptual accuracy (baseline comparison) |
| **D. CMC l:c (textile industry)** | Developed specifically for textile color matching |

## Bake-Off: Palette Optimization

| Option | Description |
|--------|-------------|
| **A. Greedy nearest-match** | Match each design color independently to closest thread |
| **B. Constrained palette optimization** | Limit to N threads total, optimize overall palette to minimize worst-case Delta-E |
| **C. Perceptual clustering** | Group similar design colors and assign one thread per cluster |

---

## Pass/Fail Criteria

- [ ] Madeira catalogue contains ≥ 200 threads with validated RGB values
- [ ] Color matching produces Delta-E < 3.5 for 90%+ of common logo colors
- [ ] Matched thread colors are visually acceptable when compared to physical thread spools
- [ ] System correctly handles edge cases: very dark colors, very light colors, neon/fluorescent
- [ ] Web UI displays design colors next to matched thread swatches

---

## Measurements To Record

- Catalogue completeness (% of Madeira Classic Rayon 40 + Polyneon covered)
- Delta-E distribution across 50 random test colors
- Delta-E distribution across 10 real customer logos
- Time to match a full design palette
- User validation: do team members agree with the auto-selected threads?

---

## Deliverables

1. `madeira_catalogue.json` — Complete thread database
2. Color matching Python module
3. Web UI for color matching visualization
4. Comparison scorecard for matching algorithms
5. **Design recommendation:** Which matching algorithm + palette strategy for MVP

---

## Estimated Effort

2-3 sessions with Claude

## Dependencies

None — independent, can run in parallel with POCs 1-4.

## Risk

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| Madeira RGB data inaccurate | **Medium** — color matching unreliable | Low-Medium | Validates against physical thread spools |

---

## Reference Documents

- [Embroidery File Generation Deep Research Brief](./Embroidery_File_Generation_Deep_Research.md)
