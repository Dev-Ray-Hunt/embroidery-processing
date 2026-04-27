# POC 2: Thread Catalogue & Color Matching

Spec: [../../POC_2_Thread_Catalogue.md](../../POC_2_Thread_Catalogue.md)

Build a Madeira thread color database (≥ 200 threads, RGB + CIELAB validated) and bake off color-matching algorithms (CIEDE2000, CIE76, RGB Euclidean, CMC l:c) plus palette-optimization strategies (greedy, constrained, perceptual clustering).

**Status:** scaffolded; no code yet. Start with [NEXT.md](NEXT.md).

**Layout:**

```
poc2_thread_catalogue/
├── README.md       (this file)
├── NEXT.md         (explicit first task — Madeira data collection + catalogue build)
├── FINDINGS.md     (writeup deliverable)
├── src/            (Python catalogue builder, matching algorithms, palette optimizers)
└── tests/          (pytest tests)
```

A small validation web UI ships later in the POC; defer setup until the catalogue exists and the matching algorithms have at least one implementation.

**Source data:** downloaded charts (Madeira Metro, EZ Stitch, Madeira digital chart, Isacord cross-reference) → `data/madeira_sources/` (gitignored). **Non-Wilcom sources only** — no Wilcom thread-database export.

**Outputs:** `madeira_catalogue.json`, scorecards, validation visuals → `outputs/poc2/` (gitignored).
