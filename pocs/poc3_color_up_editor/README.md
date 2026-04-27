# POC 3: Interactive Color-Up Editor

Spec: [../../POC_3_Color_Up_Editor.md](../../POC_3_Color_Up_Editor.md)

Web-based editor: load a DST, display its color regions, click-to-select, reassign Madeira threads, see the preview update in real time. Bake-off across frontend frameworks (SVG + vanilla JS, Canvas + React, Fabric.js, Three.js + React).

**Status:** **blocked.** Depends on:

- POC 1 — at minimum the parser + one usable renderer
- POC 2 — the Madeira catalogue + at least the recommended matching algorithm

Don't start until those two POCs have hit their MVP thresholds. When unblocking, write a `NEXT.md` here defining the first task (probably: pick stack, render a parsed DST in the browser, then add click-to-select).
