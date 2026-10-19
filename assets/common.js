/* Shared helpers for the flux site (version 2, October 2026). */
const NAV = [
  ["index.html", "Accueil"],
  ["article/index.html", "Article"],
  ["maths/index.html", "Statistiques"],
  ["data/index.html", "Données"],
  ["code/index.html", "Code et résultats"],
];
const PART_A = [];

const METRICS = {
  len:     { label: "dependency length", short: "length", color: "--c-len" },
  flux:    { label: "flux size", short: "flux", color: "--c-flux" },
  weight:  { label: "flux weight", short: "weight", color: "--c-weight" },
  pot:     { label: "potential flux (stack)", short: "potential", color: "--c-pot" },
  pot2:    { label: "potential flux, closed function words", short: "potential*", color: "--c-pot2" },
  potR:    { label: "potential flux, right to left", short: "potential ←", color: "--c-potR" },
  pot2R:   { label: "potential flux*, right to left", short: "potential* ←", color: "--c-pot2R" },
  lvert:   { label: "observed left vertices (words actually linked to the right)", short: "left vertices", color: "--c-lvert" },
  rvert:   { label: "right-vertex flux", short: "right vertices", color: "--c-rvert" },
  depwait: { label: "dependents waiting for governor", short: "dep-waiting", color: "--c-depwait" },
  govwait: { label: "governors waiting for dependent", short: "gov-waiting", color: "--c-govwait" },
};
const MAIN3 = ["len", "flux", "weight"];
const MAIN4 = MAIN3;
const VIEWS = { SUD: "SUD", UD: "UD", ContentUD: "ContentUD" };
const VIEW_DESC = { SUD: "SUD trees", UD: "UD trees", ContentUD: "UD trees, content words only" };
const FILTERS = { all: "with macro-syntax", micro: "without macro-syntax", norep: "without macro-syntax and reparandum" };
const BINS = { "all": "all sentences", "2-9": "2–9 words", "10-19": "10–19 words", "20-29": "20–29 words",
               "10-29": "10–29 words", "10+": "≥ 10 words", "20+": "≥ 20 words" };
const binKey = b => b.replace("+", "p");
function tableFile(view, filter, kind, bin) { return `data/table_${view}_${filter}_${kind}_${binKey(bin)}.json`; }

/* generic control bar: specs = [{k, label, type: "seg"|"select", options: {value: label}}] */
function makeControls(el, st, specs, onChange) {
  el.innerHTML = specs.map(sp => {
    if (sp.type === "seg")
      return `<label>${sp.label} <span class="seg" data-k="${sp.k}">${Object.entries(sp.options).map(([v, l]) => `<button data-v="${v}">${l}</button>`).join("")}</span></label>`;
    if (sp.type === "check")
      return `<label><input type="checkbox" data-k="${sp.k}"> ${sp.label}</label>`;
    return `<label>${sp.label} <select data-k="${sp.k}">${Object.entries(sp.options).map(([v, l]) => `<option value="${v}">${l}</option>`).join("")}</select></label>`;
  }).join("");
  const sync = () => {
    el.querySelectorAll(".seg").forEach(s => s.querySelectorAll("button").forEach(b => b.classList.toggle("on", String(st[s.dataset.k]) === b.dataset.v)));
    el.querySelectorAll("select[data-k]").forEach(s => s.value = st[s.dataset.k]);
    el.querySelectorAll("input[type=checkbox][data-k]").forEach(c => c.checked = !!st[c.dataset.k]);
  };
  el.querySelectorAll(".seg").forEach(s => s.querySelectorAll("button").forEach(b => b.onclick = () => { st[s.dataset.k] = b.dataset.v; sync(); onChange(); }));
  el.querySelectorAll("select[data-k]").forEach(s => s.onchange = () => { st[s.dataset.k] = s.value; sync(); onChange(); });
  el.querySelectorAll("input[type=checkbox][data-k]").forEach(c => c.onchange = () => { st[c.dataset.k] = c.checked; sync(); onChange(); });
  sync();
  return sync;
}
const VIEW_SPEC = { k: "view", label: "Trees", type: "seg", options: VIEWS };
const FILTER_SPEC = { k: "filter", label: "Relations", type: "select", options: { all: FILTERS.all, micro: FILTERS.micro } };
const FILTER_SPEC_FR = { k: "filter", label: "Relations", type: "select", options: FILTERS };
const BIN_SPEC = { k: "bin", label: "Sentences", type: "select", options: BINS };

function cssVar(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }
function mcolor(m) { return cssVar(METRICS[m] ? METRICS[m].color : "--accent"); }

function fmt(x, d = 2) {
  if (x === null || x === undefined || Number.isNaN(x)) return "–";
  if (typeof x !== "number") return x;
  return x.toFixed(d);
}
function fmtInt(x) {
  if (x === null || x === undefined) return "–";
  return Math.round(x).toLocaleString("en-US").replace(/,/g, " ");
}
function qs(name, dflt) { const v = new URLSearchParams(location.search).get(name); return v === null ? dflt : v; }
function setQs(obj) {
  const p = new URLSearchParams(location.search);
  for (const [k, v] of Object.entries(obj)) p.set(k, v);
  history.replaceState(null, "", location.pathname + "?" + p.toString());
}
const _cache = {};
async function getJSON(path) {
  if (!_cache[path]) _cache[path] = fetch(path).then(r => { if (!r.ok) throw new Error(path + " " + r.status); return r.json(); });
  return _cache[path];
}

function header() {
  const here = location.pathname.split("/").pop() || "index.html";
  const inA = PART_A.some(([f]) => f === here);
  const h = document.createElement("header");
  h.className = "top";
  h.innerHTML = `<div class="inner"><a class="brand" href="${location.pathname.includes("/article/") || location.pathname.includes("/maths/") || location.pathname.includes("/data/") || location.pathname.includes("/code/") ? "../" : ""}index.html">Le flux de dépendance · oral et écrit</a>
    <nav>${NAV.map(([f, t, part]) => `<a href="${(location.pathname.match(/\/(article|maths|data|code)\//) ? "../" : "") + f}" class="${location.pathname.endsWith("/" + f) || (f === "index.html" && !location.pathname.match(/\/(article|maths|data|code)\//)) ? "active" : ""}">${t}</a>`).join("")}</nav>
    <span class="spacer"></span><button class="btn" id="themeBtn" title="Toggle light/dark">◐</button></div>
    ${inA ? `<div class="subnav"><span class="muted small">Part A · flux size, flux weight, dependency length:</span>
      ${PART_A.map(([f, t]) => `<a href="${f}" class="${f === here ? "active" : ""}">${t}</a>`).join("")}</div>` : ""}`;
  document.body.prepend(h);
  const saved = (() => { try { return localStorage.getItem("flux-theme"); } catch (e) { return null; } })();
  if (saved) document.documentElement.setAttribute("data-theme", saved);
  h.querySelector("#themeBtn").onclick = () => {
    const cur = document.documentElement.getAttribute("data-theme") ||
      (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    const nxt = cur === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", nxt);
    try { localStorage.setItem("flux-theme", nxt); } catch (e) {}
    location.reload();
  };
  const f = document.createElement("footer");
  f.innerHTML = `Sylvain Kahane & Kim Gerdes · site compagnon de l'article « Le flux de dépendance, une mesure de la complexité syntaxique : l'oral et l'écrit en français » · <a href="https://github.com/typometrics/flux-oral-ecrit">github.com/typometrics/flux-oral-ecrit</a>`;
  document.body.append(f);
}
document.addEventListener("DOMContentLoaded", header);

/* Plotly defaults */
function plotLayout(extra = {}) {
  const t = cssVar("--text"), m = cssVar("--muted"), g = cssVar("--border");
  const base = {
    paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
    font: { family: cssVar("--sans") || "sans-serif", size: 12, color: t },
    margin: { l: 56, r: 16, t: 30, b: 46 },
    xaxis: { gridcolor: g, zerolinecolor: g, linecolor: m, tickcolor: m },
    yaxis: { gridcolor: g, zerolinecolor: g, linecolor: m, tickcolor: m },
    legend: { orientation: "h", y: -0.2, font: { size: 11 } },
    hoverlabel: { font: { size: 12 } },
  };
  const out = Object.assign({}, base, extra);
  for (const ax of ["xaxis", "yaxis", "xaxis2", "yaxis2"]) if (extra[ax]) out[ax] = Object.assign({}, base[ax] || base.xaxis, extra[ax]);
  return out;
}
const PCONF = { displaylogo: false, responsive: true, modeBarButtonsToRemove: ["lasso2d", "select2d"] };

/* truncated power law curve, normalised on 1..xmax */
function tplCurve(beta, lambda, xmax, xs) {
  let z = 0;
  for (let x = 1; x <= xmax; x++) z += Math.pow(x, -beta) * Math.exp(-lambda * x);
  return xs.map(x => Math.pow(x, -beta) * Math.exp(-lambda * x) / z);
}

/* sortable table: rows = array of objects, cols = [{key, label, sub, fmt, cls, html}] */
function renderTable(el, cols, rows, opts = {}) {
  let sortKey = opts.sortKey || cols[0].key, sortDir = opts.sortDir || 1;
  function draw() {
    const rs = rows.slice().sort((a, b) => {
      const x = a[sortKey], y = b[sortKey];
      if (x === y) return 0;
      if (x === null || x === undefined || Number.isNaN(x)) return 1;
      if (y === null || y === undefined || Number.isNaN(y)) return -1;
      return (x < y ? -1 : 1) * sortDir;
    });
    const head = "<tr>" + cols.map(c => `<th data-k="${c.key}" class="${c.cls || ""} ${c.nosort ? "nosort" : ""} ${c.key === sortKey ? (sortDir > 0 ? "sorted-asc" : "sorted-desc") : ""}" title="${c.title || ""}">${c.label}${c.sub ? `<span class="sub">${c.sub}</span>` : ""}</th>`).join("") + "</tr>";
    const body = rs.map(r => "<tr>" + cols.map(c => `<td class="${c.cls || ""} ${c.tdcls || ""}">${c.html ? c.html(r) : (c.fmt ? c.fmt(r[c.key]) : (r[c.key] ?? "–"))}</td>`).join("") + "</tr>").join("");
    el.innerHTML = `<table class="data"><thead>${head}</thead><tbody>${body}</tbody></table>`;
    el.querySelectorAll("th").forEach(th => th.onclick = () => {
      const k = th.dataset.k; const c = cols.find(c => c.key === k);
      if (c.nosort) return;
      if (k === sortKey) sortDir = -sortDir; else { sortKey = k; sortDir = (c.desc ? -1 : 1); }
      draw();
    });
    if (opts.after) opts.after(el, rs);
  }
  draw();
  return { redraw: (newRows) => { rows = newRows; draw(); } };
}

/* tiny inline log-log svg of relative frequencies: dists = {metric: [[x,count],...]}.
   x = 1…40 and relative frequency 1…1e-5, both logarithmic, faint grid at n = 10 and at 1e-2, 1e-4.
   Only values seen at least MINC times are drawn, and each curve stops at the first value below
   that (or at the first missing value): the far tail of a small sample is a staircase of single
   occurrences at 1/N, which would otherwise look like a flat plateau. */
const SPARK_MINC = 5;
function sparkSVG(dists, w = 150, h = 54, metrics = MAIN4) {
  const pad = 3, xmin = 0, xmax = Math.log10(40), ymin = -5, ymax = 0;
  const X = v => pad + (Math.log10(v) - xmin) / (xmax - xmin) * (w - 2 * pad);
  const Y = p => pad + (ymax - Math.log10(p)) / (ymax - ymin) * (h - 2 * pad);
  const g = cssVar("--border");
  let s = `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" aria-hidden="true">`;
  s += `<rect x="0.5" y="0.5" width="${w - 1}" height="${h - 1}" fill="none" stroke="${g}" rx="3"/>`;
  s += `<line x1="${X(10)}" x2="${X(10)}" y1="1" y2="${h - 1}" stroke="${g}" stroke-dasharray="1,2"/>`;
  for (const e of [-2, -4]) s += `<line x1="1" x2="${w - 1}" y1="${Y(10 ** e)}" y2="${Y(10 ** e)}" stroke="${g}" stroke-dasharray="1,2"/>`;
  for (const m of metrics) {
    const d = dists && dists[m];
    if (!d || !d.length) continue;
    const tot = d.reduce((a, b) => a + b[1], 0);
    const pts = [];
    let prev = 0;
    for (const [x, c] of d) {
      if (x < 1) continue;
      if (x > 40 || c < SPARK_MINC || c / tot < 1e-5 || (prev && x !== prev + 1)) break;
      pts.push(`${X(x).toFixed(1)},${Y(c / tot).toFixed(1)}`);
      prev = x;
    }
    if (pts.length) s += `<polyline fill="none" stroke="${mcolor(m)}" stroke-width="1.5" stroke-linejoin="round" points="${pts.join(" ")}"/>`;
  }
  return s + "</svg>";
}

/* modal dialog */
function openModal(title, opts = {}) {
  closeModal();
  const bd = document.createElement("div");
  bd.className = "modal-backdrop";
  bd.innerHTML = `<div class="modal" role="dialog" aria-modal="true"><div class="modal-head"><h3>${title}</h3>
    <span class="spacer"></span>${opts.link ? `<a class="btn" href="${opts.link}">${opts.linkText || "open page"} →</a>` : ""}
    <button class="btn modal-close" title="Close (Esc)">✕</button></div><div class="modal-body"></div></div>`;
  bd.addEventListener("click", e => { if (e.target === bd) closeModal(); });
  bd.querySelector(".modal-close").onclick = closeModal;
  document.body.append(bd);
  document.body.style.overflow = "hidden";
  return bd.querySelector(".modal-body");
}
function closeModal() {
  document.querySelectorAll(".modal-backdrop").forEach(e => { if (window.Plotly) e.querySelectorAll(".js-plotly-plot").forEach(p => Plotly.purge(p)); e.remove(); });
  document.body.style.overflow = "";
}
document.addEventListener("keydown", e => { if (e.key === "Escape") closeModal(); });

/* large interactive version of the four distributions of one unit (used by the thumbnails) */
/* the distributions of one unit with fits; used by the thumbnails and the detail pages */
function distTraces(U, view, filter, kind, bin, metrics, fitsRec, fields, opts = {}) {
  const fi = k => fields.indexOf(k);
  const tr = [];
  let N = 0, xmaxAll = 1;
  for (const m of metrics) {
    const d = U.dists[`${view}|${filter}|${kind}|${bin}|${m}`]; if (!d) continue;
    const dd = d.filter(a => a[0] >= 1);
    const tot = dd.reduce((a, b) => a + b[1], 0); N = Math.max(N, tot);
    xmaxAll = Math.max(xmaxAll, ...dd.map(a => a[0]));
    tr.push({ x: dd.map(a => a[0]), y: dd.map(a => a[1] / tot), customdata: dd.map(a => a[1]), mode: "markers",
      name: (opts.prefix || "") + METRICS[m].label,
      marker: { color: opts.color || mcolor(m), size: opts.size || 7, symbol: opts.symbol || "circle",
                opacity: dd.map(a => a[1] < SPARK_MINC ? 0.3 : 0.95) }, legendgroup: (opts.prefix || "") + m, showlegend: opts.showlegend !== false,
      hovertemplate: `${(opts.prefix || "")}${METRICS[m].short} n=%{x}: %{y:.3g} (%{customdata} occurrences)<extra></extra>` });
    const f = fitsRec && fitsRec[m];
    if (f && f[fi("mle_lambda")] !== null && opts.fit !== false) {
      const xmax = Math.max(...dd.map(a => a[0])); const xs = [];
      for (let x = 1; x <= xmax; x += (x < 10 ? 0.25 : 1)) xs.push(x);
      tr.push({ x: xs, y: tplCurve(f[fi("mle_beta")], f[fi("mle_lambda")], xmax, xs), mode: "lines", legendgroup: (opts.prefix || "") + m, showlegend: false,
        line: { color: opts.color || mcolor(m), dash: "dash", width: 1.5 }, name: `λ=${fmt(f[fi("mle_lambda")], 3)}`, hoverinfo: "name" });
    }
  }
  return { tr, N, xmaxAll };
}
const LOGLOG_RANGE = { x: [0, Math.log10(60)], y: [-5.3, 0.15] };   // common scale of distribution plots
async function showDistModal(level, unit, view, filter, kind, bin, fitsRec, fields, metrics = MAIN3) {
  const body = openModal(`${unit.replace(/_/g, " ")} · ${VIEWS[view] || view} · ${FILTERS[filter]} · ${kind === "rnd" ? "random baseline · " : ""}${BINS[bin] || bin}`,
    { link: `unit.html?level=${level}&u=${encodeURIComponent(unit)}&view=${view}&filter=${filter}&bin=${encodeURIComponent(bin)}`, linkText: "detailed page" });
  body.innerHTML = `<div class="plot tall" style="min-height:520px"></div><p class="small muted">Points: relative frequency of each value
    (faded: seen fewer than ${SPARK_MINC} times). Dashed: truncated power-law fit (maximum likelihood). Dotted grey line: one single occurrence (1/N),
    the lowest frequency this sample can show.</p>`;
  const U = await getJSON(`data/unit/${level}__${unit}.json`);
  const { tr, N, xmaxAll } = distTraces(U, view, filter, kind, bin, metrics, fitsRec, fields);
  if (N) tr.push({ x: [1, xmaxAll], y: [1 / N, 1 / N], mode: "lines", line: { color: cssVar("--muted"), dash: "dot", width: 1 },
    name: "1 occurrence", hoverinfo: "name" });
  plotNew(body.querySelector(".plot"), tr, plotLayout({ margin: { l: 76, r: 16, t: 20, b: 46 }, xaxis: { type: "log", title: "n" },
    yaxis: { type: "log", title: "relative frequency", exponentformat: "power", range: [Math.log10(1 / N) - 0.4, 0.2] } }));
}

/* scatter of two quantities with the diagonal and the same scale on both axes */
function scatterDiag(el, xs, ys, names, opts = {}) {
  const all = xs.concat(ys).filter(v => v !== null && v !== undefined && !Number.isNaN(v));
  const lo0 = Math.min(...all), hi0 = Math.max(...all), pad = (hi0 - lo0) * 0.05 || 0.1;
  const lo = opts.zero ? Math.min(0, lo0) : lo0 - pad, hi = hi0 + pad;
  const tr = [{ x: [lo, hi], y: [lo, hi], mode: "lines", line: { color: cssVar("--muted"), dash: "dot", width: 1 }, hoverinfo: "skip", showlegend: false }];
  if (opts.groups) {
    for (const [g, col] of Object.entries(opts.groups)) {
      const ii = names.map((_, i) => i).filter(i => opts.groupOf[i] === g);
      tr.push({ x: ii.map(i => xs[i]), y: ii.map(i => ys[i]), text: ii.map(i => names[i]), mode: "markers", name: g,
        marker: { color: col, size: opts.size || 7, opacity: .85 }, hovertemplate: `%{text}<br>${opts.xlab || "x"} %{x:.3f} · ${opts.ylab || "y"} %{y:.3f}<extra>${g}</extra>` });
    }
  } else {
    tr.push({ x: xs, y: ys, text: names, mode: "markers", showlegend: false,
      marker: { color: opts.colorArr || opts.color || cssVar("--accent"), size: opts.size || 7, opacity: .85,
                colorscale: opts.colorscale, reversescale: opts.reversescale, colorbar: opts.colorbar },
      hovertemplate: `%{text}<br>${opts.xlab || "x"} %{x:.3f} · ${opts.ylab || "y"} %{y:.3f}<extra></extra>` });
  }
  return plotNew(el, tr, plotLayout({ margin: opts.margin || { l: 52, r: 12, t: 10, b: 44 },
    xaxis: { title: opts.xlab || "", range: [lo, hi], constrain: "domain" },
    yaxis: { title: opts.ylab || "", range: [lo, hi], scaleanchor: "x", scaleratio: 1, constrain: "domain" },
    legend: opts.legend || { orientation: "h", y: -0.25 } }));
}

/* "red dots" figure: dependencies x inter-word positions (flux sizes above, lengths below) */
function fluxDotsSVG(forms, heads, opts = {}) {
  const n = forms.length, W = opts.w || 62, X = i => 30 + (i - 1) * W;      // word i at X(i)
  const arcs = [];
  for (let d = 1; d <= n; d++) if (heads[d - 1]) arcs.push([Math.min(d, heads[d - 1]), Math.max(d, heads[d - 1]), d]);
  arcs.sort((a, b) => (a[1] - a[0]) - (b[1] - b[0]));
  const level = {}, H0 = 40;
  const lv = arcs.map(a => { let l = 1; for (const b of arcs) if (b !== a && b[0] >= a[0] && b[1] <= a[1] && (b[1] - b[0]) < (a[1] - a[0])) l = Math.max(l, (level[b] || 1) + 1); level[a] = l; return l; });
  const maxL = Math.max(1, ...lv), top = 26, base = top + 18 + maxL * 16;
  const flux = []; for (let i = 1; i < n; i++) flux.push(arcs.filter(a => a[0] <= i && a[1] > i).length);
  const len = new Array(n).fill(null); for (const a of arcs) len[a[2] - 1] = a[1] - a[0];
  const red = cssVar("--c-weight"), mu = cssVar("--muted"), tx = cssVar("--text");
  let s = `<svg width="${X(n) + 40}" height="${base + 52}" viewBox="0 0 ${X(n) + 40} ${base + 52}" font-family="${cssVar("--sans")}" font-size="12">`;
  for (let i = 1; i < n; i++) {
    const x = (X(i) + X(i + 1)) / 2;
    s += `<line x1="${x}" x2="${x}" y1="${top + 4}" y2="${base + 4}" stroke="${mu}" stroke-dasharray="2,3" stroke-width="0.8"/>`;
    s += `<text x="${x}" y="${top - 6}" text-anchor="middle" fill="${cssVar("--c-flux")}" font-weight="600">${flux[i - 1]}</text>`;
  }
  arcs.forEach((a, k) => {
    const y = base - lv[k] * 16, x1 = X(a[0]), x2 = X(a[1]);
    s += `<path d="M${x1},${base - 2} L${x1},${y} L${x2},${y} L${x2},${base - 2}" fill="none" stroke="${tx}" stroke-width="1.1"/>`;
    const dx = a[2] === a[0] ? x1 : x2;
    s += `<path d="M${dx - 3.5},${base - 8} L${dx},${base - 2} L${dx + 3.5},${base - 8}" fill="none" stroke="${tx}" stroke-width="1.1"/>`;
    for (let i = a[0]; i < a[1]; i++) s += `<circle cx="${(X(i) + X(i + 1)) / 2}" cy="${y}" r="3.6" fill="${red}"/>`;
  });
  forms.forEach((f, i) => {
    s += `<text x="${X(i + 1)}" y="${base + 16}" text-anchor="middle" fill="${tx}">${f}</text>`;
    s += `<text x="${X(i + 1)}" y="${base + 38}" text-anchor="middle" fill="${cssVar("--c-len")}" font-weight="600">${len[i] === null ? "–" : len[i]}</text>`;
  });
  s += `<text x="2" y="${top - 6}" fill="${cssVar("--c-flux")}" font-size="10">flux</text><text x="2" y="${base + 38}" fill="${cssVar("--c-len")}" font-size="10">length</text>`;
  return s + "</svg>";
}

/* Botalla's matrix: rows = left ends, columns = right ends, cells = dependencies (+length) */
function matrixHTML(words, arcs) {
  // arcs: [dep, gov, rel, length] (1-based positions)
  const L = [...new Set(arcs.map(a => Math.min(a[0], a[1])))].sort((a, b) => a - b);
  const R = [...new Set(arcs.map(a => Math.max(a[0], a[1])))].sort((a, b) => a - b);
  let h = `<table class="data matrix"><thead><tr><th class="nosort"></th>${R.map(r => `<th class="nosort">${words[r - 1]}<span class="sub">${r}</span></th>`).join("")}</tr></thead><tbody>`;
  for (const l of L) {
    h += `<tr><th class="nosort l">${words[l - 1]}<span class="sub">${l}</span></th>`;
    for (const r of R) {
      const a = arcs.filter(x => Math.min(x[0], x[1]) === l && Math.max(x[0], x[1]) === r);
      h += `<td>${a.map(x => `${x[1] === l ? "" : "←"}${x[2]}${x[1] === l ? "→" : ""} <span class="muted">+${x[3]}</span>`).join("<br>")}</td>`;
    }
    h += "</tr>";
  }
  return h + "</tbody></table>";
}

/* every Plotly chart inside a .card gets an "enlarge" button that re-draws it in a modal */
function addEnlarge(el) {
  const card = el.closest(".card");
  if (!card || card.querySelector(".enlarge")) return;
  const b = document.createElement("button");
  b.className = "btn enlarge"; b.title = "Enlarge"; b.textContent = "⤢";
  b.onclick = () => {
    const t = (card.querySelector("h3") || {}).textContent || "";
    const body = openModal(t);
    const div = document.createElement("div"); div.className = "plot"; div.style.minHeight = "72vh";
    body.append(div);
    const layout = JSON.parse(JSON.stringify(el.layout)); delete layout.width; delete layout.height;
    plotNew(div, JSON.parse(JSON.stringify(el.data)), layout);
  };
  card.style.position = "relative";
  card.append(b);
}

/* dependency tree with inter-word values, rendered by DependencyTreeJS */
function drawTree(container, ex, rows = ["flux", "weight", "pot"]) {
  const div = document.createElement("div");
  div.className = "tree";
  const cap = document.createElement("div");
  cap.className = "cap";
  cap.innerHTML = `${ex.fw ? ex.fw + "_" : ""}${ex.treebank || ""} · <span class="mono">${ex.sent_id || ""}</span> · ${ex.caption || ""}`;
  div.append(cap);
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  div.append(svg);
  container.append(div);
  try {
    const dt = window.dependencytreejs;
    const rs = new dt.ReactiveSentence();
    rs.fromSentenceConll("# text = " + (ex.text || "") + "\n" + ex.conll);
    const opts = dt.defaultSentenceSVGOptions();
    opts.shownFeatures = ["FORM", "UPOS"];
    opts.interactive = false;
    if (document.documentElement.getAttribute("data-theme") === "dark" ||
        (!document.documentElement.getAttribute("data-theme") && matchMedia("(prefers-color-scheme: dark)").matches)) {
      try { dt.setThemeMode("DARK"); } catch (e) {}
    }
    const ss = new dt.SentenceSVG(svg, rs, opts);
    const toks = ss.tokenSVGs;
    const H0 = ss.totalHeight || svg.getBBox().height;
    const ns = "http://www.w3.org/2000/svg";
    const g = document.createElementNS(ns, "g");
    const yStart = H0 + 14;
    rows.forEach((m, r) => {
      const vals = ex.values[m];
      if (!vals) return;
      const y = yStart + r * 18;
      const lab = document.createElementNS(ns, "text");
      lab.setAttribute("x", 2); lab.setAttribute("y", y);
      lab.setAttribute("font-size", "11"); lab.setAttribute("fill", mcolor(m.trim()));
      lab.textContent = METRICS[m.trim()] ? METRICS[m.trim()].short + (m !== m.trim() ? " (micro)" : "") : m;
      g.append(lab);
      for (let i = 0; i < vals.length && i + 1 < toks.length; i++) {
        const x = (toks[i].centerX + toks[i + 1].centerX) / 2;
        const t = document.createElementNS(ns, "text");
        t.setAttribute("x", x); t.setAttribute("y", y); t.setAttribute("text-anchor", "middle");
        t.setAttribute("font-size", "12"); t.setAttribute("font-weight", "600"); t.setAttribute("fill", mcolor(m.trim()));
        t.textContent = vals[i];
        g.append(t);
        if (r === 0) {
          const ln = document.createElementNS(ns, "line");
          ln.setAttribute("x1", x); ln.setAttribute("x2", x); ln.setAttribute("y1", H0 - 30); ln.setAttribute("y2", H0 + 2);
          ln.setAttribute("stroke", cssVar("--border")); ln.setAttribute("stroke-dasharray", "2,3");
          g.append(ln);
        }
      }
    });
    svg.append(g);
    const W = Math.max(ss.totalWidth || 0, svg.getBBox().width + 10);
    const H = yStart + rows.length * 18;
    svg.setAttribute("width", W); svg.setAttribute("height", H);
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  } catch (e) {
    div.append(Object.assign(document.createElement("pre"), { textContent: "tree rendering failed: " + e + "\n" + ex.conll }));
  }
  return div;
}

function legendHTML(metrics) {
  return `<div class="legend">${metrics.map(m => `<span style="--c:${mcolor(m)}">${METRICS[m].label}</span>`).join("")}</div>`;
}

/* Plotly.newPlot with an explicit width taken from the container (grid cells are not
   always measured correctly by Plotly's autosize), and a resize on window changes. */
function plotNew(el, data, layout, conf = PCONF) {
  const e = typeof el === "string" ? document.getElementById(el) : el;
  // deferred, so that all cards of a grid exist before widths are measured
  return new Promise(res => setTimeout(() => {
    const w = e.getBoundingClientRect().width;
    if (w > 50) layout.width = Math.floor(w);
    // clip the y range of log plots to the observed points (fitted curves go far below)
    if (layout.yaxis && layout.yaxis.type === "log" && !layout.yaxis.range) {
      const obs = data.filter(t => (t.mode || "").includes("markers")).flatMap(t => t.y || []).filter(v => v > 0);
      if (obs.length) layout.yaxis.range = [Math.log10(Math.min(...obs)) - 0.6, Math.log10(Math.max(...obs)) + 0.3];
    }
    res(Plotly.newPlot(e, data, layout, conf).then(p => { if (!e.closest(".modal")) addEnlarge(e); return p; }));
  }, 0));
}
window.addEventListener("resize", () => {
  clearTimeout(window._rsz);
  window._rsz = setTimeout(() => document.querySelectorAll(".js-plotly-plot").forEach(e => {
    const w = e.parentElement.getBoundingClientRect().width;
    if (w > 50) Plotly.relayout(e, { width: Math.floor(w) - 2 });
  }), 200);
});
