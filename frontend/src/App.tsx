import { useCallback, useEffect, useRef, useState } from 'react';
import { fetchStudioHealth, type StudioHealth } from './api';
import TalentLab from './TalentLab';
import CollaborationLab from './CollaborationLab';
import DraftInspector from './DraftInspector';
import Studio from './Studio';
import RoomLobby from './RoomLobby';

export default function App() {
  const [logoFailed, setLogoFailed] = useState(false);
  const [health, setHealth] = useState<StudioHealth | null>(null);
  const [checking, setChecking] = useState(true);
  const [checkedAt, setCheckedAt] = useState<string | null>(null);
  const activeRequest = useRef<AbortController | null>(null);
  const check = useCallback(async () => {
    activeRequest.current?.abort();
    const controller = new AbortController();
    activeRequest.current = controller;
    setChecking(true);
    try {
      const result = await fetchStudioHealth(controller.signal);
      if (!controller.signal.aborted) {
        setHealth(result);
        setCheckedAt(new Date().toLocaleTimeString());
      }
    } catch {
      if (!controller.signal.aborted) {
        setHealth({ api: { status: 'down', message: 'Connection check failed. Please retry.' },
          database: { status: 'down', message: 'Database readiness cannot be confirmed.' } });
      }
    } finally {
      if (!controller.signal.aborted) setChecking(false);
    }
  }, []);

  useEffect(() => { void check(); return () => activeRequest.current?.abort(); }, [check]);
  const fullyReady = health?.api.status === 'up' && health.database.status === 'up';

  return <div className="studio-shell">
    <a className="skip-link" href="#studio">Skip to film studio</a>
    <header className="studio-header"><a href="#studio" className="brand" aria-label="CineDraft home"><span className="brand-mark">CD</span><span>CINE<span className="font-normal text-stone-400">DRAFT</span></span></a><nav aria-label="Main navigation"><a href="#studio">Your studio</a><a href="#rooms">Co-op rooms</a><a href="#tools">Developer tools</a></nav><span className="edition">LOCAL STUDIO / PHASE 15</span></header>
    <main><section className="studio-intro"><div><p className="eyebrow">Classic mode / A film by you</p><h1>Great films start<br/>with <em>great choices.</em></h1><p>Assemble eight creative voices. Make the budget work.<br/>Find out what happens on opening night.</p></div><div className="intro-note"><span>THE PRODUCTION RULES</span><p><strong>08</strong> distinct people</p><p><strong>02</strong> offer rerolls</p><p><strong>01</strong> final recast</p></div></section>
    <Studio/>
    <RoomLobby/>
    <details id="tools" className="developer-tools"><summary>Developer tools · connection, catalogs &amp; inspectors</summary><p className="muted">These learning tools use their own session state. Keep your studio token saved before testing a different session in the draft inspector.</p>
        <section className="status-panel" aria-labelledby="connection-title">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div><p className="eyebrow">Connection diagnostics</p><h2 id="connection-title">Check the foundations.</h2></div>
            <button className="button-secondary" onClick={() => void check()} disabled={checking}>{checking ? 'Checking services…' : 'Check connection'}</button>
          </div>
          <div className="mt-6 grid gap-4 sm:grid-cols-2" aria-live="polite" aria-busy={checking}>
            {(['api', 'database'] as const).map(key => {
              const item = health?.[key];
              return <article key={key} className="service-card">
                <div className="flex items-center justify-between gap-4"><h3>{key === 'api' ? 'Application API' : 'PostgreSQL database'}</h3><span className={`service-tag ${!checking && item?.status === 'up' ? 'connected' : ''}`}>{checking ? 'Checking' : item?.status === 'up' ? 'Connected' : 'Unavailable'}</span></div>
                <p>{checking ? 'Waiting for the local service…' : item?.message}</p>
              </article>;
            })}
          </div>
          <p className="mt-4 text-sm text-stone-400" role="status">{checking ? 'Running a fresh health check.' : fullyReady ? 'Both services are connected. Your local API and database are reachable.' : 'A service needs attention. The original prototype can still run independently.'}{checkedAt && !checking ? ` Last checked ${checkedAt}.` : ''}</p>
        </section>

    <TalentLab/><CollaborationLab/><DraftInspector/><div className="studio-actions"><a className="button-secondary" href="/api/docs" target="_blank" rel="noreferrer">API documentation ↗</a><a className="button-secondary" href={import.meta.env.VITE_LEGACY_URL || 'http://127.0.0.1:5500'}>Original prototype ↗</a></div></details>
        <section className="border-t border-white/10 py-8" aria-labelledby="credits-title">
          <h2 id="credits-title">About &amp; credits</h2>
          <a className="mt-4 inline-block" href="https://www.themoviedb.org" target="_blank" rel="noreferrer">
            {logoFailed ? <strong>TMDB</strong> : <img onError={()=>setLogoFailed(true)} width="96" className="h-auto" alt="TMDB" src="https://www.themoviedb.org/assets/2/v4/logos/v2/blue_short-8e7b30f73a4020692ccca9c88bafe5dcb6f8a62a4c6bc55cd9ba82bb2cd95f6c.svg" />}
          </a>
          <p className="mt-3 text-sm text-stone-400">This product uses the TMDB API but is not endorsed or certified by TMDB.</p>
          <p className="mt-2 text-sm text-stone-400">Imported movie facts and audience ratings come from TMDB. Game hiring fees and simulated outcomes are fictional. Synthetic test records are labeled separately.</p>
        </section>
    </main><footer className="studio-footer"><span>INDEPENDENT SPIRIT. IMPOSSIBLE CASTS.</span><span>Phase 15 · Local development · Fictional game economics</span></footer></div>;
}
