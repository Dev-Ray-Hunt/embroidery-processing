# Coloring Up Engine

POC repo for an embroidery coloring-up and proof-approval engine. **Learning-first technology exploration**, not a product build with a deadline.

For the full framing, read [POC_PRD_Coloring_Up_Engine.md](POC_PRD_Coloring_Up_Engine.md).

## What's in this repo

- **POC specs** at the repo root (`POC_PRD_*`, `POC_1_*` through `POC_4_*`, and the future-state `PRD_Coloring_Up_Order_Management.md`).
- **`pocs/`** — one folder per POC. Each has a `README.md` (links to its spec), a `FINDINGS.md` (the writeup deliverable), and source / tests directories.
  - `poc1_dst_renderer/` — DST → preview image, 5-way bake-off
  - `poc2_thread_catalogue/` — Madeira thread DB + color-matching algorithm bake-off
  - `poc3_color_up_editor/` — interactive web editor (blocked on POCs 1 & 2)
  - `poc4_order_workflow/` — order → proof → approval workflow (blocked on POC 3)
- **`shared/`** — cross-POC Python utilities. Empty for now; first occupant will be color-space math.
- **`data/`** — gitignored. Drop public sample DSTs into `data/sample_dsts/`, Madeira source files into `data/madeira_sources/`. See `data/README.md` for sources.
- **`outputs/`** — gitignored. Render artifacts, scorecards, comparison galleries.
- **`Trim Sheet Examples/`** — reference PDFs of the production trim sheet format the full app will eventually generate.
- **`Blue Sky Archive/`** — earlier embroidery *generation* roadmap, archived in favor of the simpler "render existing DSTs" approach.

## Setup

Requires Python 3.12 and [`uv`](https://docs.astral.sh/uv/).

```bash
uv sync                    # creates .venv/ and installs deps
uv run pytest              # runs tests (zero today; should exit clean)
uv run ruff check .        # lint
uv run ruff format .       # format
```

## Test data

This project is **architecturally and source-isolated** from Straight Down's Wilcom toolchain. No production DSTs land here — only public sample DSTs (e.g., from `pyembroidery`'s test corpus). See `data/README.md` for sources and licensing.

## Where to start

POC 1 and POC 2 have no dependencies on each other and are intended to run in parallel:

- POC 1 first task: [pocs/poc1_dst_renderer/NEXT.md](pocs/poc1_dst_renderer/NEXT.md)
- POC 2 first task: [pocs/poc2_thread_catalogue/NEXT.md](pocs/poc2_thread_catalogue/NEXT.md)
