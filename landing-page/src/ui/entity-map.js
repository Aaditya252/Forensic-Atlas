const esc = value => String(value ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const kinds = ['Case','Evidence','Entity','Inspection','Agent memory','Report'];
let graph = null, selected = null, zoom = 1;

export function renderEntityMap(data) {
  graph = data; selected = null; zoom = 1;
  if (!data) return '';
  return `<section class="atlas-map panel" aria-label="Interactive evidence relationship map"><header class="atlas-map-header"><div><span class="eyebrow">CASE INTELLIGENCE / PROVENANCE EXPLORER</span><h2>Follow the evidence.</h2><p>Hover to understand. Select to investigate. Every link keeps its recorded basis.</p></div><span class="atlas-map-live">${data.demo?'Fictional demo · saved graph remains local':data.graphAvailable?'FalkorDB connected':'Graph offline · local records only'}</span></header><div class="atlas-map-tools"><label>Find a record<input type="search" data-map-search placeholder="Name, ID or evidence source…" /></label><label>View<select data-map-view><option value="investigation">Investigation</option><option value="all">Full provenance</option></select></label><label>Layer<select data-map-kind><option value="">All layers</option>${kinds.map(k=>`<option>${esc(k)}</option>`).join('')}</select></label><div class="atlas-map-zoom"><button type="button" data-map-zoom="out" aria-label="Zoom out graph">−</button><button type="button" data-map-zoom="reset">Fit</button><button type="button" data-map-zoom="in" aria-label="Zoom in graph">+</button></div><button type="button" class="button" data-map-clear>Clear selection</button></div><div class="atlas-map-layout"><div><div class="atlas-map-count" aria-live="polite"></div><div class="atlas-map-stage" tabindex="0" aria-label="Scrollable relationship map"><div data-map-drawing></div></div><div class="atlas-map-legend">${kinds.map((k,i)=>`<span><i style="background:var(--map-${i})"></i>${esc(k)}</span>`).join('')}<span>— Recorded / provenance</span><span>┄ Candidate / hypothesis</span></div></div><aside class="atlas-map-inspector" aria-label="Relationship explanation"><div data-map-details><span class="eyebrow">INVESTIGATION NOTES</span><h3>What connects to what?</h3><p>Hover a node or a line to see why it exists. Click or press Enter to pin its explanation here.</p><div class="atlas-map-guide"><b>01 · Source</b><p>Start with the original evidence.</p><b>02 · Derivation</b><p>Follow inspections and cited agent output.</p><b>03 · Review</b><p>Check alternatives before forming a finding.</p></div></div></aside></div><footer class="atlas-map-foot">${esc(data.notice)}<br>Layout proximity is visual organization, not evidence strength. No confidence or causal scores are inferred.</footer></section>`;
}

function draw() {
  const root=document.querySelector('.atlas-map'); if(!root || !graph)return;
  const query=root.querySelector('[data-map-search]').value.toLowerCase(),kind=root.querySelector('[data-map-kind]').value;
  const view=root.querySelector('[data-map-view]').value;
  const primary=graph.nodes.filter(n=>(!kind||n.kind===kind)&&(!query||[n.name,n.id,...n.sources].join(' ').toLowerCase().includes(query))&&(view==='all'||kind||!['Agent memory','Report'].includes(n.kind)));
  const included=new Set(primary.map(n=>n.id));
  if(kind||query)graph.edges.forEach(e=>{if(primary.some(n=>n.id===e.from||n.id===e.to)){included.add(e.from);included.add(e.to);}});
  const all=graph.nodes.filter(n=>included.has(n.id));
  const nodes=all.slice(0,80),ids=new Set(nodes.map(n=>n.id)),groups=kinds.filter(k=>nodes.some(n=>n.kind===k));
  const height=Math.max(440,...groups.map(k=>nodes.filter(n=>n.kind===k).length*92+95)),width=Math.max(500,groups.length*220+60),positions=new Map();
  groups.forEach((kind,col)=>nodes.filter(n=>n.kind===kind).forEach((n,row)=>positions.set(n.id,{x:140+col*220,y:100+row*92})));
  const edges=graph.edges.filter(e=>ids.has(e.from)&&ids.has(e.to));
  root.querySelector('.atlas-map-count').textContent=`${nodes.length} / ${graph.nodes.length} nodes displayed · ${edges.length} links${all.length>80?' · narrow the search to see remaining nodes':''}`;
  const neighbor=new Set(selected?[selected]:[]); graph.edges.forEach(e=>{if(e.from===selected)neighbor.add(e.to);if(e.to===selected)neighbor.add(e.from);});
  root.querySelector('[data-map-drawing]').innerHTML=`<svg width="${width*zoom}" height="${height*zoom}" viewBox="0 0 ${width} ${height}" aria-label="Evidence provenance diagram"><defs><pattern id="mapDots" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="1" fill="currentColor" opacity=".09"/></pattern><marker id="mapArrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0 0L7 3.5L0 7" fill="currentColor"/></marker></defs><rect width="100%" height="100%" fill="url(#mapDots)"/>${groups.map((k,i)=>`<text x="${140+i*220}" y="30" text-anchor="middle" class="atlas-lane-label">${esc(k.toUpperCase())}</text>`).join('')}${edges.map(e=>{const a=positions.get(e.from),b=positions.get(e.to),dim=selected&&e.from!==selected&&e.to!==selected;return `<g class="atlas-link ${['candidate','hypothesis'].includes(e.state)?'candidate':''} ${dim?'dim':''}" tabindex="0" role="button" data-map-edge="${graph.edges.indexOf(e)}" aria-label="${esc(e.label+'; '+e.reason)}"><path d="M${a.x} ${a.y} C${(a.x+b.x)/2} ${a.y},${(a.x+b.x)/2} ${b.y},${b.x} ${b.y}" marker-end="url(#mapArrow)"/><title>${esc(e.label+' · '+e.state+'\n'+e.reason)}</title><text x="${(a.x+b.x)/2}" y="${(a.y+b.y)/2-7}" text-anchor="middle">${esc(e.label)}</text></g>`;}).join('')}${nodes.map(n=>{const p=positions.get(n.id),index=graph.nodes.indexOf(n);return `<g transform="translate(${p.x-90},${p.y-28})" tabindex="0" role="button" class="atlas-graph-node ${selected===n.id?'selected':''} ${selected&&!neighbor.has(n.id)?'dim':''}" data-map-node="${index}" aria-label="${esc(n.kind+': '+n.name+'; '+n.state)}" style="--node-color:var(--map-${kinds.indexOf(n.kind)})"><title>${esc(n.name+'\n'+n.reason)}</title><rect width="180" height="58" rx="11"/><rect class="atlas-node-stripe" width="4" height="34" y="12" rx="2"/><text x="13" y="24">${esc(n.name.length>22?n.name.slice(0,21)+'…':n.name)}</text><text x="13" y="43" class="atlas-node-id">${esc(n.id.length>24?n.id.slice(0,23)+'…':n.id)}</text></g>`;}).join('')}</svg>`;
  if(!nodes.length)root.querySelector('[data-map-drawing]').innerHTML='<div class="empty-state">No matching records. Clear the filters to see the case.</div>';
}

function explain(target,pin=false) {
  const nodeIndex=target.getAttribute('data-map-node'),item=nodeIndex!==null?graph.nodes[Number(nodeIndex)]:graph.edges[Number(target.getAttribute('data-map-edge'))];
  if(!item)return;
  if(pin){selected=nodeIndex!==null?item.id:item.from;draw();document.querySelector(`[data-map-node="${graph.nodes.findIndex(n=>n.id===selected)}"]`)?.focus();}
  const details=document.querySelector('[data-map-details]');if(!details)return;
  details.innerHTML=`<span class="eyebrow">${pin?'PINNED EXPLANATION':'HOVER PREVIEW'} · ${esc(item.kind||'RELATIONSHIP')}</span><h3>${esc(item.name||item.label)}</h3><span class="atlas-state">${esc(item.state)}</span>${item.from?`<p class="atlas-map-endpoints">${esc(item.from)} → ${esc(item.to)}</p>`:`<p class="atlas-map-endpoints">${esc(item.id)}</p>`}<h4>Why this is here</h4><p>${esc(item.reason)}</p><h4>Supporting sources</h4>${item.sources.length?item.sources.map(id=>`<code>${esc(id)}</code>`).join(' '):'<p>No direct source citation. Membership alone is not evidence of a relationship.</p>'}<h4>Next investigation step</h4><p>${esc(item.nextStep)}</p><div class="atlas-map-caution">A link is not proof of cause, intent, identity, or authenticity. Check original records and alternative explanations.</div>${pin?'<button class="button" type="button" data-map-trace>Use in path agent ↓</button>':''}`;
}

document.addEventListener('pointerover',e=>{
 const t=e.target.closest('[data-map-node],[data-map-edge]');if(!t||!graph)return;if(!selected)explain(t);
 const item=t.hasAttribute('data-map-node')?graph.nodes[Number(t.dataset.mapNode)]:graph.edges[Number(t.dataset.mapEdge)];
 let tip=document.getElementById('atlasMapTooltip');if(!tip){tip=document.createElement('div');tip.id='atlasMapTooltip';tip.className='atlas-map-tooltip';tip.setAttribute('role','tooltip');document.body.append(tip);}
 tip.innerHTML=`<strong>${esc(item.name||item.label)}</strong><small>${esc(item.kind||'Relationship')} / ${esc(item.state)}</small><p>${esc(item.reason.slice(0,260))}</p><small>Sources: ${esc(item.sources.join(', ')||'No direct citation')} / Click to pin</small>`;
 tip.style.left=Math.min(Math.max(10,e.clientX+16),Math.max(10,innerWidth-340))+'px';tip.style.top=Math.min(Math.max(10,e.clientY+16),Math.max(10,innerHeight-230))+'px';tip.hidden=false;
});
document.addEventListener('pointerout',e=>{const t=e.target.closest('[data-map-node],[data-map-edge]');if(t&&!t.contains(e.relatedTarget))document.getElementById('atlasMapTooltip')?.setAttribute('hidden','');});
document.addEventListener('focusin',e=>{const t=e.target.closest('[data-map-node],[data-map-edge]');if(t&&graph&&!selected)explain(t);});
document.addEventListener('keydown',e=>{if(['Enter',' '].includes(e.key)&&e.target.matches('[data-map-node],[data-map-edge]')){e.preventDefault();explain(e.target,true);}});
document.addEventListener('click',e=>{
  const target=e.target.closest('[data-map-node],[data-map-edge]');if(target&&graph){document.getElementById('atlasMapTooltip')?.setAttribute('hidden','');explain(target,true);return;}
  const action=e.target.closest('[data-map-zoom],[data-map-clear],[data-map-trace]');if(!action)return;
  if(action.hasAttribute('data-map-trace')){const select=document.getElementById('graphEntityId');if(select&&[...select.options].some(o=>o.value===selected)){select.value=selected;document.getElementById('graphQuestion')?.focus();select.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'center'});}else{action.textContent='No traversable CaseEntity for this record';}return;}
  if(action.hasAttribute('data-map-clear')){selected=null;document.querySelector('[data-map-details]').innerHTML='<h3>Selection cleared</h3><p>Hover or select a node or relationship to inspect its recorded basis.</p>';}
  else{const type=action.dataset.mapZoom;zoom=type==='reset'?Math.max(.3,Math.min(1,document.querySelector('.atlas-map-stage').clientWidth/(document.querySelector('.atlas-map-stage svg')?.viewBox.baseVal.width||960))):Math.max(.5,Math.min(1.8,zoom+(type==='in'?.15:-.15)));}
  draw();
});
document.addEventListener('input',e=>{if(e.target.matches('[data-map-search]'))draw();});
document.addEventListener('change',e=>{if(e.target.matches('[data-map-kind],[data-map-view]'))draw();});
// The page renderer replaces the map after asynchronous navigation or refresh.
new MutationObserver(()=>{const stage=document.querySelector('[data-map-drawing]');if(stage&&!stage.childNodes.length)draw();}).observe(document.body,{childList:true,subtree:true});
