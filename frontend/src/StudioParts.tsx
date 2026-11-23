import {useEffect,useRef,useState,type ReactNode} from 'react';
import {api,type Card,type Member,type Work} from './studioApi';
export const usd=(n:number)=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:0}).format(n);
export const label=(s:string)=>s.replaceAll('_',' ');
export const slots=['director','lead','co_lead','supporting_1','supporting_2','writer','cinematographer','composer'];
export function Modal({title,onClose,children}:{title:string;onClose:()=>void;children:ReactNode}){
 const dialog=useRef<HTMLDialogElement>(null);
 useEffect(()=>{const previous=document.activeElement as HTMLElement|null;const el=dialog.current!;el.showModal();return()=>{el.close();if(previous?.isConnected)previous.focus();};},[]);
 return <dialog ref={dialog} className="studio-modal" aria-labelledby="modal-title" onCancel={e=>{e.preventDefault();onClose();}}><div className="modal-top"><h2 id="modal-title">{title}</h2><button autoFocus className="button-secondary" onClick={onClose} aria-label="Close dialog">Close</button></div>{children}</dialog>;
}
function Poster({work}:{work:Work}){
 const [failed,setFailed]=useState(false);
 return work.poster_url&&!failed?<img className="work-poster" src={work.poster_url} alt="" loading="lazy" onError={()=>setFailed(true)}/>:<span className="work-poster placeholder" aria-hidden="true">FILM</span>;
}
export function Works({works,source}:{works:Work[];source:string}){
 return <ol className="work-list">{works.map(w=><li key={w.movie_id}><Poster work={w}/><div><strong>{w.title}</strong><span>{w.year??w.release_date?.slice(0,4)??'Year unavailable'} · {w.credited_jobs.join(' / ')}</span><small>{w.audience_rating==null?'No audience rating':`${source==='fixture'?'Synthetic':'TMDB'} audience ${w.audience_rating.toFixed(1)} / 10`}</small></div></li>)}</ol>;
}
export function CardFace({card,children}:{card:Card;children?:ReactNode}){
 return <article className="candidate-card"><div className="candidate-heading"><span className="initials" aria-hidden="true">{card.name.split(' ').map(s=>s[0]).slice(0,2).join('')}</span><div><h4>{card.name}</h4><p>{label(card.role)} · {card.source==='fixture'?'Synthetic practice':'TMDB catalog'}</p></div></div><p className="candidate-price">{usd(card.hiring_fee_usd)}</p><p className="muted small">Fictional game fee · USD</p><dl className="attributes"><div><dt>Talent strength</dt><dd>{card.talent_strength??'Unknown'}<small> / 100</small></dd></div><div><dt>Genre fit</dt><dd>{card.genre_fit??'Unknown'}<small> / 100</small></dd></div></dl>{!!card.specialties?.length&&<p className="specialties">{card.specialties.slice(0,3).map(label).join(' · ')}</p>}<p className="muted small">{card.coverage}</p><h5>Notable films · from our catalog</h5><Works works={card.notable_works} source={card.source}/><p className="muted small">{card.notable_works.length} verified films shown{card.notable_works.length<5?' · limited catalog coverage':''}.</p>{children}</article>;
}
type Films={items:Work[];next_offset:number|null};
type Profile={reception:number;experience:number;versatility:number;genre_evidence_movies:number;genre_catalog_gap:boolean;coverage:{eligible_movies:number;rated_movies:number}};
type Pair={edge:{edge_id:string|null;shared_movie_count:number;bonus:number};message:string};
export function CandidateDetails({card,genre,members,onClose}:{card:Card;genre:string;members:Member[];onClose:()=>void}){
 const [films,setFilms]=useState<Films|null>(null),[profile,setProfile]=useState<Profile|null>(null),[offset,setOffset]=useState(0),[error,setError]=useState(''),[loading,setLoading]=useState(true),[retry,setRetry]=useState(0);
 const [pairs,setPairs]=useState<{name:string;text:string}[]>([]);
 useEffect(()=>{
  const c=new AbortController();let alive=true;setLoading(true);setError('');setFilms(null);
  if(!card.versions){setError('Pinned evidence identifiers are unavailable. Refresh the draft.');setLoading(false);return()=>{alive=false;c.abort();};}
  const v=card.versions;
  void Promise.all([api<Films>(`/api/catalog/${encodeURIComponent(v.dataset_id)}/people/${card.person_id}/films?role=${card.role}&limit=10&offset=${offset}`,'',undefined,c.signal),api<Profile>(`/api/talent/${encodeURIComponent(v.pricing_id)}/profiles/${card.person_id}/${card.role}?genre=${genre}`,'',undefined,c.signal)]).then(([f,p])=>{if(alive){setFilms(f);setProfile(p);}}).catch(e=>{if(alive)setError((e as Error).message);}).finally(()=>{if(alive)setLoading(false);});
  return()=>{alive=false;c.abort();};
 },[card,genre,offset,retry]);
 useEffect(()=>{
  const c=new AbortController();let alive=true;setPairs([]);if(!card.versions)return;
  void Promise.all(members.filter(m=>m.card.person_id!==card.person_id).map(async m=>{
   try{const q=new URLSearchParams({person_a:card.person_id,role_a:card.role,person_b:m.card.person_id,role_b:m.card.role});const p=await api<Pair>(`/api/collaboration/${encodeURIComponent(card.versions!.graph_id)}/pair?${q}`,'',undefined,c.signal);return{name:m.card.name,text:p.edge.shared_movie_count?`${p.edge.shared_movie_count} shared films`:'No shared credits found in this dataset.'};}
   catch{return{name:m.card.name,text:'Evidence unavailable. Reopen details to retry.'};}
  })).then(items=>{if(alive)setPairs(items);});return()=>{alive=false;c.abort();};
 },[card,members]);
 return <Modal title={card.name+' · talent dossier'} onClose={onClose}><p className="muted">{label(card.role)} · {card.source==='fixture'?'Invented practice data':'Imported TMDB records'}. Only the draft’s pinned dataset is shown.</p>{loading&&<p role="status">Loading filmography and calculation evidence…</p>}{error&&<div className="callout" role="alert"><p>{error}</p><button className="button-secondary" onClick={()=>setRetry(x=>x+1)}>Retry evidence</button></div>}{profile&&<><h3>Behind the attributes</h3><dl className="attributes"><div><dt>Reception</dt><dd>{profile.reception}</dd></div><div><dt>Experience</dt><dd>{profile.experience}</dd></div><div><dt>Versatility</dt><dd>{profile.versatility}</dd></div></dl><p className="small muted">{profile.coverage.eligible_movies} eligible films; {profile.coverage.rated_movies} with audience evidence; {profile.genre_evidence_movies} in this genre. {profile.genre_catalog_gap?'Genre catalog gap: fit uses a fallback prior.':''} These are game attributes, not professional assessments.</p></>}{films&&<><h3>Full role-specific filmography</h3><p className="small muted">Eligible films in our imported catalog, newest first. This is not a claim of complete career coverage.</p><Works works={films.items} source={card.source}/>{!films.items.length&&<p>No eligible films in this role and dataset.</p>}<div className="studio-actions"><button className="button-secondary" disabled={offset===0||loading} onClick={()=>setOffset(Math.max(0,offset-10))}>Previous films</button><button className="button-secondary" disabled={films.next_offset===null||loading} onClick={()=>setOffset(films.next_offset!)}>Next films</button></div></>}<h3>Shared credits with your roster</h3><p className="small muted">Research only. The score uses twelve designated slot relationships; these counts do not predict personal compatibility.</p>{!members.length?<p>No roster picks yet.</p>:pairs.length?<ul className="evidence-list">{pairs.map((p,i)=><li key={i}><strong>{p.name}</strong><span>{p.text}</span></li>)}</ul>:<p role="status">Loading collaboration evidence…</p>}</Modal>;
}
