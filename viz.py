"""
viz.py — render a Pipeline as a self-contained, read-only HTML DAG view.

Domain-agnostic (like core): takes any Pipeline, calls .to_graph(), emits one
standalone .html with inline CSS/JS — no external deps, opens via file://.

    from viz import write_html
    write_html(pipeline, "pipeline_view.html")

Layout: columns by layer (left->right), AWS-Step-Functions style cards showing
each stage's IN/OUT files. Curved arrows are producer->consumer; edges that skip
a layer (an output handed to a non-adjacent stage) are dashed amber + labeled.
"""
from __future__ import annotations

import json
from pathlib import Path

_TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__NAME__ · pipeline</title>
<style>
* { box-sizing: border-box; }
body { margin:0; font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
       background:#0d1117; color:#e6edf3; }
.header { padding:16px 20px; border-bottom:1px solid #21262d; display:flex;
          align-items:baseline; gap:16px; flex-wrap:wrap; }
.header h1 { font-size:15px; margin:0; font-weight:600; letter-spacing:.3px; }
.header .sub { color:#7d8590; font-size:12px; }
.legend { margin-left:auto; display:flex; gap:16px; font-size:11px; color:#7d8590; }
.legend .k { display:inline-flex; align-items:center; gap:6px; }
.dot { width:9px; height:9px; border-radius:2px; display:inline-block; }
.line { width:16px; height:0; border-top:2px solid #4b5563; display:inline-block; }
.line.skip { border-top:2px dashed #d29922; }
.scroll { overflow-x:auto; padding:30px 22px; }
.graph { position:relative; display:flex; gap:70px; min-width:min-content;
         align-items:flex-start; }
svg.edges { position:absolute; inset:0; pointer-events:none; overflow:visible; }
.col { display:flex; flex-direction:column; gap:26px; position:relative; z-index:1; }
.node { background:#161b22; border:1px solid #30363d; border-left:3px solid #388bfd;
        border-radius:8px; width:212px; box-shadow:0 1px 2px rgba(0,0,0,.5); }
.node.native { border-left-color:#3fb950; }
.nhead { padding:9px 11px; border-bottom:1px solid #21262d; display:flex;
         align-items:center; justify-content:space-between; }
.nname { font-size:12.5px; font-weight:600; }
.ndesc { padding:8px 11px 9px; font-size:10.5px; color:#8b949e; line-height:1.45;
         border-bottom:1px solid #21262d; white-space:normal; }
.badge { font-size:9px; text-transform:uppercase; letter-spacing:.5px;
         padding:2px 6px; border-radius:10px; color:#7d8590; border:1px solid #30363d; }
.badge.native { color:#3fb950; border-color:#238636; }
.sect { padding:8px 11px; }
.lbl { font-size:9px; color:#6e7681; letter-spacing:.6px; margin-bottom:5px; }
.chip { display:block; font-size:11px; padding:3px 7px; margin:3px 0; background:#0d1117;
        border:1px solid #21262d; border-radius:5px; color:#c9d1d9;
        white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.chip.ext { border-style:dashed; color:#8b949e; }
.chip.out { color:#a5d6ff; }
path.edge { fill:none; stroke:#4b5563; stroke-width:1.6; }
path.edge.skip { stroke:#d29922; stroke-dasharray:5 4; stroke-width:1.8; }
text.elabel { fill:#d29922; font-size:9.5px; font-family:ui-monospace,Menlo,monospace; }
</style></head>
<body>
<div class="header">
  <h1>__NAME__</h1>
  <span class="sub">read-only pipeline view</span>
  <div class="legend">
    <span class="k"><span class="dot" style="background:#3fb950"></span>native (ours)</span>
    <span class="k"><span class="dot" style="background:#388bfd"></span>adapter (wraps tool)</span>
    <span class="k"><span class="line"></span>dependency</span>
    <span class="k"><span class="line skip"></span>skips a stage</span>
  </div>
</div>
<div class="scroll"><div class="graph" id="graph">
  <svg class="edges" id="edges"><defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" fill="#6b7280"/></marker>
    <marker id="arrowskip" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" fill="#d29922"/></marker>
  </defs></svg>
</div></div>
<script>
const GRAPH = __GRAPH__;
const graphEl = document.getElementById('graph');
const svg = document.getElementById('edges');
const SVGNS = 'http://www.w3.org/2000/svg';

const layers = {};
GRAPH.nodes.forEach(n => { (layers[n.layer] = layers[n.layer] || []).push(n); });
Object.keys(layers).map(Number).sort((a,b)=>a-b).forEach(L => {
  const col = document.createElement('div'); col.className = 'col';
  layers[L].forEach(n => col.appendChild(card(n)));
  graphEl.appendChild(col);
});

function card(n){
  const d = document.createElement('div');
  d.className = 'node' + (n.kind === 'native' ? ' native' : '');
  d.dataset.id = n.id;
  const kind = n.kind === 'native' ? 'native' : 'adapter';
  const ins = n.inputs.map(i => `<span class="chip${i.external?' ext':''}">${i.name}</span>`).join('') || '<span class="chip ext">—</span>';
  const outs = n.outputs.map(o => `<span class="chip out">${o}</span>`).join('') || '<span class="chip">—</span>';
  d.innerHTML =
    `<div class="nhead"><span class="nname">${n.id}</span><span class="badge${n.kind==='native'?' native':''}">${kind}</span></div>`
    + (n.description ? `<div class="ndesc">${n.description}</div>` : '')
    + `<div class="sect"><div class="lbl">IN</div>${ins}</div>`
    + `<div class="sect"><div class="lbl">OUT</div>${outs}</div>`;
  return d;
}

function draw(){
  [...svg.querySelectorAll('path,text')].forEach(el => el.remove());
  svg.setAttribute('width', graphEl.scrollWidth);
  svg.setAttribute('height', graphEl.scrollHeight);
  const g = graphEl.getBoundingClientRect();
  GRAPH.edges.forEach(e => {
    const s = graphEl.querySelector(`[data-id="${e.src}"]`);
    const t = graphEl.querySelector(`[data-id="${e.dst}"]`);
    if(!s || !t) return;
    const sr = s.getBoundingClientRect(), tr = t.getBoundingClientRect();
    const x1 = sr.right - g.left, y1 = sr.top - g.top + sr.height/2;
    const x2 = tr.left  - g.left, y2 = tr.top - g.top + tr.height/2;
    const dx = Math.max(34, (x2 - x1) / 2);
    const p = document.createElementNS(SVGNS, 'path');
    p.setAttribute('d', `M${x1},${y1} C${x1+dx},${y1} ${x2-dx},${y2} ${x2},${y2}`);
    p.setAttribute('class', 'edge' + (e.skip ? ' skip' : ''));
    p.setAttribute('marker-end', e.skip ? 'url(#arrowskip)' : 'url(#arrow)');
    const title = document.createElementNS(SVGNS, 'title');
    title.textContent = e.file + (e.skip ? '  (skips a stage)' : '');
    p.appendChild(title);
    svg.appendChild(p);
    if(e.skip){
      const tx = document.createElementNS(SVGNS, 'text');
      tx.setAttribute('class', 'elabel');
      tx.setAttribute('x', (x1 + x2) / 2); tx.setAttribute('y', Math.min(y1, y2) - 6);
      tx.setAttribute('text-anchor', 'middle');
      tx.textContent = e.file;
      svg.appendChild(tx);
    }
  });
}
draw();
window.addEventListener('resize', draw);
</script>
</body></html>
"""


def render_html(graph: dict) -> str:
    """Return a full standalone HTML document for a Pipeline.to_graph() dict."""
    return (_TEMPLATE
            .replace("__GRAPH__", json.dumps(graph))
            .replace("__NAME__", str(graph.get("name", "pipeline"))))


def write_html(pipeline, path) -> Path:
    """Render `pipeline` to a standalone HTML file. Returns the path."""
    path = Path(path)
    path.write_text(render_html(pipeline.to_graph()))
    return path
