# shared/

Python utilities that more than one POC needs. Empty for now.

## What belongs here

- Color-space math (RGB ↔ CIELAB, Delta-E variants) — POC 2 builds it, POC 3 reuses it.
- DST stitch-data structures — once POC 1's parser settles, the canonical types and JSON schema live here so POC 3's editor can consume them without depending on POC 1's package.
- Anything else that turns out to be reused by a second POC.

## What doesn't

- Code only one POC uses. Keep it inside that POC's `src/`.
- Frontend code. POC-specific JS/TS lives next to its POC.
- Throwaway scaffolding. Demo runners, comparison-gallery generators, etc., live with their POC.

Rule of thumb: don't promote code to `shared/` until a second POC actually imports it.
