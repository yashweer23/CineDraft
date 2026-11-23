import { useEffect, useState } from 'react';

type Version = { pricing_id: string; dataset_id: string; source: string };
type Work = { movie_id: string; title: string; year: number | null; poster_url: string | null; audience_rating: number | null; credited_jobs: string[]; rank: number };
type Profile = { person_id: string; name: string; source: string; role: string; profile_url: string | null; hiring_fee_usd: number;
  talent_strength: number; genre_fit: number; genre_evidence_movies: number; genre_catalog_gap: boolean;
  coverage: { level: string; eligible_movies: number; rated_movies: number; reception_prior_only: boolean };
  notable_works: Work[] };
const roles = [['director','Director'],['actor','Actor'],['writer','Screenwriter'],['cinematographer','Cinematographer'],['composer','Composer']];
const genres = ['action','adventure','comedy','crime','drama','horror','mystery','romance','science_fiction','thriller'];
const usd = new Intl.NumberFormat('en-US', { style:'currency', currency:'USD', maximumFractionDigits:0 });

async function page<T>(url: string, signal?: AbortSignal): Promise<{ items:T[]; next_offset:number|null }> {
  const response = await fetch(url, { signal: signal ? AbortSignal.any([signal, AbortSignal.timeout(10000)]) : AbortSignal.timeout(10000) });
  if (!response.ok) throw new Error('Catalog unavailable. Check the API connection and database migration.');
  const body = await response.json();
  if (!Array.isArray(body.items) || !(body.next_offset === null || Number.isInteger(body.next_offset))) throw new Error('Unexpected catalog response. Check that the Phase 5 backend is running.');
  return body;
}

function SourceImage({ url, alt, portrait = false }: { url:string|null; alt:string; portrait?:boolean }) {
  const [failed, setFailed] = useState(false);
  useEffect(() => setFailed(false), [url]);
  const cls = portrait ? 'h-14 w-14 rounded-full object-cover' : 'h-14 w-10 rounded object-cover';
  return url && !failed ? <img className={cls} src={url} alt={alt} loading="lazy" onError={() => setFailed(true)} />
    : <span className={`${cls} flex shrink-0 items-center justify-center bg-white/5 text-[10px] text-stone-500`} aria-label={`${alt}: image unavailable`}>No image</span>;
}

export default function TalentLab() {
  const [versions,setVersions] = useState<Version[]>([]);
  const [version,setVersion] = useState('');
  const [versionNext,setVersionNext] = useState<number|null>(null);
  const [role,setRole] = useState('director');
  const [genre,setGenre] = useState('drama');
  const [offset,setOffset] = useState(0);
  const [items,setItems] = useState<Profile[]>([]);
  const [next,setNext] = useState<number|null>(null);
  const [loaded,setLoaded] = useState(false);
  const [loadingVersions,setLoadingVersions] = useState(false);
  const [loading,setLoading] = useState(false);
  const [error,setError] = useState('');
  const [versionError,setVersionError] = useState('');
  const [refresh,setRefresh] = useState(0);
  async function loadVersions(start=0) {
    setLoadingVersions(true);setVersionError('');
    try {
      const result = await page<Version>(`/api/talent/versions?limit=50&offset=${start}`);
      setVersions(old => start ? [...old, ...result.items] : result.items);
      setVersionNext(result.next_offset);setLoaded(true);
      if (!start) { setVersion(old => result.items.some(v=>v.pricing_id===old) ? old : result.items[0]?.pricing_id || ''); setOffset(0);setRefresh(n=>n+1); }
    } catch (e) { setVersionError(e instanceof Error ? e.message : 'Could not load the catalog.'); }
    finally { setLoadingVersions(false); }
  }
  useEffect(() => {
    if (!version) {setItems([]);return;}
    const controller = new AbortController();setLoading(true);setError('');
    page<Profile>(`/api/talent/${encodeURIComponent(version)}/profiles?role=${role}&genre=${genre}&limit=6&offset=${offset}`,controller.signal)
      .then(result => { if (!controller.signal.aborted) {setItems(result.items);setNext(result.next_offset);} })
      .catch(e => {if (!controller.signal.aborted) {setItems([]);setError(e instanceof Error ? e.message : 'Could not load profiles.');}})
      .finally(() => {if (!controller.signal.aborted) setLoading(false);});
    return () => controller.abort();
  },[version,role,genre,offset,refresh]);
  return <section className="border-t border-white/10 py-12" aria-labelledby="talent-title">
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div><p className="eyebrow">03 / Talent lab</p><h2 id="talent-title">Know who you’re hiring.</h2>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-stone-400">Explore published ratings, fictional fees and verified films from your imported catalog. This research view is separate from the guided studio above.</p></div>
      <button className="button-secondary" disabled={loadingVersions} onClick={()=>void loadVersions()}>{loadingVersions ? 'Loading catalog…' : loaded ? 'Refresh talent catalog' : 'Load talent catalog'}</button>
    </div>
    {versionError && <p role="alert" className="mt-4 text-amber-300">{versionError}</p>}
    {loaded && !versions.length && <p role="status" className="mt-5 text-stone-400">No published talent builds yet. Follow the Phase 5 README to build ratings from a sealed dataset, then refresh here.</p>}
    {!!versions.length && <>
      <div className="my-6 grid gap-4 sm:grid-cols-3">
        <label className="text-sm text-stone-300">Published version<select className="mt-2 w-full rounded border border-white/15 bg-stone-950 p-3" value={version} onChange={e=>{setVersion(e.target.value);setOffset(0);}}>{versions.map(v=><option key={v.pricing_id} value={v.pricing_id}>{v.pricing_id} ({v.source})</option>)}</select></label>
        <label className="text-sm text-stone-300">Professional role<select className="mt-2 w-full rounded border border-white/15 bg-stone-950 p-3" value={role} onChange={e=>{setRole(e.target.value);setOffset(0);}}>{roles.map(([id,label])=><option key={id} value={id}>{label}</option>)}</select></label>
        <label className="text-sm text-stone-300">Genre fit<select className="mt-2 w-full rounded border border-white/15 bg-stone-950 p-3" value={genre} onChange={e=>{setGenre(e.target.value);setOffset(0);}}>{genres.map(g=><option key={g} value={g}>{g.replaceAll('_',' ')}</option>)}</select></label>
      </div>
      {versionNext!==null && <button className="button-secondary mb-4" disabled={loadingVersions} onClick={()=>void loadVersions(versionNext)}>Load more versions</button>}
      <p className="mb-5 text-xs text-stone-500">Dataset: {versions.find(v=>v.pricing_id===version)?.dataset_id}. Fees stay the same across genres and production tiers.</p>
      {loading ? <p role="status">Loading profiles…</p> : error ? <div role="alert"><p className="text-amber-300">{error}</p><button className="button-secondary mt-3" onClick={()=>setRefresh(n=>n+1)}>Retry profiles</button></div> : <>
        {!items.length && <p role="status" className="text-stone-400">No verified profiles for this role in this version.</p>}
        <div className="grid items-start gap-5 md:grid-cols-2 xl:grid-cols-3">{items.map(p=><article key={p.person_id} className="rounded-xl border border-white/10 bg-white/[.02] p-5">
          <div className="flex items-center gap-3"><SourceImage url={p.profile_url} alt={p.name} portrait/><div><h3 className="text-lg font-semibold">{p.name}</h3><p className="text-xs text-stone-400">{p.role} · {p.source==='fixture' ? 'Synthetic fixture' : 'TMDB catalog'}</p></div></div>
          <p className="mt-5 text-2xl font-semibold">{usd.format(p.hiring_fee_usd)}</p><p className="text-xs text-stone-500">Fictional game hiring fee · USD</p>
          <dl className="my-5 grid grid-cols-2 gap-3 text-sm"><div><dt className="text-stone-400">Game talent strength</dt><dd className="mt-1 text-xl">{p.talent_strength.toFixed(1)}<span className="text-xs text-stone-500"> / 100</span></dd></div><div><dt className="text-stone-400">Genre exposure fit</dt><dd className="mt-1 text-xl">{p.genre_fit.toFixed(1)}<span className="text-xs text-stone-500"> / 100</span></dd></div></dl>
          <p className="text-xs leading-relaxed text-stone-400">{p.coverage.level} coverage · {p.coverage.eligible_movies} eligible films · {p.coverage.rated_movies} with audience evidence.</p>
          {p.coverage.reception_prior_only && <p className="mt-2 text-xs text-amber-300">No rated-film evidence; reception uses the catalog prior.</p>}
          {p.genre_catalog_gap && <p className="mt-2 text-xs text-amber-300">Catalog gap for this role and genre; fit uses a fallback prior.</p>}
          <h4 className="mb-3 mt-6 text-sm font-semibold">Notable films · from our catalog</h4>
          <ol className="space-y-3">{p.notable_works.map(w=><li key={w.movie_id} className="flex gap-3"><SourceImage url={w.poster_url} alt={`${w.title} poster`}/><div className="min-w-0"><p className="text-sm">{w.rank}. {w.title} <span className="text-stone-500">({w.year ?? 'Year unavailable'})</span></p><p className="mt-1 text-xs text-stone-400">{w.credited_jobs.join(' / ')}</p><p className="text-xs text-stone-500">{w.audience_rating===null ? 'No audience rating' : `${p.source==='fixture' ? 'Synthetic' : 'TMDB'} audience: ${w.audience_rating.toFixed(1)} / 10`}</p></div></li>)}</ol>
          <p className="mt-3 text-xs text-stone-500">{p.notable_works.length ? `${p.notable_works.length} verified films shown` : 'Filmography unavailable'}</p>
          <a className="mt-5 inline-block text-sm text-amber-200 underline underline-offset-4" href={`/api/talent/${encodeURIComponent(version)}/profiles/${p.person_id}/${p.role}?genre=${genre}`} target="_blank" rel="noreferrer">View calculation evidence ↗</a>
        </article>)}</div>
        <div className="mt-6 flex gap-3"><button className="button-secondary" disabled={offset===0} onClick={()=>setOffset(Math.max(0,offset-6))}>Previous profiles</button><button className="button-secondary" disabled={next===null} onClick={()=>{if(next!==null)setOffset(next);}}>Next profiles</button></div>
      </>}
    </>}
  </section>;
}
