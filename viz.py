"""
viz.py — render a Pipeline as a self-contained, INTERACTIVE HTML view.

Domain-agnostic (like core): takes any Pipeline, calls .to_graph(), and emits one
standalone .html with inline CSS/JS — no external deps, opens via file://.

    from viz import write_html
    write_html(pipeline, "pipeline_view.html")

Everything shown is *derived from the abstraction*, not hand-authored:
  - flow order + edges   from the DAG (stage sequence, wraps to the next row;
                         producer->consumer edges, dashed when they skip a stage)
  - kind + description   from the Stage class
  - active strategy +    from the core.Strategy seam (auto: which impl is plugged in
    its alternatives       + every other concrete impl, with their docstrings)
  - live self_test dot   from Stage.test_status() (run at render time)
  - docs drawer          from the Stage class docstring + the stage's README.md

Click a stage for the detail drawer; hover to trace its dependencies; click an
I/O file chip for a per-file explainer (what it is / how it's made / who produces
+ consumes it — the last two derived from the graph, the prose from an optional
domain `file_docs` map). Because it all comes from the graph, adding a stage or
swapping a strategy updates the view with no edits here.
"""
from __future__ import annotations

import importlib
import inspect
import json
import pkgutil
from pathlib import Path


def _eager_import_approaches(pipeline) -> None:
    """Import every submodule of each stage's package so `Strategy.__subclasses__`
    sees ALL alternatives (not just the default that got imported on construction).
    Best-effort and side-effect-only: a broken/heavy submodule is skipped."""
    seen: set[str] = set()
    for st in pipeline.stages:
        pkg_name = type(st).__module__.rsplit(".", 1)[0]  # the stage package
        if pkg_name in seen:
            continue
        seen.add(pkg_name)
        pkg = importlib.import_module(pkg_name)
        if not hasattr(pkg, "__path__"):
            continue
        for info in pkgutil.walk_packages(pkg.__path__, prefix=pkg_name + "."):
            if info.name not in seen:
                seen.add(info.name)
                try:
                    importlib.import_module(info.name)
                except Exception:  # noqa: BLE001 — a bad submodule shouldn't break the view
                    pass


def _stage_readme(st) -> str:
    """The README.md sitting next to a stage's module, if any (auto-doc source)."""
    try:
        readme = Path(inspect.getfile(type(st))).parent / "README.md"
        return readme.read_text() if readme.exists() else ""
    except (OSError, TypeError):
        return ""


def _enrich(graph: dict, pipeline, run_self_tests: bool) -> dict:
    """Fold per-stage README + live test status into the graph nodes."""
    by_name = {st.name: st for st in pipeline.stages}
    for node in graph["nodes"]:
        st = by_name.get(node["id"])
        if st is None:
            continue
        node["readme"] = _stage_readme(st)
        if run_self_tests:
            status, detail = st.test_status()
            node["test"] = {"status": status, "detail": detail or ""}
        else:
            node["test"] = {"status": "unknown", "detail": ""}
    return graph


_TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__NAME__ · pipeline</title>
<style>
:root{
  --bg:#0d1117; --panel:#161b22; --panel2:#0d1117; --line:#21262d; --line2:#30363d;
  --fg:#e6edf3; --mut:#8b949e; --mut2:#6e7681;
  --native:#3fb950; --adapter:#388bfd; --skip:#d29922;
  --pass:#3fb950; --fail:#f85149; --notest:#6e7681;
}
*{box-sizing:border-box}
html,body{height:100%}
body{margin:0;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;background:var(--bg);color:var(--fg)}
a{color:#58a6ff}
.header{padding:14px 20px;border-bottom:1px solid var(--line);display:flex;align-items:baseline;gap:16px;flex-wrap:wrap}
.header h1{font-size:15px;margin:0;font-weight:600;letter-spacing:.3px}
.header .sub{color:var(--mut);font-size:12px}
.toolbar{margin-left:auto;display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.btn{font:inherit;font-size:11px;color:var(--mut);background:var(--panel);border:1px solid var(--line2);
     border-radius:6px;padding:4px 9px;cursor:pointer}
.btn:hover{color:var(--fg);border-color:#484f58}
.btn.on{color:var(--fg);border-color:#484f58;background:#1f2630}
.legend{display:flex;gap:14px;font-size:11px;color:var(--mut);align-items:center}
.legend .k{display:inline-flex;align-items:center;gap:6px}
.dot{width:9px;height:9px;border-radius:2px;display:inline-block}
.line{width:16px;height:0;border-top:2px solid #4b5563;display:inline-block}
.line.skip{border-top:2px dashed var(--skip)}
.scroll{padding:30px 26px 90px}
.graph{position:relative;display:grid;grid-template-columns:repeat(auto-fill,220px);
       gap:52px 66px;align-items:start;justify-content:start}
svg.edges{position:absolute;inset:0;pointer-events:none;overflow:visible;z-index:0}
.node{background:var(--panel);border:1px solid var(--line2);border-left:3px solid var(--adapter);
      border-radius:8px;width:220px;box-shadow:0 1px 2px rgba(0,0,0,.5);cursor:pointer;
      transition:border-color .12s,box-shadow .12s,opacity .12s;position:relative;z-index:1}
.node.native{border-left-color:var(--native)}
.node:hover{border-color:#484f58}
.node.sel{border-color:#58a6ff;box-shadow:0 0 0 1px #58a6ff,0 2px 10px rgba(0,0,0,.6)}
.node.dim{opacity:.28}
.nhead{padding:9px 11px;border-bottom:1px solid var(--line);display:flex;align-items:center;gap:8px}
.nname{font-size:12.5px;font-weight:600;flex:1}
.tstat{font-size:11px;line-height:1}
.tstat.pass{color:var(--pass)} .tstat.fail{color:var(--fail)} .tstat.notest{color:var(--notest)}
.nsub{padding:6px 11px;font-size:10px;color:var(--mut);border-bottom:1px solid var(--line);
      display:flex;gap:6px;align-items:center;flex-wrap:wrap}
.kbadge{text-transform:uppercase;letter-spacing:.5px;font-size:9px;padding:1px 6px;border-radius:10px;
        border:1px solid var(--line2);color:var(--mut)}
.kbadge.native{color:var(--native);border-color:#238636}
.kbadge.adapter{color:var(--adapter);border-color:#1f6feb}
.strat{color:#d2a8ff}
.ndesc{padding:8px 11px 9px;font-size:10.5px;color:var(--mut);line-height:1.45;border-bottom:1px solid var(--line)}
.sect{padding:7px 11px}
.lbl{font-size:9px;color:var(--mut2);letter-spacing:.6px;margin-bottom:5px}
.chip{display:block;font-size:11px;padding:3px 7px;margin:3px 0;background:var(--panel2);
      border:1px solid var(--line);border-radius:5px;color:#c9d1d9;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.chip.ext{border-style:dashed;color:var(--mut)}
.chip.out{color:#a5d6ff}
.chip.has-doc{cursor:pointer;border-left:2px solid #2f4a63}
.chip.has-doc:hover{border-color:#58a6ff;color:#fff}
.nfoot{padding:6px 11px;font-size:10px;color:var(--mut2);border-top:1px solid var(--line)}
path.edge{fill:none;stroke:#4b5563;stroke-width:1.6}
path.edge.skip{stroke:var(--skip);stroke-dasharray:5 4;stroke-width:1.8}
path.edge.hot{stroke:#58a6ff;stroke-width:2.6}
path.edge.hot.skip{stroke:#e3b341}
path.edge.fade{opacity:.12}
text.elabel{fill:var(--skip);font-size:9.5px;font-family:ui-monospace,Menlo,monospace}
/* drawer */
.scrim{position:fixed;inset:0;background:rgba(1,4,9,.55);opacity:0;pointer-events:none;transition:opacity .16s;z-index:5}
.scrim.show{opacity:1;pointer-events:auto}
.drawer{position:fixed;top:0;right:0;height:100%;width:min(560px,94vw);background:var(--panel);
        border-left:1px solid var(--line2);transform:translateX(100%);transition:transform .18s ease;
        z-index:6;display:flex;flex-direction:column}
.drawer.show{transform:none}
.dhead{padding:16px 20px;border-bottom:1px solid var(--line);display:flex;align-items:center;gap:12px}
.dhead h2{margin:0;font-size:15px}
.dclose{margin-left:auto;background:none;border:none;color:var(--mut);font-size:20px;cursor:pointer;line-height:1}
.dbody{overflow-y:auto;padding:18px 20px 60px}
.dsec{margin-bottom:22px}
.dsec h3{font-size:10px;letter-spacing:.7px;text-transform:uppercase;color:var(--mut2);margin:0 0 9px;font-weight:600}
.pill{display:inline-flex;align-items:center;gap:6px;font-size:11px;padding:3px 9px;border-radius:12px;
      border:1px solid var(--line2);color:var(--mut);margin:0 6px 6px 0}
.pill.pass{color:var(--pass);border-color:#238636} .pill.fail{color:var(--fail);border-color:#8b2c2c}
.opt{border:1px solid var(--line);border-radius:7px;padding:10px 12px;margin-bottom:8px;background:var(--panel2)}
.opt.active{border-color:#8957e5;box-shadow:0 0 0 1px rgba(137,87,229,.4)}
.opt .ohead{display:flex;align-items:center;gap:8px;font-size:12px}
.opt .oname{font-weight:600;color:#d2a8ff}
.opt .otag{font-size:9px;text-transform:uppercase;letter-spacing:.5px;padding:1px 6px;border-radius:10px}
.opt.active .otag{color:var(--native);border:1px solid #238636}
.opt .otag.alt{color:var(--mut);border:1px solid var(--line2)}
/* prose, not code: let it reflow instead of honouring the docstring's source wrapping */
.opt .odoc{font-size:11px;color:var(--mut);line-height:1.5;margin-top:7px;white-space:normal}
.flow{display:flex;flex-wrap:wrap;gap:6px}
.nav{font-size:11px;padding:3px 9px;border:1px solid var(--line2);border-radius:6px;color:#c9d1d9;
     background:var(--panel2);cursor:pointer}
.nav:hover{border-color:#58a6ff;color:#fff}
.md{font-size:12px;line-height:1.6;color:#c9d1d9}
.md h1,.md h2,.md h3,.md h4{color:var(--fg);margin:16px 0 8px;line-height:1.3}
.md h1{font-size:15px} .md h2{font-size:13.5px} .md h3{font-size:12.5px} .md h4{font-size:12px}
.md p{margin:8px 0}
.md code{background:#0b0f14;border:1px solid var(--line);border-radius:4px;padding:1px 5px;font-size:11px}
.md pre{background:#0b0f14;border:1px solid var(--line);border-radius:6px;padding:10px 12px;overflow-x:auto}
.md pre code{background:none;border:none;padding:0}
.md ul{margin:8px 0;padding-left:20px} .md li{margin:3px 0}
.md blockquote{border-left:3px solid var(--line2);margin:8px 0;padding:2px 12px;color:var(--mut)}
.md table{border-collapse:collapse;margin:10px 0;font-size:11px;display:block;overflow-x:auto}
.md th,.md td{border:1px solid var(--line2);padding:5px 9px;text-align:left}
.md th{background:#161b22}
.md hr{border:none;border-top:1px solid var(--line);margin:14px 0}
.empty{color:var(--mut2);font-size:11px;font-style:italic}
/* file popover */
.fpop{position:fixed;z-index:8;width:344px;max-width:92vw;background:var(--panel);
      border:1px solid var(--line2);border-radius:10px;box-shadow:0 10px 34px rgba(1,4,9,.72);
      display:none}
.fpop.show{display:block}
.fpop .fclose{position:absolute;top:7px;right:10px;background:none;border:none;color:var(--mut);
      font-size:18px;cursor:pointer;line-height:1}
.fpop .fhead{padding:13px 34px 11px 14px;border-bottom:1px solid var(--line)}
.fpop .ftitle{font-size:13px;font-weight:600;color:var(--fg)}
.fpop .fname{font-family:ui-monospace,Menlo,monospace;font-size:10.5px;color:#a5d6ff;margin-top:3px;word-break:break-all}
.fpop .fbadges{display:flex;flex-wrap:wrap;gap:6px;padding:11px 14px 0}
.fpop .fbadge{font-size:9.5px;padding:2px 7px;border-radius:10px;border:1px solid var(--line2);color:var(--mut)}
.fpop .fbadge.fmt{color:#d2a8ff;border-color:#3a2d52}
.fpop .fbody{padding:6px 14px 14px}
.fpop .frow{margin:11px 0 0}
.fpop .flbl{font-size:9px;letter-spacing:.6px;text-transform:uppercase;color:var(--mut2);margin-bottom:4px}
.fpop .ftxt{font-size:12px;color:#c9d1d9;line-height:1.55}
.fpop .fnav{display:flex;gap:6px;flex-wrap:wrap}
</style></head>
<body>
<div class="header">
  <h1>__NAME__</h1>
  <span class="sub">interactive pipeline view · click a stage</span>
  <div class="toolbar">
    <div class="legend">
      <span class="k"><span class="dot" style="background:var(--native)"></span>native</span>
      <span class="k"><span class="dot" style="background:var(--adapter)"></span>adapter</span>
      <span class="k"><span class="line"></span>dep</span>
      <span class="k"><span class="line skip"></span>skip</span>
    </div>
    <button class="btn on" data-filter="all">all</button>
    <button class="btn" data-filter="native">native</button>
    <button class="btn" data-filter="adapter">adapter</button>
  </div>
</div>
<div class="scroll"><div class="graph" id="graph">
  <svg class="edges" id="edges"><defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" fill="#6b7280"/></marker>
    <marker id="arrowhot" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" fill="#58a6ff"/></marker>
    <marker id="arrowskip" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" fill="#d29922"/></marker>
  </defs></svg>
</div></div>

<div class="scrim" id="scrim"></div>
<aside class="drawer" id="drawer" aria-hidden="true">
  <div class="dhead"><h2 id="dtitle"></h2><button class="dclose" id="dclose">&times;</button></div>
  <div class="dbody" id="dbody"></div>
</aside>
<div class="fpop" id="fpop"></div>

<script>
const GRAPH = __GRAPH__;
const NODES = Object.fromEntries(GRAPH.nodes.map(n => [n.id, n]));
const FILE_DOCS = GRAPH.file_docs || {};
const graphEl = document.getElementById('graph');

/* ---------- files: who makes/consumes a file (from the graph) + doc chip ---------- */
function fileProducer(name){ return GRAPH.nodes.find(n => n.outputs.includes(name)); }
function fileConsumers(name){ return GRAPH.nodes.filter(n => n.inputs.some(i => i.name === name)); }
function fileChip(name, cls){
  const has = !!FILE_DOCS[name];
  return `<span class="chip ${cls}${has?' has-doc':''}" data-file="${esc(name)}"`
       + `${has?' title="click: what is this file?"':''}>${esc(name)}</span>`;
}
function wireFileChips(root){
  root.querySelectorAll('.chip.has-doc[data-file]').forEach(ch =>
    ch.addEventListener('click', e => { e.stopPropagation(); openFilePop(ch.dataset.file, ch); }));
}
const svg = document.getElementById('edges');
const SVGNS = 'http://www.w3.org/2000/svg';

/* ---------- lay out in stage-number reading order (wraps to next row) ---------- */
const seqKey = id => { const m = id.match(/^(\d+)([a-z]?)/); return m ? [+m[1], m[2]||''] : [999, id]; };
[...GRAPH.nodes]
  .sort((a,b) => { const ka=seqKey(a.id), kb=seqKey(b.id);
                   return ka[0]-kb[0] || (ka[1]<kb[1]?-1:ka[1]>kb[1]?1:0); })
  .forEach(n => graphEl.appendChild(card(n)));

function esc(s){ return (s||'').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }

function card(n){
  const d = document.createElement('div');
  d.className = 'node ' + (n.kind === 'native' ? 'native' : 'adapter');
  d.dataset.id = n.id;
  const t = n.test || {status:'unknown'};
  const tcls = t.status==='pass'?'pass':(t.status==='fail'?'fail':'notest');
  const tsym = t.status==='pass'?'●':(t.status==='fail'?'●':'○');
  const active = (n.strategies[0]||{}).active;
  const ins = n.inputs.map(i=>fileChip(i.name, i.external?'ext':'')).join('')
    || '<span class="chip ext" title="root stage: no upstream file input">root · no file input</span>';
  const outs = n.outputs.map(o=>fileChip(o,'out')).join('') || '<span class="chip">—</span>';
  const nopt = (n.strategies[0]||{options:[]}).options.length;
  d.innerHTML =
    `<div class="nhead"><span class="nname">${esc(n.id)}</span>`
      + `<span class="tstat ${tcls}" title="self_test: ${esc(t.status)}${t.detail?' — '+esc(t.detail):''}">${tsym}</span></div>`
    + `<div class="nsub"><span class="kbadge ${n.kind}">${esc(n.kind)}</span>`
      + (active?`<span class="strat">${esc(active)}</span>`:'') + `</div>`
    + (n.description?`<div class="ndesc">${esc(n.description)}</div>`:'')
    + `<div class="sect"><div class="lbl">IN</div>${ins}</div>`
    + `<div class="sect"><div class="lbl">OUT</div>${outs}</div>`
    + (nopt>1?`<div class="nfoot">⚙ ${nopt} interchangeable options</div>`:'');
  d.addEventListener('click', e => { e.stopPropagation(); select(n.id); });
  d.addEventListener('mouseenter', () => { if(!selected) highlight(n.id); });
  d.addEventListener('mouseleave', () => { if(!selected) highlight(null); });
  wireFileChips(d);  // clicking a file chip opens its popover, not the stage drawer
  return d;
}

/* ---------- edges ---------- */
function draw(){
  [...svg.querySelectorAll('path,text')].forEach(el => el.remove());
  svg.setAttribute('width', graphEl.scrollWidth);
  svg.setAttribute('height', graphEl.scrollHeight);
  const g = graphEl.getBoundingClientRect();
  GRAPH.edges.forEach((e,i) => {
    const s = graphEl.querySelector(`[data-id="${e.src}"]`);
    const t = graphEl.querySelector(`[data-id="${e.dst}"]`);
    if(!s||!t||s.offsetParent===null||t.offsetParent===null) return;  // skip hidden (filtered) nodes
    const sr=s.getBoundingClientRect(), tr=t.getBoundingClientRect();
    // forward = consumer starts at/after the producer ends -> horizontal curve;
    // otherwise the consumer wrapped to a later row -> exit the bottom, enter the top.
    const forward = tr.left >= sr.right - 4;
    let x1,y1,x2,y2,c1x,c1y,c2x,c2y;
    if(forward){
      x1=sr.right-g.left; y1=sr.top-g.top+sr.height/2;
      x2=tr.left-g.left;  y2=tr.top-g.top+tr.height/2;
      const dx=Math.max(34,(x2-x1)/2);
      c1x=x1+dx; c1y=y1; c2x=x2-dx; c2y=y2;
    } else {
      x1=sr.left-g.left+sr.width/2; y1=sr.bottom-g.top;
      x2=tr.left-g.left+tr.width/2; y2=tr.top-g.top;
      const dy=Math.max(30,(y2-y1)/2);
      c1x=x1; c1y=y1+dy; c2x=x2; c2y=y2-dy;
    }
    const p=document.createElementNS(SVGNS,'path');
    p.setAttribute('d',`M${x1},${y1} C${c1x},${c1y} ${c2x},${c2y} ${x2},${y2}`);
    p.setAttribute('class','edge'+(e.skip?' skip':''));
    p.setAttribute('marker-end', e.skip?'url(#arrowskip)':'url(#arrow)');
    p.dataset.src=e.src; p.dataset.dst=e.dst; p.dataset.skip=e.skip?1:'';
    const title=document.createElementNS(SVGNS,'title');
    title.textContent=e.file+(e.skip?'  (skips a stage)':''); p.appendChild(title);
    svg.appendChild(p);
    if(e.skip){
      const tx=document.createElementNS(SVGNS,'text');
      tx.setAttribute('class','elabel'); tx.setAttribute('x',(x1+x2)/2);
      tx.setAttribute('y',Math.min(y1,y2)-6); tx.setAttribute('text-anchor','middle');
      tx.textContent=e.file; svg.appendChild(tx);
    }
  });
}

/* ---------- highlight dependency neighbourhood ---------- */
function neighbours(id){
  const up=new Set(), down=new Set();
  GRAPH.edges.forEach(e=>{ if(e.dst===id) up.add(e.src); if(e.src===id) down.add(e.dst); });
  return {up,down};
}
function highlight(id){
  const paths=[...svg.querySelectorAll('path.edge')];
  if(!id){
    document.querySelectorAll('.node').forEach(n=>n.classList.remove('dim','sel'));
    paths.forEach(p=>p.classList.remove('hot','fade'));
    if(selected) document.querySelector(`[data-id="${selected}"]`)?.classList.add('sel');
    return;
  }
  const {up,down}=neighbours(id);
  const keep=new Set([id,...up,...down]);
  document.querySelectorAll('.node').forEach(n=>{
    n.classList.toggle('dim', !keep.has(n.dataset.id));
    n.classList.toggle('sel', n.dataset.id===id);
  });
  paths.forEach(p=>{
    const hot=(p.dataset.src===id||p.dataset.dst===id);
    p.classList.toggle('hot',hot);
    p.classList.toggle('fade',!hot);
    p.setAttribute('marker-end', hot?'url(#arrowhot)':(p.dataset.skip?'url(#arrowskip)':'url(#arrow)'));
  });
}

/* ---------- drawer ---------- */
let selected=null;
const scrim=document.getElementById('scrim'), drawer=document.getElementById('drawer');
function closeDrawer(){ selected=null; drawer.classList.remove('show'); scrim.classList.remove('show');
  drawer.setAttribute('aria-hidden','true'); highlight(null); }
document.getElementById('dclose').addEventListener('click',closeDrawer);
scrim.addEventListener('click',closeDrawer);
document.addEventListener('keydown',e=>{ if(e.key==='Escape'){ closeFilePop(); closeDrawer(); } });

function select(id){
  selected=id; highlight(id);
  const n=NODES[id]; const {up,down}=neighbours(id);
  document.getElementById('dtitle').innerHTML =
    `${esc(id)} <span class="kbadge ${n.kind}" style="vertical-align:middle">${esc(n.kind)}</span>`;
  const t=n.test||{status:'unknown'};
  const runs = n.kind==='native'
     ? 'runs here — our own logic'
     : 'adapter — tool execution deferred to Colab';
  let h='';
  h += `<div class="dsec">`
     + `<span class="pill ${t.status==='pass'?'pass':(t.status==='fail'?'fail':'')}">self_test: ${esc(t.status)}</span>`
     + `<span class="pill">${esc(runs)}</span>`
     + `<span class="pill">layer ${n.layer}</span></div>`;
  if(n.description) h+=`<div class="dsec"><div class="md"><p>${esc(n.description)}</p></div></div>`;

  /* strategy seam */
  n.strategies.forEach(s=>{
    h+=`<div class="dsec"><h3>seam · ${esc(s.seam)} &nbsp;<span style="color:var(--mut2)">(.${esc(s.attr)})</span></h3>`;
    if(s.seam_doc) h+=`<div class="md" style="margin-bottom:10px"><p>${esc(s.seam_doc.split('\n\n')[0])}</p></div>`;
    s.options.forEach(o=>{
      h+=`<div class="opt${o.active?' active':''}"><div class="ohead">`
       + `<span class="oname">${esc(o.cls)}</span>`
       + `<span class="otag ${o.active?'':'alt'}">${o.active?'active':'available'}</span></div>`
       + (o.doc?`<div class="odoc">${esc(o.doc.split('\n\n')[0])}</div>`:'')
       + `</div>`;
    });
    h+=`</div>`;
  });

  /* IO (chips clickable when documented) */
  const dchip = (name, cls, suffix) => {
    const has = !!FILE_DOCS[name];
    return `<span class="chip ${cls}${has?' has-doc':''}" data-file="${esc(name)}" `
         + `style="display:inline-block;margin:0 6px 6px 0"${has?' title="click for details"':''}>`
         + `${esc(name)}${suffix||''}</span>`;
  };
  h+=`<div class="dsec"><h3>inputs</h3>`+ (n.inputs.length
      ? n.inputs.map(i=>dchip(i.name, i.external?'ext':'', i.external?' · external':'')).join('')
      : `<span class="empty">none (root stage)</span>`) + `</div>`;
  h+=`<div class="dsec"><h3>outputs</h3>`+ n.outputs.map(o=>dchip(o,'out','')).join('') + `</div>`;

  /* neighbours */
  const navs = arr => arr.length ? arr.map(x=>`<span class="nav" data-go="${esc(x)}">${esc(x)}</span>`).join('') : '<span class="empty">none</span>';
  h+=`<div class="dsec"><h3>upstream</h3><div class="flow">${navs([...up])}</div></div>`;
  h+=`<div class="dsec"><h3>downstream</h3><div class="flow">${navs([...down])}</div></div>`;

  /* docs: class docstring + README */
  if(n.doc) h+=`<div class="dsec"><h3>module docstring</h3><div class="md">${md(n.doc)}</div></div>`;
  if(n.readme) h+=`<div class="dsec"><h3>README</h3><div class="md">${md(n.readme)}</div></div>`;

  const body=document.getElementById('dbody'); body.innerHTML=h; body.scrollTop=0;
  body.querySelectorAll('[data-go]').forEach(el=>el.addEventListener('click',()=>select(el.dataset.go)));
  wireFileChips(body);
  drawer.classList.add('show'); scrim.classList.add('show'); drawer.setAttribute('aria-hidden','false');
}

/* ---------- file popover: what a file is / how it's made / who makes+uses it ---------- */
const fpop=document.getElementById('fpop');
function closeFilePop(){ fpop.classList.remove('show'); }
function openFilePop(name, anchor){
  const doc=FILE_DOCS[name]; if(!doc) return;
  const prod=fileProducer(name), cons=fileConsumers(name);
  const link=id=>`<span class="nav" data-go="${esc(id)}">${esc(id)}</span>`;
  let h=`<button class="fclose" title="close">&times;</button>`
    + `<div class="fhead"><div class="ftitle">${esc(doc.title||name)}</div>`
    + `<div class="fname">${esc(name)}</div></div>`
    + `<div class="fbadges">`
    + (doc.format?`<span class="fbadge fmt">${esc(doc.format)}</span>`:'')
    + `<span class="fbadge">${prod?'derived':'external input'}</span></div>`
    + `<div class="fbody">`;
  if(doc.what) h+=`<div class="frow"><div class="flbl">what it is</div><div class="ftxt">${esc(doc.what)}</div></div>`;
  if(doc.how)  h+=`<div class="frow"><div class="flbl">how it's made</div><div class="ftxt">${esc(doc.how)}</div></div>`;
  h+=`<div class="frow"><div class="flbl">produced by</div><div class="fnav">`
    + (prod?link(prod.id):`<span class="empty">external — supplied to the pipeline</span>`)+`</div></div>`;
  h+=`<div class="frow"><div class="flbl">consumed by</div><div class="fnav">`
    + (cons.length?cons.map(c=>link(c.id)).join(''):`<span class="empty">none (terminal output)</span>`)+`</div></div>`;
  h+=`</div>`;
  fpop.innerHTML=h; fpop.classList.add('show');
  const r=anchor.getBoundingClientRect(), pw=fpop.offsetWidth, ph=fpop.offsetHeight;
  let left=Math.min(r.left, window.innerWidth-10-pw); left=Math.max(10,left);
  let top=r.bottom+8; if(top+ph>window.innerHeight-10) top=Math.max(10, r.top-8-ph);
  fpop.style.left=left+'px'; fpop.style.top=top+'px';
  fpop.querySelector('.fclose').addEventListener('click',e=>{e.stopPropagation();closeFilePop();});
  fpop.querySelectorAll('[data-go]').forEach(el=>el.addEventListener('click',e=>{
    e.stopPropagation(); closeFilePop(); select(el.dataset.go); }));
}
document.addEventListener('click',e=>{
  if(fpop.classList.contains('show') && !fpop.contains(e.target) && !e.target.closest('.chip.has-doc'))
    closeFilePop();
});
window.addEventListener('resize',closeFilePop);

/* ---------- tiny markdown (headings, bold/italic/code, lists, tables, quotes, links, hr, fences) ---------- */
function md(src){
  const lines=src.replace(/\r/g,'').split('\n');
  let out='', i=0;
  const inline=s=>esc(s)
    .replace(/`([^`]+)`/g,'<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>')
    .replace(/(^|[^*])\*([^*]+)\*/g,'$1<em>$2</em>')
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g,'<a href="$2" target="_blank" rel="noopener">$1</a>');
  while(i<lines.length){
    let l=lines[i];
    if(/^```/.test(l)){ let buf=[]; i++; while(i<lines.length&&!/^```/.test(lines[i])){buf.push(lines[i]);i++;} i++;
      out+='<pre><code>'+esc(buf.join('\n'))+'</code></pre>'; continue; }
    if(/^\s*$/.test(l)){ i++; continue; }
    let m=l.match(/^(#{1,6})\s+(.*)$/);
    if(m){ const lv=m[1].length; out+=`<h${lv}>${inline(m[2])}</h${lv}>`; i++; continue; }
    if(/^\s*([-*_])\1?\1?\s*$/.test(l) && l.trim().length>=3){ out+='<hr>'; i++; continue; }
    if(/^\s*>/.test(l)){ let buf=[]; while(i<lines.length&&/^\s*>/.test(lines[i])){buf.push(lines[i].replace(/^\s*>\s?/,''));i++;}
      out+='<blockquote>'+inline(buf.join(' '))+'</blockquote>'; continue; }
    if(/^\s*[-*]\s+/.test(l)){ out+='<ul>'; while(i<lines.length&&/^\s*[-*]\s+/.test(lines[i])){
        out+='<li>'+inline(lines[i].replace(/^\s*[-*]\s+/,''))+'</li>'; i++; } out+='</ul>'; continue; }
    if(l.includes('|') && i+1<lines.length && /^\s*\|?[\s:|-]+\|[\s:|-]*$/.test(lines[i+1])){
      const row=s=>s.replace(/^\s*\|/,'').replace(/\|\s*$/,'').split('|').map(c=>c.trim());
      const head=row(l); i+=2; let body='';
      while(i<lines.length && lines[i].includes('|') && lines[i].trim()!==''){
        body+='<tr>'+row(lines[i]).map(c=>`<td>${inline(c)}</td>`).join('')+'</tr>'; i++; }
      out+='<table><thead><tr>'+head.map(c=>`<th>${inline(c)}</th>`).join('')+'</tr></thead><tbody>'+body+'</tbody></table>';
      continue; }
    let buf=[l]; i++;
    while(i<lines.length && !/^\s*$/.test(lines[i]) && !/^(#{1,6}\s|```|\s*[-*]\s|\s*>)/.test(lines[i])
          && !(lines[i].includes('|')&&i+1<lines.length&&/^\s*\|?[\s:|-]+\|/.test(lines[i+1]))){ buf.push(lines[i]); i++; }
    out+='<p>'+inline(buf.join(' '))+'</p>';
  }
  return out;
}

/* ---------- filter ---------- */
document.querySelectorAll('.btn[data-filter]').forEach(b=>b.addEventListener('click',()=>{
  document.querySelectorAll('.btn[data-filter]').forEach(x=>x.classList.remove('on'));
  b.classList.add('on'); const f=b.dataset.filter;
  document.querySelectorAll('.node').forEach(n=>{
    n.style.display = (f==='all'||NODES[n.dataset.id].kind===f)?'':'none';
  });
  requestAnimationFrame(draw);
}));

draw();
window.addEventListener('resize',draw);
</script>
</body></html>
"""


def render_html(graph: dict) -> str:
    """Return a full standalone HTML document for an (enriched) graph dict."""
    return (_TEMPLATE
            .replace("__GRAPH__", json.dumps(graph))
            .replace("__NAME__", str(graph.get("name", "pipeline"))))


def write_html(pipeline, path, run_self_tests: bool = True, file_docs: dict | None = None) -> Path:
    """Render `pipeline` to a standalone interactive HTML file. Returns the path.

    `run_self_tests` executes each stage's self_test() at render time so the view
    shows a live pass/fail dot. Stages self-test on tiny in-memory fixtures, so
    this is cheap and side-effect-free; set False to skip.

    `file_docs` is an optional `{basename: {title, format, what, how, ...}}` map
    (domain-supplied — viz stays domain-agnostic). When given, matching I/O file
    chips become clickable and open a per-file explainer popover. Everything else
    about a file (producer, consumers) is derived from the graph."""
    _eager_import_approaches(pipeline)
    graph = _enrich(pipeline.to_graph(), pipeline, run_self_tests)
    graph["file_docs"] = file_docs or {}
    path = Path(path)
    path.write_text(render_html(graph))
    return path
