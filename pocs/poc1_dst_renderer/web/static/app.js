// POC 1 bake-off UI — vanilla JS, no build step.
//
// Loads the DST list and renderer registry from the backend, builds the
// 5-panel grid, and re-renders all server-side panels when the user picks
// a DST. Client-side renderers (D, E) will plug in later.

const grid = document.getElementById('grid');
const dstItems = document.getElementById('dst-items');

let renderers = [];
let selectedFilename = null;
let selectedItem = null;

function fmtNumber(n) {
  return n.toLocaleString();
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

  // Trigger every server-side implemented renderer in parallel.
  const tasks = renderers
    .filter((r) => r.implemented && r.kind === 'server')
    .map((r) => renderPanel(r.id, filename));
  await Promise.all(tasks);
}

async function renderPanel(rendererId, filename) {
  const article = grid.querySelector(`.renderer[data-renderer="${rendererId}"]`);
  if (!article) return;
  const area = article.querySelector('.render-area');
  area.innerHTML = `<span class="placeholder">Rendering…</span>`;

  const url = `/api/render/${rendererId}/${encodeURIComponent(filename)}?t=${Date.now()}`;
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

(async function init() {
  await loadRenderers();
  await loadDsts();
})();
