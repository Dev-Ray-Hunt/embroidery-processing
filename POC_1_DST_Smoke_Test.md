# POC 1: DST Smoke Test

## Proof of Concept — Project Requirements Document

---

## Objective

Prove that we can programmatically generate a DST file that a Barudan machine will accept, load, and stitch correctly.

## Why This Is First

If we can't write a valid DST file that the machine accepts, nothing else matters. This is the single highest-risk validation.

---

## Global Constraints

| Constraint | Value |
|-----------|-------|
| **Builder** | Brandon + Claude/AI agents |
| **Primary language** | Python 3.10+ (backend/engine) |
| **Target machine** | Barudan embroidery machines via BNet software |
| **Primary output format** | DST (Tajima) — universal compatibility |
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

A Python script that generates hardcoded geometric shapes as stitch patterns and writes them to DST files.

## Test Designs

1. **Filled rectangle** (50mm × 30mm) — Tests fill stitch generation and DST encoding
2. **Filled circle** (40mm diameter) — Tests curved-boundary fill handling
3. **Satin-stitched border** (2mm wide rectangle outline) — Tests satin stitch encoding
4. **Multi-color design** (two rectangles, different colors) — Tests color-change commands
5. **Running stitch outline** (star shape) — Tests running stitch encoding

---

## Bake-Off: DST Writing Approaches

| Option | Description | What To Test |
|--------|-------------|-------------|
| **A. pyembroidery** | Use pyembroidery's `write()` function with `EmbPattern` objects | Generate all 5 test designs, write to DST, validate on machine |
| **B. libembroidery (via Python wrapper)** | Use libembroidery's C library through ctypes/cffi | Same 5 designs, compare output file byte-for-byte with Option A |
| **C. Custom DST writer** | Write our own DST encoder following the spec from the research doc | Same 5 designs, validate header/body structure, test on machine |

---

## Pass/Fail Criteria

- [ ] All 5 DST files load without error on Barudan machine
- [ ] All 5 designs stitch correctly (correct shapes, no thread breaks from bad encoding)
- [ ] Color changes occur at the correct points in the multi-color design
- [ ] Stitch count in header matches actual stitch records in body
- [ ] File passes `(file_size - 512) % 3 == 0` validation

---

## Measurements To Record

- File size per design
- Processing time per design
- Machine load time (subjective: instant / noticeable delay / slow)
- Any machine errors or warnings displayed
- Stitch quality assessment (photo the stitched output)

---

## Deliverables

1. Python script(s) for each approach
2. 5 DST files per approach (15 total)
3. Photos of stitched output from each approach
4. Comparison scorecard (Reliability / Quality / Speed / Flexibility)
5. **Design recommendation:** Which DST writing approach to use for MVP

---

## Estimated Effort

1-2 sessions with Claude

## Dependencies

None — this is the first POC.

## Risk

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| DST files rejected by Barudan | **Critical** — blocks everything | Low (format is well-spec'd) | POC 1 is first; use pyembroidery's battle-tested writer |

---

## Reference Documents

- [Embroidery File Generation Deep Research Brief](./Embroidery_File_Generation_Deep_Research.md)
