# Spool photo capture protocol (POC 2 Task 3)

Ten physical Madeira spools from Straight Down inventory, photographed to
validate the catalogue's RGB values against reality. Written now so the
on-site session is a checklist, not a design exercise.

## Which spools

Pick 10 spanning the range — and **prefer catalog numbers that are
conflict-flagged in the catalogue** (`conflict: true` entries are where the
sources disagree, so a photo settles the argument):

- 2 light (white, pastel)
- 2 dark (black, navy)
- 2 saturated (a bright red, a bright blue)
- 2 mid-tone neutrals (gold/tan, gray)
- 2 edge cases (a metallic and/or a fluorescent if stocked — these will fail
  RGB matching; that failure is itself a documented finding)

## Setup

- Daylight near a window (no direct sun), or daylight-balanced (5000-6500K)
  lamp. No mixed lighting (overhead fluorescents off).
- White printer paper as background AND as white reference in every frame.
- Phone camera, no flash, no filters; lock exposure if possible (long-press
  on iPhone). Shoot from ~30cm, spool flat, thread face toward camera.
- One photo per spool, whole spool + label visible.

## Naming & storage

`data/madeira_sources/spool_photos/<line>_<catalog>.jpg`
e.g. `classic_1147.jpg`, `polyneon_1801.jpg`. Gitignored like all data.

## Processing (scripted later, Step 4)

1. White-balance each photo against the paper region.
2. Sample mean RGB from a thread-only patch (avoid specular highlights on
   the spool's curve — sample the flattest face).
3. Convert to Lab, compute ΔE2000 vs the catalogue entry.
4. ΔE < 5 → catalogue value validated. ΔE ≥ 5 → flag entry, prefer the
   photo-derived value after a second opinion (re-photograph or compare
   against the physical color card).
