import { useEffect, useRef, useState } from 'react';

type Node = { person_id:string; name:string; role:string; source:string; source_key:string; film_count:number };
type Edge = { edge_id:string|null; a:Node; b:Node; shared_movie_count:number; bonus:number; capped:boolean };
type Version = { graph_id:string; dataset_id:string; source:string; report:{nodes:number;edges:number;evidence_rows:number;isolated_nodes:number} };
type Page<T> = {items:T[];next_offset:number|null};
type Film = {movie_id:string;title:string;year:number|null;source:string;source_url:string|null;poster_url:string|null;jobs_a:string[];jobs_b:string[]};
type Pair = {graph_id:string;dataset_id:string;edge:Edge;message:string};
const roles=['director','actor','writer','cinematographer','composer'];
const input='mt-2 w-full min-w-0 rounded border border-white/15 bg-stone-950 p-3 text-sm';
const identity=(n:Node)=>`${n.person_id}/${n.role}`;
const endpoint=(id:string)=>`/api/collaboration/${encodeURIComponent(id)}`;
async function get<T>(url:string, signal:AbortSignal):Promise<T> {
  const response=await fetch(url,{signal:AbortSignal.any([signal,AbortSignal.timeout(10000)])});
  if(!response.ok) throw new Error(response.status===404 ? 'This graph or credited role is unavailable. Refresh the graph list.' : 'Collaboration data unavailable. Check the API connection and Phase 6 migration, then retry.');
  return response.json() as Promise<T>;
}

function PersonPicker({label,graphId,value,onSelect,exclude}:{label:string;graphId:string;value:Node|null;onSelect:(n:Node|null)=>void;exclude?:string}) {
  const [text,setText]=useState('');const [query,setQuery]=useState('');const [role,setRole]=useState('');
  const [offset,setOffset]=useState(0);const [rows,setRows]=useState<Node[]>([]);const [next,setNext]=useState<number|null>(null);
  const [busy,setBusy]=useState(false);const [error,setError]=useState('');const [retry,setRetry]=useState(0);
  useEffect(()=>{
    const control=new AbortController();setBusy(true);setError('');
    const params=new URLSearchParams({q:query,limit:'20',offset:String(offset)});if(role)params.set('role',role);
    void get<Page<Node>>(`${endpoint(graphId)}/nodes?${params}`,control.signal).then(page=>{
      if(!control.signal.aborted){setRows(previous=>offset ? [...previous,...page.items.filter(n=>!previous.some(old=>identity(old)===identity(n)))] : page.items);setNext(page.next_offset);}
    }).catch(e=>{if(!control.signal.aborted)setError((e as Error).message);}).finally(()=>{if(!control.signal.aborted)setBusy(false);});
    return ()=>control.abort();
  },[graphId,query,role,offset,retry]);
  return <div className="min-w-0 rounded-lg border border-white/10 p-4">
    <h4 className="font-semibold">{label}</h4>
    <form className="mt-3" onSubmit={e=>{e.preventDefault();setRows([]);setOffset(0);setQuery(text.trim());onSelect(null);setRetry(n=>n+1);}}>
      <label className="text-xs text-stone-400">{label} name search<input className={input} value={text} maxLength={80} onChange={e=>setText(e.target.value)} placeholder="Search your imported catalog"/></label>
      <button className="button-secondary mt-2" disabled={busy} type="submit">Search {label.toLowerCase()}</button>
    </form>
    <label className="mt-4 block text-xs text-stone-400">{label} role filter<select className={input} value={role} onChange={e=>{setRole(e.target.value);setOffset(0);setRows([]);onSelect(null);}}><option value="">All professional roles</option>{roles.map(r=><option key={r}>{r}</option>)}</select></label>
    <label className="mt-4 block text-xs text-stone-400">{label} credited role<select className={input} value={value?identity(value):''} onChange={e=>onSelect(rows.find(n=>identity(n)===e.target.value)??null)} disabled={busy&&rows.length===0}>
      <option value="">Select a person and role</option>{rows.filter(n=>n.person_id!==exclude).map(n=><option key={identity(n)} value={identity(n)}>{n.name} · {n.role}</option>)}
    </select></label>
    {busy&&<p className="mt-2 text-xs" role="status">Loading credited roles…</p>}
    {!busy&&!rows.length&&!error&&<p className="mt-2 text-xs text-stone-400">No eligible roles match this search.</p>}
    {error&&<div role="alert" className="mt-2 text-sm text-amber-200"><p>{error}</p><button className="button-secondary mt-2" onClick={()=>setRetry(n=>n+1)}>Retry {label.toLowerCase()}</button></div>}
    {next!==null&&<button className="button-secondary mt-3" disabled={busy} onClick={()=>setOffset(next)}>More {label.toLowerCase()} choices</button>}
  </div>;
}

function Evidence({graphId,edge}:{graphId:string;edge:Edge}) {
  const [offset,setOffset]=useState(0);const [page,setPage]=useState<Page<Film>|null>(null);
  const [busy,setBusy]=useState(true);const [error,setError]=useState('');const [retry,setRetry]=useState(0);
  useEffect(()=>{
    const control=new AbortController();setBusy(true);setPage(null);setError('');
    void get<Page<Film>>(`${endpoint(graphId)}/edges/${edge.edge_id}/films?limit=5&offset=${offset}`,control.signal)
      .then(value=>{if(!control.signal.aborted)setPage(value);})
      .catch(e=>{if(!control.signal.aborted)setError((e as Error).message);})
      .finally(()=>{if(!control.signal.aborted)setBusy(false);});
    return ()=>control.abort();
  },[graphId,edge.edge_id,offset,retry]);
  return <div className="mt-4" aria-busy={busy}>
    {busy&&<p role="status">Loading shared-film evidence…</p>}
    {error&&<div role="alert"><p className="text-amber-200">{error}</p><button className="button-secondary mt-3" onClick={()=>setRetry(n=>n+1)}>Retry evidence</button></div>}
    {page&&<>
      <ol className="grid gap-3 md:grid-cols-2">{page.items.map(f=><li key={f.movie_id} className="rounded-lg border border-white/10 bg-stone-950/40 p-5">
        <h4 className="font-semibold">{f.title} <span className="text-sm font-normal text-stone-400">({f.year??'Year unavailable'})</span></h4>
        <p className="mt-1 text-xs text-stone-500">{f.source==='fixture'?'Synthetic fixture':'TMDB catalog'}</p>
        <dl className="mt-4 space-y-3 text-sm"><div><dt className="text-stone-400">{edge.a.name} · {edge.a.role}</dt><dd>{f.jobs_a.join(' / ')}</dd></div><div><dt className="text-stone-400">{edge.b.name} · {edge.b.role}</dt><dd>{f.jobs_b.join(' / ')}</dd></div></dl>
        {f.source_url&&<a className="mt-4 inline-block text-sm text-amber-200 underline underline-offset-4" href={f.source_url} target="_blank" rel="noreferrer">View movie on TMDB ↗</a>}
      </li>)}</ol>
      <p className="mt-4 text-xs text-stone-400">Showing {page.items.length?offset+1:0}–{offset+page.items.length} of {edge.shared_movie_count} shared films. Each movie counts once.</p>
      <div className="mt-3 flex flex-wrap gap-3"><button className="button-secondary" disabled={offset===0||busy} onClick={()=>setOffset(Math.max(0,offset-5))}>Previous shared films</button><button className="button-secondary" disabled={page.next_offset===null||busy} onClick={()=>{if(page.next_offset!==null)setOffset(page.next_offset);}}>Next shared films</button></div>
    </>}
  </div>;
}

function GraphExplorer({version}:{version:Version}) {
  const [role,setRole]=useState('');const [offset,setOffset]=useState(0);const [page,setPage]=useState<Page<Edge>|null>(null);
  const [busy,setBusy]=useState(true);const [error,setError]=useState('');const [retry,setRetry]=useState(0);
  const [a,setA]=useState<Node|null>(null);const [b,setB]=useState<Node|null>(null);
  const [selection,setSelection]=useState<Pair|null>(null);const [pairBusy,setPairBusy]=useState(false);const [pairError,setPairError]=useState('');
  const pairRequest=useRef<AbortController|null>(null);
  useEffect(()=>()=>pairRequest.current?.abort(),[]);
  useEffect(()=>{
    const control=new AbortController();setBusy(true);setError('');setPage(null);
    const params=new URLSearchParams({limit:'6',offset:String(offset)});if(role)params.set('role',role);
    void get<Page<Edge>>(`${endpoint(version.graph_id)}/edges?${params}`,control.signal)
      .then(value=>{if(!control.signal.aborted)setPage(value);})
      .catch(e=>{if(!control.signal.aborted)setError((e as Error).message);})
      .finally(()=>{if(!control.signal.aborted)setBusy(false);});
    return ()=>control.abort();
  },[version.graph_id,role,offset,retry]);
  function clearPair(){pairRequest.current?.abort();setPairBusy(false);setPairError('');setSelection(null);}
  async function compare(){
    if(!a||!b)return;
    pairRequest.current?.abort();const control=new AbortController();pairRequest.current=control;
    setPairBusy(true);setPairError('');setSelection(null);
    try{
      const params=new URLSearchParams({person_a:a.person_id,role_a:a.role,person_b:b.person_id,role_b:b.role});
      const value=await get<Pair>(`${endpoint(version.graph_id)}/pair?${params}`,control.signal);
      if(!control.signal.aborted)setSelection(value);
    }catch(e){if(!control.signal.aborted)setPairError((e as Error).message);}
    finally{if(!control.signal.aborted)setPairBusy(false);}
  }
  return <>
    <p className="mt-4 break-all text-xs text-stone-400">Dataset: {version.dataset_id} · {version.source==='fixture'?'Synthetic fixture':'Imported catalog'}</p>
    <dl className="my-6 grid grid-cols-2 gap-3 lg:grid-cols-4">{[['Role profiles',version.report.nodes],['Role-pair connections',version.report.edges],['Film evidence records',version.report.evidence_rows],['Profiles without shared credits',version.report.isolated_nodes]].map(([label,value])=><div key={label} className="rounded-lg border border-white/10 p-4"><dt className="text-xs text-stone-400">{label}</dt><dd className="mt-2 text-2xl">{value.toLocaleString()}</dd></div>)}</dl>
    <div className="flex flex-wrap items-end justify-between gap-4"><h3 className="text-lg font-semibold">Explore recorded collaborations</h3><label className="text-sm text-stone-400">Connection role filter<select className={input} value={role} onChange={e=>{setRole(e.target.value);setOffset(0);}}><option value="">All roles</option>{roles.map(r=><option key={r}>{r}</option>)}</select></label></div>
    <p className="mt-2 text-xs text-stone-500">Ordered by distinct shared-film count. The game bonus stops increasing after three films.</p>
    {busy&&<p className="mt-5" role="status">Loading collaborations…</p>}
    {error&&<div role="alert" className="mt-5"><p className="text-amber-200">{error}</p><button className="button-secondary mt-3" onClick={()=>setRetry(n=>n+1)}>Retry collaborations</button></div>}
    {page&&<>
      {!page.items.length&&<p className="mt-5 text-stone-400" role="status">No shared credits found in this dataset for this filter. Missing credits do not imply incompatibility.</p>}
      <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3">{page.items.map(e=><article key={e.edge_id} className="rounded-lg border border-white/10 bg-white/[.02] p-5">
        <p className="font-semibold">{e.a.name} <span className="block text-xs font-normal text-stone-400">{e.a.role}</span></p>
        <p className="my-3 text-xs tracking-wider text-amber-200">{e.shared_movie_count} SHARED FILM{e.shared_movie_count!==1?'S':''} · +{e.bonus} / 12</p>
        <p className="font-semibold">{e.b.name} <span className="block text-xs font-normal text-stone-400">{e.b.role}</span></p>
        <button className="button-secondary mt-5" onClick={()=>{clearPair();setSelection({graph_id:version.graph_id,dataset_id:version.dataset_id,edge:e,message:'Shared credits found in this dataset.'});}}>Inspect shared films</button>
      </article>)}</div>
      <div className="mt-5 flex flex-wrap gap-3"><button className="button-secondary" disabled={offset===0} onClick={()=>setOffset(Math.max(0,offset-6))}>Previous connections</button><button className="button-secondary" disabled={page.next_offset===null} onClick={()=>{if(page.next_offset!==null)setOffset(page.next_offset);}}>Next connections</button></div>
    </>}
    <div className="mt-10 border-t border-white/10 pt-8"><h3 className="text-lg font-semibold">Check a specific pair</h3><p className="mt-2 text-sm text-stone-400">Choose each person's credited role. A writer profile and an acting profile have different film evidence.</p>
      <div className="mt-5 grid gap-4 md:grid-cols-2"><PersonPicker label="Person A" graphId={version.graph_id} value={a} onSelect={n=>{clearPair();setA(n);setB(null);}}/><PersonPicker label="Person B" graphId={version.graph_id} value={b} exclude={a?.person_id} onSelect={n=>{clearPair();setB(n);}}/></div>
      <button className="button-primary mt-4" disabled={!a||!b||a.person_id===b.person_id||pairBusy} onClick={()=>void compare()}>{pairBusy?'Checking shared credits…':'Compare credited roles'}</button>
      {pairError&&<p role="alert" className="mt-3 text-amber-200">{pairError}</p>}
    </div>
    {selection&&<section className="mt-8 rounded-xl border border-amber-200/30 bg-amber-200/[.03] p-5 sm:p-7" aria-labelledby="shared-evidence-title">
      <p className="eyebrow">Shared-film evidence</p><h3 id="shared-evidence-title" className="text-xl">{selection.edge.a.name} · {selection.edge.a.role} &amp; {selection.edge.b.name} · {selection.edge.b.role}</h3>
      <p className="mt-4 text-lg">{selection.edge.shared_movie_count} shared films · <strong>+{selection.edge.bonus} / 12 game bonus</strong></p>
      {selection.edge.capped&&<p className="mt-2 text-sm text-amber-200">Bonus capped at 12. All supporting films remain available below.</p>}
      {!selection.edge.edge_id?<p className="mt-3 text-stone-300" role="status">{selection.message} This is not evidence that they never collaborated.</p>:<Evidence key={selection.edge.edge_id} graphId={version.graph_id} edge={selection.edge}/>}
    </section>}
    <a className="mt-6 inline-block text-sm text-amber-200 underline underline-offset-4" href={`${endpoint(version.graph_id)}/report`} target="_blank" rel="noreferrer">View graph build report ↗</a>
  </>;
}

export default function CollaborationLab(){
  const [versions,setVersions]=useState<Version[]>([]);const [selected,setSelected]=useState('');const [next,setNext]=useState<number|null>(null);
  const [loaded,setLoaded]=useState(false);const [busy,setBusy]=useState(false);const [error,setError]=useState('');
  const request=useRef<AbortController|null>(null);useEffect(()=>()=>request.current?.abort(),[]);
  async function load(offset=0){
    request.current?.abort();const control=new AbortController();request.current=control;setBusy(true);setError('');
    try{
      const page=await get<Page<Version>>(`/api/collaboration/versions?limit=20&offset=${offset}`,control.signal);
      if(!control.signal.aborted){setVersions(old=>offset?[...old,...page.items]:page.items);setNext(page.next_offset);setLoaded(true);if(!offset)setSelected(old=>page.items.some(v=>v.graph_id===old)?old:page.items[0]?.graph_id??'');}
    }catch(e){if(!control.signal.aborted)setError((e as Error).message);}
    finally{if(!control.signal.aborted)setBusy(false);}
  }
  const version=versions.find(v=>v.graph_id===selected);
  return <section className="border-t border-white/10 py-12" aria-labelledby="collaboration-title">
    <div className="flex flex-wrap items-start justify-between gap-4"><div><p className="eyebrow">04 / Collaboration lab</p><h2 id="collaboration-title">Every connection has a credit.</h2></div><button className="button-secondary" disabled={busy} onClick={()=>void load()}>{busy?'Loading graphs…':loaded?'Refresh collaboration graphs':'Load collaboration graphs'}</button></div>
    <p className="mt-4 max-w-3xl text-sm leading-relaxed text-stone-400">Explore shared films in your imported catalog, with exact professional roles and source jobs. The bonus is a fictional game rule; shared credits do not describe friendship, compatibility or personal relationships.</p>
    {error&&<p role="alert" className="mt-4 text-amber-200">{error}</p>}
    {loaded&&!versions.length&&<p role="status" className="mt-5 text-stone-400">No published collaboration graphs yet. Follow the Phase 6 README to preview and publish a graph from your sealed dataset, then refresh here.</p>}
    {!!versions.length&&<><label className="mt-6 block max-w-xl text-sm text-stone-400">Published collaboration graph<select className={input} value={selected} onChange={e=>setSelected(e.target.value)}>{versions.map(v=><option key={v.graph_id} value={v.graph_id}>{v.graph_id} ({v.source})</option>)}</select></label>{next!==null&&<button className="button-secondary mt-3" disabled={busy} onClick={()=>void load(next)}>Load more graphs</button>}</>}
    {version&&<GraphExplorer key={version.graph_id} version={version}/>}
  </section>;
}
