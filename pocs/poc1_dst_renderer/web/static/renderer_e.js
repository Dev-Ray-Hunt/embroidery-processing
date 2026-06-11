// Renderer E — Three.js 2.5D instanced thread geometry.
//
// Each stitch is an instanced box, oriented along the stitch direction and
// slightly raised off a fabric plane. A directional key light over oriented
// 3D geometry produces angle-dependent sheen naturally (geometric anisotropy);
// a custom Kajiya-Kay hair shader is noted as future work in FINDINGS.
//
// Interactive: wheel zoom, drag pan, shift-drag (or right-drag) tilt — the
// "2.5D" payoff where raised stitches catch the light.
//
// Exports mount(area, design, fabricHex) -> { setFabric, destroy, renderMs }.

import * as THREE from './vendor/three.module.min.js';

const THREAD_W = 4; // DST units (0.4 mm)
const THREAD_H = 1.3; // raised thread height
const MAX_TILT = (38 * Math.PI) / 180;

function buildSegments(design) {
  // STITCH draws from the previous point; other commands move the pen.
  const segs = [];
  const colors = [];
  let prev = null;
  let block = 0;
  for (const [x, y, cmd] of design.stitches) {
    if (cmd === 'STITCH') {
      if (prev) {
        segs.push([prev[0], prev[1], x, y]);
        colors.push(block);
      }
      prev = [x, y];
    } else if (cmd === 'COLOR_CHANGE') {
      block += 1;
      prev = [x, y];
    } else {
      prev = [x, y];
    }
  }
  return { segs, colors };
}

export function mount(area, design, fabricHex) {
  area.innerHTML = '';
  const cssW = area.clientWidth || 360;
  const cssH = area.clientHeight || 300;

  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true });
  } catch (e) {
    area.innerHTML = `<span class="error">WebGL unavailable: ${e.message}</span>`;
    return { setFabric() {}, destroy() {}, renderMs: 0 };
  }
  renderer.setPixelRatio(window.devicePixelRatio || 1);
  renderer.setSize(cssW, cssH);
  renderer.domElement.className = 'client-canvas';
  area.appendChild(renderer.domElement);

  const scene = new THREE.Scene();

  // Design space: DST +y is down; negate y so the design reads upright.
  const [minX, minY, maxX, maxY] = design.extents;
  const cx = (minX + maxX) / 2;
  const cy = -(minY + maxY) / 2;
  const wU = Math.max(maxX - minX, 1);
  const hU = Math.max(maxY - minY, 1);

  // Fabric plane, comfortably larger than the design.
  const fabricMat = new THREE.MeshStandardMaterial({
    color: new THREE.Color(fabricHex),
    roughness: 0.92,
    metalness: 0.0,
  });
  const fabricSize = Math.max(wU, hU) * 1.6;
  const fabric = new THREE.Mesh(new THREE.PlaneGeometry(fabricSize, fabricSize), fabricMat);
  fabric.position.set(cx, cy, 0);
  scene.add(fabric);

  // Instanced stitches.
  const { segs, colors } = buildSegments(design);
  const geo = new THREE.BoxGeometry(1, 1, 1);
  const mat = new THREE.MeshStandardMaterial({ roughness: 0.5, metalness: 0.12 });
  const mesh = new THREE.InstancedMesh(geo, mat, segs.length);
  const dummy = new THREE.Object3D();
  const tint = new THREE.Color();
  for (let i = 0; i < segs.length; i++) {
    const [x0, y0, x1, y1] = segs[i];
    const dx = x1 - x0;
    const dy = -(y1 - y0); // y negated into world space
    // Extend by the thread width so adjacent stitches overlap like round caps
    // would — without this, fills show dark gaps at every stitch joint.
    const len = Math.hypot(dx, dy) + THREAD_W * 0.9;
    // Deterministic per-stitch height jitter — breaks up perfectly flat fills.
    const jitter = 0.94 + 0.12 * (((i * 2654435761) >>> 16) % 1000) / 1000;
    // Later stitches sit ON TOP of earlier ones (like real thread): a small
    // monotonic rise by stitch order prevents z-fighting where, e.g., white
    // lettering is stitched over a gold fill.
    const stack = (i / segs.length) * 2.0;
    dummy.position.set((x0 + x1) / 2, -(y0 + y1) / 2, stack + (THREAD_H * jitter) / 2);
    dummy.rotation.set(0, 0, Math.atan2(dy, dx));
    dummy.scale.set(len, THREAD_W, THREAD_H * jitter);
    dummy.updateMatrix();
    mesh.setMatrixAt(i, dummy.matrix);
    mesh.setColorAt(
      i,
      tint.set(design.block_colors[colors[i] % design.block_colors.length])
    );
  }
  mesh.instanceMatrix.needsUpdate = true;
  if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
  scene.add(mesh);

  // Lights: key from upper-left (matches B's "horizontal = bright" look).
  const key = new THREE.DirectionalLight(0xffffff, 1.7);
  key.position.set(-0.4 * fabricSize, 0.5 * fabricSize, 0.9 * fabricSize);
  key.target.position.set(cx, cy, 0);
  scene.add(key, key.target);
  scene.add(new THREE.AmbientLight(0xffffff, 1.15));

  // Orthographic top-down camera fitted to the design with margin.
  const aspect = cssW / cssH;
  let halfH = (Math.max(hU, wU / aspect) / 2) * 1.1;
  const camera = new THREE.OrthographicCamera(
    -halfH * aspect,
    halfH * aspect,
    halfH,
    -halfH,
    1,
    fabricSize * 6
  );
  const camDist = fabricSize * 2;
  const target = new THREE.Vector3(cx, cy, 0);
  let tilt = 0; // polar angle from straight-down
  let azimuth = 0;

  function placeCamera() {
    camera.position.set(
      target.x + camDist * Math.sin(tilt) * Math.sin(azimuth),
      target.y - camDist * Math.sin(tilt) * Math.cos(azimuth),
      target.z + camDist * Math.cos(tilt)
    );
    camera.up.set(0, 1, 0);
    camera.lookAt(target);
    camera.updateProjectionMatrix();
  }

  let renderMs = 0;
  let queued = false;
  function render() {
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => {
      queued = false;
      const t0 = performance.now();
      renderer.render(scene, camera);
      renderMs = performance.now() - t0;
    });
  }

  placeCamera();
  // First render measured synchronously so renderMs is meaningful immediately.
  {
    const t0 = performance.now();
    renderer.render(scene, camera);
    renderMs = performance.now() - t0;
  }

  // --- Interactivity -------------------------------------------------------
  const el = renderer.domElement;
  el.addEventListener('contextmenu', (ev) => ev.preventDefault());
  el.addEventListener('wheel', (ev) => {
    ev.preventDefault();
    camera.zoom *= ev.deltaY < 0 ? 1.15 : 1 / 1.15;
    camera.updateProjectionMatrix();
    render();
  });

  let mode = null; // 'pan' | 'tilt'
  let last = null;
  el.addEventListener('pointerdown', (ev) => {
    mode = ev.shiftKey || ev.button === 2 ? 'tilt' : 'pan';
    last = [ev.clientX, ev.clientY];
    el.setPointerCapture(ev.pointerId);
  });
  el.addEventListener('pointerup', (ev) => {
    mode = null;
    el.releasePointerCapture(ev.pointerId);
  });
  el.addEventListener('pointermove', (ev) => {
    if (!mode) return;
    const dx = ev.clientX - last[0];
    const dy = ev.clientY - last[1];
    last = [ev.clientX, ev.clientY];
    if (mode === 'pan') {
      const unitsPerPx = (camera.top - camera.bottom) / camera.zoom / el.clientHeight;
      target.x -= dx * unitsPerPx;
      target.y += dy * unitsPerPx;
    } else {
      tilt = Math.min(MAX_TILT, Math.max(0, tilt + dy * 0.005));
      azimuth += dx * 0.005;
    }
    placeCamera();
    render();
  });

  return {
    setFabric(hex) {
      fabricMat.color.set(hex);
      render();
    },
    get renderMs() {
      return renderMs;
    },
    destroy() {
      renderer.dispose();
      geo.dispose();
      mat.dispose();
      fabricMat.dispose();
      area.innerHTML = '';
    },
  };
}
