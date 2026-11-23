import {useEffect,useState,useId} from 'react';
import type {Draft} from './DraftInspector';
type Attempt={attempt_number:number;status:'succeeded'|'failed';message:string;error_code:string|null};
type Status={status:string;latest_attempt:Attempt|null;result_available:boolean};
type Edge={slot_a:string;slot_b:string;person_id_a:string;person_id_b:string;canonical_a:[string,string];canonical_b:[string,string];name_a:string;name_b:string;role_a:string;role_b:string;edge_id:string|null;shared_movie_count:number;bonus:number;message:string};
type Film={movie_id:string;title:string;year:number|null;jobs_a:string[];jobs_b:string[]};
export type ReleaseResult={schema_version:string;draft_id:string;input_hash:string;simulation_id:string;simulation_version:string;synthetic:boolean;versions:{graph_id:string;catalog_id:string};studio_score:number;studio_score_unrounded:string;critics:number;audience:number;cast_appeal:string;score_components:{name:string;value:string;weight:string;contribution:string}[];production_cost_usd:number;marketing_usd:number;total_cost_usd:number;worldwide_gross_usd:number;studio_receipts_usd:number;profit_usd:number;return_on_total_cost_percent:string;weekly_gross_usd:number[];unused_talent_budget_usd:number;explanation:{note:string;finance_note:string;rows:{slot:string;name:string;genre_contribution:string;hiring_fee_usd:number}[];top_genre_contributors:string[];chemistry_edges:Edge[];warnings:string[]};reproducibility:Record<string,unknown>};
type Saved={output_hash:string;result:ReleaseResult};
const money=(n:number)=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:0}).format(n);
export function displayDecimal(value:string){
 const negative=value.startsWith('-');const [whole,fraction='']=value.replace(/^-/,'').split('.');const digits=fraction.padEnd(3,'0');
 let cents=BigInt(whole)*100n+BigInt(digits.slice(0,2));if(digits[2]>='5')cents+=1n;
 return `${negative&&cents>0n?'-':''}${cents/100n}.${String(cents%100n).padStart(2,'0')}`;
}
const short=displayDecimal;
const label=(value:string)=>value.replaceAll('_',' ');
async function get<T>(path:string,token:string,signal:AbortSignal):Promise<T>{
 const response=await fetch(path,{cache:'no-store',headers:token?{Authorization:'Bearer '+token}:{},signal});
 const value=await response.json().catch(()=>null);
 if(!response.ok||!value)throw new Error(value?.error?.message??'Release API unavailable. Check the connection and Phase 8 migration.');
 return value as T;
}
function FilmEvidence({edge,graph}:{edge:Edge;graph:string}){
 const [page,setPage]=useState<{items:Film[];next_offset:number|null}|null>(null);const [offset,setOffset]=useState(0);const [error,setError]=useState('');const [loading,setLoading]=useState(false);const [opened,setOpened]=useState(false);const [retry,setRetry]=useState(0);
 useEffect(()=>{
  if(!opened||!edge.edge_id)return;
  let alive=true;const control=new AbortController();const timer=setTimeout(()=>control.abort(),20000);setLoading(true);setError('');setPage(null);
  void get<{items:Film[];next_offset:number|null}>(`/api/collaboration/${encodeURIComponent(graph)}/edges/${edge.edge_id}/films?limit=5&offset=${offset}`,'',control.signal)
   .then(value=>{if(alive)setPage(value);}).catch(e=>{if(alive)setError(control.signal.aborted?'Film evidence request timed out. Retry to inspect it.':(e as Error).message);}).finally(()=>{clearTimeout(timer);if(alive)setLoading(false);});
  return()=>{alive=false;clearTimeout(timer);control.abort();};
 },[opened,offset,retry,edge.edge_id,graph]);
 if(!edge.edge_id)return <p className="mt-2 text-xs text-stone-400">{edge.message}</p>;
 return <div className="mt-3">
  <button className="button-secondary text-sm" onClick={()=>setOpened(v=>!v)}>{opened?'Hide':'Inspect'} shared films</button>
  {opened&&<>{loading&&<p className="mt-2 text-sm" role="status">Loading frozen graph evidence…</p>}{error&&<div className="mt-3" role="alert"><p>{error}</p><button className="button-secondary mt-2" onClick={()=>setRetry(x=>x+1)}>Retry shared films</button></div>}
  {page&&<><p className="mt-3 text-xs text-stone-400">Exact credited jobs for the selected roles; each film counts once.</p><ul className="mt-2 space-y-3">{page.items.map(f=><li key={f.movie_id} className="text-sm">{f.title} ({f.year??'year unknown'})<span className="block text-xs text-stone-400">{edge.name_a} ({edge.role_a}): {(edge.canonical_a[0]===edge.person_id_a?f.jobs_a:f.jobs_b).join(' / ')} · {edge.name_b} ({edge.role_b}): {(edge.canonical_a[0]===edge.person_id_a?f.jobs_b:f.jobs_a).join(' / ')}</span></li>)}</ul><div className="mt-3 flex gap-2"><button className="button-secondary" disabled={offset===0||loading} onClick={()=>setOffset(Math.max(0,offset-5))}>Previous evidence</button><button className="button-secondary" disabled={page.next_offset===null||loading} onClick={()=>setOffset(page.next_offset!)}>Next evidence</button></div></>}
  </>}
 </div>;
}
export default function ReleaseInspector({draft,token,disabled,onAction}:{draft:Draft;token:string;disabled:boolean;onAction:(path:string)=>void}){
 const releaseId=useId();
 const [status,setStatus]=useState<Status|null>(null);const [saved,setSaved]=useState<Saved|null>(null);const [error,setError]=useState('');const [loading,setLoading]=useState(true);const [refresh,setRefresh]=useState(0);
 useEffect(()=>{
  let alive=true;const control=new AbortController();const timer=setTimeout(()=>control.abort(),20000);setLoading(true);setError('');setSaved(null);setStatus(null);
  void (async()=>{
   const state=await get<Status>(`/api/v1/drafts/${draft.draft_id}/simulation`,token,control.signal);if(!alive)return;setStatus(state);
   if(state.result_available){const result=await get<Saved>(`/api/v1/drafts/${draft.draft_id}/result`,token,control.signal);if(alive)setSaved(result);}
  })().catch(e=>{if(alive)setError(control.signal.aborted?'Release read timed out. Refresh the report.':(e as Error).message);}).finally(()=>{clearTimeout(timer);if(alive)setLoading(false);});
  return()=>{alive=false;clearTimeout(timer);control.abort();};
 },[draft.draft_id,draft.revision,draft.status,token,refresh]);
 const result=saved?.result;const changed=status&&status.status!==draft.status;
 return <section className="mt-7 border-t border-white/10 pt-6" aria-labelledby={releaseId}>
  <div className="flex flex-wrap items-center justify-between gap-3"><div><p className="eyebrow">Release report</p><h4 id={releaseId} className="text-xl">What happens on opening night?</h4></div><button className="button-secondary" disabled={loading||disabled} onClick={()=>setRefresh(v=>v+1)}>Refresh release report</button></div>
  <p className="mt-3 text-sm text-stone-400">One fictional release from your frozen roster. A successful result is saved permanently; retrying a request cannot reroll it.</p>
  {loading&&<p className="mt-4" role="status">Loading release state…</p>}{error&&<p className="mt-4 text-amber-200" role="alert">{error}</p>}
  {changed&&<p className="mt-4 text-amber-200" role="status">The server state changed. Use Refresh draft above before another action.</p>}
  {draft.status==='production_finalized'&&!result&&<button className="button-primary mt-5" disabled={disabled||loading||!!changed||!!error} onClick={()=>onAction('release')}>Run release simulation</button>}
  {draft.status==='simulation_failed'&&<div className="mt-4"><p role="alert">{status?.latest_attempt?.message??'The last simulation failed. The original roster and seed remain saved.'}</p><button className="button-primary mt-3" disabled={disabled||loading||!!changed||!!error} onClick={()=>onAction('retry-simulation')}>Retry failed simulation</button><p className="mt-2 text-xs text-stone-400">This is a new retry command after a confirmed engine failure. For an interrupted request, use Retry same request above.</p></div>}
  {draft.status==='simulation_running'&&<p className="mt-4">The server is processing this release. Refresh the draft to check its saved state.</p>}
  {result&&<>
   <p className="mt-6 text-xs uppercase tracking-wider text-amber-200">{result.synthetic?'Synthetic practice release':'TMDB source roster · fictional release'}</p>
   <div className="mt-4 grid gap-3 sm:grid-cols-3">{[['Studio score',result.studio_score],['Simulated critics',result.critics.toFixed(2)],['Simulated audience',result.audience.toFixed(2)]].map(([k,v])=><div className="rounded-lg border border-white/10 p-5" key={k}><p className="text-sm text-stone-400">{k}</p><p className="mt-2 text-3xl">{v}<span className="text-sm text-stone-500"> / 100</span></p></div>)}</div>
   <p className="mt-3 text-xs text-stone-400">Simulated reviews are game outputs, separate from TMDB audience ratings. Studio score contains no box-office bonus.</p>
   <div className="mt-6 overflow-x-auto"><table className="w-full text-left text-sm"><caption className="mb-3 text-left text-lg font-semibold">Why this score?</caption><thead><tr className="border-b border-white/10"><th className="py-3 pr-3">Component</th><th className="pr-3">Value / 100</th><th className="pr-3">Weight</th><th>Score contribution</th></tr></thead><tbody>{result.score_components.map(c=><tr key={c.name} className="border-b border-white/5"><th className="py-3 pr-3 font-normal capitalize">{c.name}</th><td>{short(c.value)}</td><td>{(Number(c.weight)*100).toFixed(0)}%</td><td>{short(c.contribution)}</td></tr>)}</tbody></table></div>
   <p className="mt-3 text-xs text-stone-400">Studio score rounds to {result.studio_score} using half-up rounding. Displayed components use two decimals; the saved report retains full precision.</p>
   <p className="mt-3 text-sm">Top weighted genre contributors: {result.explanation.top_genre_contributors.map(slot=>{const person=result.explanation.rows.find(r=>r.slot===slot);return `${person?.name??slot} (${label(slot)})`;}).join('; ')}.</p>
   <div className="mt-7"><h5 className="text-lg font-semibold">Fictional financial outcome</h5><dl className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{[['Worldwide theatrical gross',money(result.worldwide_gross_usd)],['Studio receipts',money(result.studio_receipts_usd)],['Committed production',money(result.production_cost_usd)],['Marketing',money(result.marketing_usd)],['Total production + marketing',money(result.total_cost_usd)],['Profit after marketing',money(result.profit_usd)]].map(([k,v])=><div className="rounded-lg bg-white/5 p-4" key={k}><dt className="text-xs text-stone-400">{k}</dt><dd className="mt-2 text-xl">{v}</dd></div>)}</dl><p className="mt-3 text-sm">Return on total cost: {short(result.return_on_total_cost_percent)}%. Unused talent authorization: {money(result.unused_talent_budget_usd)}.</p><p className="mt-2 text-xs leading-relaxed text-stone-400">{result.explanation.finance_note} Unspent talent authorization is not charged as production cost.</p></div>
   <div className="mt-7"><h5 className="text-lg font-semibold">Four-week theatrical run</h5><ol className="mt-4 space-y-3">{result.weekly_gross_usd.map((amount,i)=><li key={i}><div className="flex justify-between gap-3 text-sm"><span>Week {i+1}</span><span>{money(amount)}</span></div><div className="mt-2 h-2 rounded-full bg-white/10" aria-hidden="true"><div className="h-full rounded-full bg-amber-200/80" style={{width:`${result.worldwide_gross_usd?amount/result.worldwide_gross_usd*100:0}%`}}/></div></li>)}</ol><p className="mt-3 text-xs text-stone-400">Weeks sum to {money(result.worldwide_gross_usd)}. Week four includes the integer-dollar rounding remainder.</p></div>
   <details className="mt-7"><summary className="cursor-pointer text-lg font-semibold">The twelve chemistry relationships</summary><p className="mt-3 text-sm text-stone-400">No shared credits gives neutral chemistry, not incompatibility. Each connection adds at most 12 evidence points after three shared films.</p><div className="mt-4 grid gap-3 md:grid-cols-2">{result.explanation.chemistry_edges.map(edge=><article key={edge.slot_a+edge.slot_b} className="rounded-lg border border-white/10 p-4"><h6 className="font-semibold">{edge.name_a} · {edge.name_b}</h6><p className="mt-1 text-xs text-stone-400">{label(edge.slot_a)} / {label(edge.slot_b)} · {edge.role_a} / {edge.role_b}</p><p className="mt-3 text-sm">{edge.shared_movie_count} shared films · +{edge.bonus} / 12</p><FilmEvidence edge={edge} graph={result.versions.graph_id}/></article>)}</div></details>
   {!!result.explanation.warnings.length&&<details className="mt-6"><summary className="cursor-pointer font-semibold">Source coverage notes ({result.explanation.warnings.length})</summary><ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-stone-400">{result.explanation.warnings.map((w,i)=><li key={i}>{w}</li>)}</ul></details>}
   <p className="mt-6 text-sm text-stone-400">{result.explanation.note}</p><p className="mt-3 break-all text-xs text-stone-500">Input SHA-256: {result.input_hash}<br/>Output SHA-256: {saved.output_hash}</p>
   <details className="mt-5 text-xs text-stone-400"><summary>Inspect saved result and reproducibility record</summary><pre className="mt-3 max-h-96 overflow-auto whitespace-pre-wrap break-all">{JSON.stringify(saved,null,2)}</pre></details>
  </>}
 </section>;
}
