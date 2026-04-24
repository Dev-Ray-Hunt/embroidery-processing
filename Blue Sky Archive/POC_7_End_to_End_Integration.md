# POC 7: End-to-End Pipeline Integration

## Proof of Concept — Project Requirements Document

---

## Objective

Prove the entire chain works: image input → auto-generation → preview → adjustment → DST export + proof image — as one continuous process.

## Why This Is Seventh

Individual components working in isolation doesn't guarantee they integrate smoothly. This POC stress-tests the interfaces between every module and measures end-to-end performance.

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

---

## What To Build

A single web application that orchestrates the full pipeline:

1. **Upload** — User uploads a PNG/JPG/SVG logo
2. **Process** — Backend runs: image preprocessing → color quantization → vectorization → stitch type classification → stitch generation → DST creation → preview rendering
3. **Preview** — Frontend displays the rendered preview with fabric background
4. **Adjust** — Team member can modify regions (from POC 6 editor)
5. **Export** — Generate final DST file + high-quality proof image (PNG/PDF)

---

## Test Scenarios

1. **Happy path** — Clean 3-color SVG logo → DST + preview in under 60 seconds
2. **Raster logo** — 4-color PNG logo with transparent background
3. **Edge case: many colors** — Logo with 8+ colors that need reduction
4. **Edge case: fine detail** — Logo with thin lines and small text
5. **Edge case: large design** — 200mm × 200mm design (max common hoop size)

---

## Pass/Fail Criteria

- [ ] End-to-end processing completes for all 5 test scenarios
- [ ] Total time from upload to preview display < 120 seconds
- [ ] Generated DST files stitch correctly on Barudan machine
- [ ] Preview image matches stitched output at an acceptable level
- [ ] Proof export produces a shareable PNG or PDF suitable for customer email
- [ ] No data loss or corruption when passing data between pipeline stages

---

## Measurements To Record

- End-to-end processing time (broken down by stage)
- Memory usage peak during processing
- File sizes (input image, intermediate data, DST output, preview image)
- Error rate across test scenarios
- Bottleneck identification (which stage is slowest?)

---

## Deliverables

1. Integrated web application
2. Performance profiling report (time per pipeline stage)
3. Stitched output photos for all 5 test scenarios
4. Side-by-side: preview vs. stitched photo
5. **Design recommendation:** Architecture for MVP pipeline (what to optimize, what to parallelize, what to cache)

---

## Estimated Effort

3-4 sessions with Claude

## Dependencies

- **All previous POCs (1-6)** must be complete

## Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| End-to-end too slow | **High** — blocks production use | Unknown (POC measures) | Profile each stage; optimize bottleneck identified |
| Pipeline integration failures | **High** — components don't fit together | Medium | Explicitly tests integration; standardize data formats between modules early |

---

## Reference Documents

- [Embroidery File Generation Deep Research Brief](./Embroidery_File_Generation_Deep_Research.md)
- [POC 1: DST Smoke Test](./POC_1_DST_Smoke_Test.md)
- [POC 2: Stitch Generation](./POC_2_Stitch_Generation.md)
- [POC 3: Image-to-Regions](./POC_3_Image_to_Regions.md)
- [POC 4: Stitch Preview Renderer](./POC_4_Stitch_Preview_Renderer.md)
- [POC 5: Thread Catalogue](./POC_5_Thread_Catalogue.md)
- [POC 6: Interactive Region Editor](./POC_6_Interactive_Region_Editor.md)
