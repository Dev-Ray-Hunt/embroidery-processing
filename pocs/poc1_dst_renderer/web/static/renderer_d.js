// Renderer D — HTML5 Canvas 2D.
//
// Draws stitches as thick round-capped lines, batched per color block.
// Interactive: wheel zoom (about the cursor), drag pan, hover highlights the
// color block under the cursor (a rehearsal of POC 3's color-up editor).
//
// Hit-testing uses a hidden "picking" canvas: every block is drawn there in a
// unique flat color, so the block under the cursor is one getImageData away —
// no per-segment distance math on 60k-stitch designs.
//
// Exports mount(area, design, fabricHex) -> { setFabric, destroy, renderMs }.

const THREAD_WIDTH_DST_UNITS = 4; // 0.4 mm; 1 DST unit = 0.1 mm
const MARGIN_FRAC = 0.04;

function buildBlocks(design) {
  // Mirror of the server-side design_geometry logic: STITCH draws from the
  // previous point; everything else moves the pen; COLOR_CHANGE starts a block.
  const blocks = [[]];
  let prev = null;
  for (const [x, y, cmd] of design.stitches) {
    if (cmd === 'STITCH') {
      if (prev) blocks[blocks.length - 1].push([prev[0], prev[1], x, y]);
      prev = [x, y];
    } else if (cmd === 'COLOR_CHANGE') {
      blocks.push([]);
      // Thread is cut at a color change — no connector into the new block.
      prev = null;
    } else {
      prev = [x, y];
    }
  }
  return blocks;
}

export function mount(area, design, fabricHex) {
  area.innerHTML = '';
  const canvas = document.createElement('canvas');
  canvas.className = 'client-canvas';
  area.appendChild(canvas);

  const dpr = window.devicePixelRatio || 1;
  const cssW = area.clientWidth || 360;
  const cssH = area.clientHeight || 300;
  canvas.width = Math.round(cssW * dpr);
  canvas.height = Math.round(cssH * dpr);
  canvas.style.width = `${cssW}px`;
  canvas.style.height = `${cssH}px`;

  const ctx = canvas.getContext('2d');
  const pick = document.createElement('canvas');
  pick.width = canvas.width;
  pick.height = canvas.height;
  const pctx = pick.getContext('2d', { willReadFrequently: true });

  const [minX, minY, maxX, maxY] = design.extents;
  const wU = Math.max(maxX - minX, 1e-6);
  const hU = Math.max(maxY - minY, 1e-6);
  const blocks = buildBlocks(design);

  // View state: scale (px per DST unit) and offset, mutated by zoom/pan.
  const fit = (1 - 2 * MARGIN_FRAC) * Math.min(canvas.width / wU, canvas.height / hU);
  const view = {
    scale: fit,
    ox: (canvas.width - wU * fit) / 2 - minX * fit,
    oy: (canvas.height - hU * fit) / 2 - minY * fit,
  };

  let fabric = fabricHex;
  let hoverBlock = -1;
  let renderMs = 0;

  function drawScene(target, picking) {
    const t0 = performance.now();
    target.setTransform(1, 0, 0, 1, 0, 0);
    target.fillStyle = picking ? '#000000' : fabric;
    target.fillRect(0, 0, canvas.width, canvas.height);
    target.setTransform(view.scale, 0, 0, view.scale, view.ox, view.oy);
    target.lineCap = 'round';
    target.lineJoin = 'round';
    target.lineWidth = THREAD_WIDTH_DST_UNITS;

    blocks.forEach((segs, i) => {
      if (picking) {
        // Encode block index i as a unique flat color: R = i + 1.
        target.strokeStyle = `rgb(${i + 1}, 0, 0)`;
      } else {
        target.strokeStyle = design.block_colors[i % design.block_colors.length];
        target.globalAlpha = hoverBlock >= 0 && hoverBlock !== i ? 0.18 : 1.0;
      }
      target.beginPath();
      for (const [x0, y0, x1, y1] of segs) {
        target.moveTo(x0, y0);
        target.lineTo(x1, y1);
      }
      target.stroke();
    });
    target.globalAlpha = 1.0;
    if (!picking) renderMs = performance.now() - t0;
  }

  function redraw() {
    drawScene(ctx, false);
  }

  function redrawPick() {
    drawScene(pctx, true);
  }

  redraw();
  redrawPick();

  // --- Interactivity -------------------------------------------------------
  function canvasPoint(ev) {
    const r = canvas.getBoundingClientRect();
    return [((ev.clientX - r.left) / r.width) * canvas.width, ((ev.clientY - r.top) / r.height) * canvas.height];
  }

  let dragging = false;
  let last = null;
  let pickDirty = false;

  canvas.addEventListener('wheel', (ev) => {
    ev.preventDefault();
    const [cx, cy] = canvasPoint(ev);
    const k = ev.deltaY < 0 ? 1.15 : 1 / 1.15;
    // Zoom about the cursor: keep the design point under it fixed.
    view.ox = cx - (cx - view.ox) * k;
    view.oy = cy - (cy - view.oy) * k;
    view.scale *= k;
    pickDirty = true;
    redraw();
  });

  canvas.addEventListener('pointerdown', (ev) => {
    dragging = true;
    last = canvasPoint(ev);
    canvas.setPointerCapture(ev.pointerId);
  });
  canvas.addEventListener('pointerup', (ev) => {
    dragging = false;
    canvas.releasePointerCapture(ev.pointerId);
    if (pickDirty) {
      redrawPick();
      pickDirty = false;
    }
  });
  canvas.addEventListener('pointermove', (ev) => {
    const pt = canvasPoint(ev);
    if (dragging) {
      view.ox += pt[0] - last[0];
      view.oy += pt[1] - last[1];
      last = pt;
      pickDirty = true;
      redraw();
      return;
    }
    if (pickDirty) {
      redrawPick();
      pickDirty = false;
    }
    const px = pctx.getImageData(Math.round(pt[0]), Math.round(pt[1]), 1, 1).data;
    const block = px[0] > 0 ? px[0] - 1 : -1;
    if (block !== hoverBlock) {
      hoverBlock = block;
      redraw();
    }
  });
  canvas.addEventListener('pointerleave', () => {
    if (hoverBlock !== -1) {
      hoverBlock = -1;
      redraw();
    }
  });

  return {
    setFabric(hex) {
      fabric = hex;
      redraw();
    },
    get renderMs() {
      return renderMs;
    },
    destroy() {
      area.innerHTML = '';
    },
  };
}
