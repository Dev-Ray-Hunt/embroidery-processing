"""POC 1 renderer implementations.

One module per bake-off entry. Each module exposes a `render_png(dst_path: Path) -> bytes`
function that takes a DST file path and returns PNG bytes.

- a_pyembroidery: pyembroidery's built-in PNG writer (zero custom code, baseline).
- (b_pillow): Pillow 2D with angle-based shading. Not implemented yet.
- c_cairo: PyCairo antialiased vector with round caps and a sheen pass.
- D and E (browser-side Canvas / Three.js) live in web/static/, not here.
"""
