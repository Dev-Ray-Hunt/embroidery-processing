# POC 1 — Next Step: Human Evaluation

All five renderers are built and machine-verified (see
[VERIFICATION.md](VERIFICATION.md)); measurements and provisional scores are
in [FINDINGS.md](FINDINGS.md). What remains is the part only a human can do.

## Brandon's evaluation pass

1. **Gallery review** — `uv run python scripts/build_gallery.py`, then
   `open outputs/gallery/index.html`. All 105 renderer × design × fabric
   combinations on one page.
2. **Live interactivity check** —
   `uv run uvicorn pocs.poc1_dst_renderer.web.server:app --reload --port 8000`.
   Judge D's zoom/pan/hover-highlight and E's tilt *on a real GPU* (the
   automated pass ran software WebGL).
3. **Fill in the Q column** of the FINDINGS scorecard and accept/override the
   draft primary/secondary recommendation.
4. **Team preference ranking** (spec Step 3): show the gallery to the team,
   ask which they'd send to a customer.

## Blocked on external input

- **Stitched-sample photo** — one phone photo of a stitched-out design (from
  the team request). Without it, "visual fidelity vs. real embroidery" stays
  unscored. When it lands, drop it in `data/` and do the side-by-side against
  the same design in the gallery.

## Optional follow-ups (post-evaluation)

- Kajiya-Kay anisotropic shader for E; real-GPU performance pass.
- Procedural fabric weave texture (deliberately cut from this round).
- Madeira palette plumb-through once POC 2 produces real thread colors.
