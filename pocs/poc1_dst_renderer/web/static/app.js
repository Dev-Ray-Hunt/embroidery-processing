// POC 1 bake-off UI — vanilla JS ES modules, no build step.
//
// Loads the DST list, renderer registry, and fabric list from the backend,
// builds the 5-panel grid, and re-renders every panel when the user picks a
// DST or switches fabric. Server renderers (A-C) return PNGs; client
// renderers (D, E) draw into live canvases from the design JSON.

import { mount as mountD } from './renderer_d.js';
import { mount as mountE } from './renderer_e.js';

const CLIENT_RENDERERS = { d: mountD, e: mountE };

const grid = document.getElementById('grid');
const dstItems = document.getElementById('dst-items');
const fabricRow = document.getElementById('fabric-row');

let renderers = [];
let fabrics = [];
let selectedFabric = null;
let selectedFilename = null;
let selectedItem = null;

// Live client-renderer instances, keyed by renderer id, so fabric switches
// restyle in place instead of rebuilding 60k instanced meshes.
const clientMounts = {};
// Design JSON cache: filename -> parsed design (they're immutable).
const designCache = {};

function fmtNumber(n) {
  return n.toLocaleString();
}

function fabricHex() {
  return fabrics.find((f) => f.name === selectedFabric)?.hex ?? '#f2f1ec';
}

async function loadRenderers() {
  const r = await fetch('/api/renderers');
  if (!r.ok) {
    grid.innerHTML = `<p class="error">Failed to load renderers (${r.status})</p>`;
    return;
  }
  renderers = await r.json();
  buildGrid();
}

async function loadFabrics() {
  const r = await fetch('/api/fabrics');
  if (!r.ok) return;
  fabrics = await r.json();
  selectedFabric = fabrics.find((f) => f.default)?.name ?? fabrics[0]?.name;
  fabricRow.innerHTML = '';
  for (const f of fabrics) {
    const btn = document.createElement('button');
    btn.className = 'fabric-swatch' + (f.name === selectedFabric ? ' selected' : '');
    btn.dataset.fabric = f.name;
    btn.style.setProperty('--swatch', f.hex);
    btn.title = f.name;
    btn.innerHTML = `<span class="chip"></span>${f.name}`;
    btn.addEventListener('click', () => selectFabric(f.name));
    fabricRow.appendChild(btn);
  }
}

function selectFabric(name) {
  if (name === selectedFabric) return;
  selectedFabric = name;
  fabricRow
    .querySelectorAll('.fabric-swatch')
    .forEach((b) => b.classList.toggle('selected', b.dataset.fabric === name));
  if (!selectedFilename) return;
  // Server panels re-render; client panels restyle in place.
  for (const r of renderers) {
    if (!r.implemented) continue;
    if (r.kind === 'server') renderServerPanel(r.id, selectedFilename);
    else clientMounts[r.id]?.setFabric(fabricHex());
  }
}

function buildGrid() {
  grid.innerHTML = '';
  for (const rend of renderers) {
    const article = document.createElement('article');
    article.className = 'renderer' + (rend.implemented ? '' : ' not-implemented');
    article.dataset.renderer = rend.id;
    article.innerHTML = `
      <h3>${rend.title}</h3>
      <p class="desc">${rend.desc}</p>
      <div class="render-area">
        <span class="placeholder">${
          rend.implemented ? 'Pick a DST →' : 'Not implemented yet'
        }</span>
      </div>
    `;
    grid.appendChild(article);
  }
}

async function loadDsts() {
  const r = await fetch('/api/dsts');
  if (!r.ok) {
    dstItems.innerHTML = `<li class="error">Failed to load (${r.status})</li>`;
    return;
  }
  const items = await r.json();
  dstItems.innerHTML = '';
  if (items.length === 0) {
    dstItems.innerHTML = `<li class="empty">No DSTs in data/sample_dsts/. Drop some in.</li>`;
    return;
  }
  for (const item of items) {
    const li = document.createElement('li');
    li.className = 'dst-item' + (item.error ? ' has-error' : '');
    li.dataset.filename = item.name;
    if (item.error) {
      li.innerHTML = `
        <span class="name">${item.name}</span>
        <span class="meta">parse error: ${item.error}</span>
      `;
    } else {
      li.innerHTML = `
        <span class="name">${item.name}</span>
        <span class="meta">
          ${fmtNumber(item.stitches)} stitches · ${item.color_blocks} colors ·
          ${item.width_mm} × ${item.height_mm} mm
        </span>
      `;
      li.addEventListener('click', () => selectDst(item.name, li));
    }
    dstItems.appendChild(li);
  }
}

async function selectDst(filename, li) {
  if (selectedItem) selectedItem.classList.remove('selected');
  li.classList.add('selected');
  selectedItem = li;
  selectedFilename = filename;

  const tasks = [];
  for (const r of renderers) {
    if (!r.implemented) continue;
    tasks.push(
      r.kind === 'server' ? renderServerPanel(r.id, filename) : renderClientPanel(r.id, filename)
    );
  }
  await Promise.all(tasks);
}

async function renderServerPanel(rendererId, filename) {
  const article = grid.querySelector(`.renderer[data-renderer="${rendererId}"]`);
  if (!article) return;
  const area = article.querySelector('.render-area');
  area.innerHTML = `<span class="placeholder">Rendering…</span>`;

  const url =
    `/api/render/${rendererId}/${encodeURIComponent(filename)}` +
    `?fabric=${encodeURIComponent(selectedFabric)}&t=${Date.now()}`;
  const t0 = performance.now();
  try {
    const resp = await fetch(url);
    if (!resp.ok) {
      const text = await resp.text();
      area.innerHTML = `<span class="error">${resp.status}: ${text}</span>`;
      return;
    }
    const blob = await resp.blob();
    const objectUrl = URL.createObjectURL(blob);
    const elapsed = (performance.now() - t0).toFixed(0);
    area.innerHTML = `
      <img src="${objectUrl}" alt="${rendererId} render of ${filename}">
      <span class="timing">${elapsed} ms</span>
    `;
    // Once the image has decoded the blob, the object URL can be released.
    article
      .querySelector('img')
      .addEventListener('load', () => URL.revokeObjectURL(objectUrl), { once: true });
  } catch (e) {
    area.innerHTML = `<span class="error">${e.message}</span>`;
  }
}

async function fetchDesign(filename) {
  if (designCache[filename]) return designCache[filename];
  const resp = await fetch(`/api/design/${encodeURIComponent(filename)}`);
  if (!resp.ok) throw new Error(`${resp.status}: ${await resp.text()}`);
  const design = await resp.json();
  designCache[filename] = design;
  return design;
}

async function renderClientPanel(rendererId, filename) {
  const article = grid.querySelector(`.renderer[data-renderer="${rendererId}"]`);
  if (!article) return;
  const area = article.querySelector('.render-area');
  delete area.dataset.rendered;
  area.innerHTML = `<span class="placeholder">Rendering…</span>`;

  try {
    clientMounts[rendererId]?.destroy();
    delete clientMounts[rendererId];

    const t0 = performance.now();
    const design = await fetchDesign(filename);
    const instance = CLIENT_RENDERERS[rendererId](area, design, fabricHex());
    clientMounts[rendererId] = instance;
    const total = (performance.now() - t0).toFixed(0);

    const timing = document.createElement('span');
    timing.className = 'timing';
    timing.textContent = `${total} ms (draw ${instance.renderMs.toFixed(0)} ms)`;
    area.appendChild(timing);
    // Mark painted for the automated harness.
    area.dataset.rendered = '1';
  } catch (e) {
    area.innerHTML = `<span class="error">${e.message}</span>`;
  }
}

(async function init() {
  await Promise.all([loadRenderers(), loadFabrics()]);
  await loadDsts();
})();
