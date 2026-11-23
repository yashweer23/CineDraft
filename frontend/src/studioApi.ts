import {useEffect,useRef,useState,useCallback} from 'react';
import type {Draft} from './DraftInspector';
export type Work={movie_id:string;title:string;year?:number|null;release_date?:string|null;credited_jobs:string[];poster_url?:string|null;audience_rating?:number|null};
export type Card={person_id:string;name:string;role:string;hiring_fee_usd:number;source:string;talent_strength:number|null;genre_fit:number|null;coverage:string;specialties?:string[];notable_works:(Work&{year:number|null})[];versions?:{dataset_id:string;pricing_id:string;graph_id:string}};
export type Candidate={card:Card;selectable:boolean;blocked_reason:string|null};
export type Member={slot:string;locked_fee_usd:number;card:Card};
export type Roster={draft_id:string;revision:number;members:Member[]};
export type Catalog={catalog_id:string;synthetic:boolean;tiers:{tier:string;total_budget_usd:number;talent_budget_usd:number;enabled:boolean;reason:string|null}[]};
export type Pending={path:string;body:Record<string,unknown>};
export type Account={account_id:string;username:string};
export type Challenge={challenge_id:string;opens_at:string;closes_at:string;timezone:string;status:'scheduled'|'open'|'closed';genre_id:string;tier:string;catalog_id:string;config_hash:string;seed_commitment:string;configuration:Record<string,unknown>;results_hidden:boolean;synthetic:boolean};
export type ChallengeContext={challenge:Challenge|null;submitted:boolean};
type Page={items:Draft[];next_offset:number|null};
export class ApiError extends Error{constructor(message:string,readonly uncertain=false,readonly status=0,readonly code=''){super(message);}}
export async function api<T>(path:string,token='',body?:Record<string,unknown>,signal?:AbortSignal):Promise<T>{
 const response=await fetch(path,{method:body?'POST':'GET',cache:'no-store',signal:signal?AbortSignal.any([signal,AbortSignal.timeout(20000)]):AbortSignal.timeout(20000),headers:{...(token?{Authorization:'Bearer '+token}:{}),...(body?{'Content-Type':'application/json'}:{})},...(body?{body:JSON.stringify(body)}:{})}).catch(()=>{throw new ApiError('Connection interrupted. Your last saved state is still shown.',!!body);});
 const value=await response.json().catch(()=>null);
 if(!response.ok)throw new ApiError(value?.error?.message??`The API returned ${response.status}. Check the connection and migration.`,!!body&&(response.status>=500||response.status===408),response.status,value?.error?.code??'');
 if(!value)throw new ApiError('The API response could not be read.',!!body);
 return value as T;
}
export function useStudio(){
 const [catalog,setCatalog]=useState<Catalog|null>(null),[catalogError,setCatalogError]=useState('');
 const [account,setAccount]=useState<Account|null>(null),[challengeContext,setChallengeContext]=useState<ChallengeContext|null>(null);
 const [token,setToken]=useState(''),[expires,setExpires]=useState('');
 const [draft,setDraft]=useState<Draft|null>(null),[roster,setRoster]=useState<Roster|null>(null),[page,setPage]=useState<Page|null>(null);
 const [busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState(''),[pending,setPending]=useState<Pending|null>(null),[mustRefresh,setMustRefresh]=useState(false);
 const [labBusy,setLabBusy]=useState(false);const labGuard=useRef(false);
 const setLabLock=useCallback((value:boolean)=>{labGuard.current=value;setLabBusy(value);},[]);
 const guard=useRef(false),alive=useRef(true),controller=useRef<AbortController|null>(null),catalogController=useRef<AbortController|null>(null);
 useEffect(()=>{alive.current=true;return()=>{alive.current=false;controller.current?.abort();catalogController.current?.abort();};},[]);
 useEffect(()=>{if(!pending)return;const warn=(e:BeforeUnloadEvent)=>{e.preventDefault();e.returnValue='';};window.addEventListener('beforeunload',warn);return()=>window.removeEventListener('beforeunload',warn);},[pending]);
 async function loadCatalog(){
  catalogController.current?.abort();const control=new AbortController();catalogController.current=control;setCatalogError('');
  try{const c=await api<Catalog>('/api/v1/catalog','',undefined,control.signal);if(!Array.isArray(c.tiers))throw new Error('No compatible draft catalog. Follow the README setup steps.');if(alive.current&&!control.signal.aborted)setCatalog(c);}
  catch(e){if(alive.current&&!control.signal.aborted)setCatalogError((e as Error).message);}
 }
 useEffect(()=>{void loadCatalog();},[]);
 async function run(work:(signal:AbortSignal)=>Promise<void>){
  if(guard.current||labGuard.current)return;guard.current=true;const c=new AbortController();controller.current=c;setBusy(true);setError('');setNotice('');
  try{await work(c.signal);}catch(e){if(alive.current)setError((e as Error).message);}
  finally{guard.current=false;if(alive.current)setBusy(false);}
 }
 // A mutation receipt may be older than another tab. Fetch current draft + matching roster
 // before enabling writes, even after a successful replay. Never turn a failed read into a new POST.
 async function current(id:string,cap:string,signal:AbortSignal){
  setMustRefresh(true);setRoster(null);setChallengeContext(null);
  const d=await api<Draft>('/api/v1/drafts/'+id,cap,undefined,signal);if(!alive.current)return;
  setDraft(d);
  const r=await api<Roster>('/api/v1/drafts/'+id+'/roster',cap,undefined,signal);if(!alive.current)return;
  if(r.draft_id!==id||r.revision!==d.revision)throw new Error('Another tab changed this draft. Refresh draft to load a consistent roster.');
  const context=await api<ChallengeContext>('/api/v1/drafts/'+id+'/challenge',cap,undefined,signal);if(!alive.current)return;
  if(!('challenge' in context)||typeof context.submitted!=='boolean')throw new Error('Update the API to Phase 10 and refresh this draft.');
  setChallengeContext(context);setRoster(r);setMustRefresh(false);
 }
 async function session(value?:string){
  if(pending)return;
  await run(async signal=>{
   if(value!==undefined){const cap=value.trim();if(!/^[A-Za-z0-9_-]{43}$/.test(cap))throw new Error('Enter the complete 43-character recovery token.');const p=await api<Page>('/api/v1/drafts?limit=5',cap,undefined,signal);if(!alive.current)return;setToken(cap);setExpires('');setPage(p);setNotice('Session restored. Open one of your saved films.');}
   else{const s=await api<{access_token:string;expires_at:string}>('/api/v1/sessions','',{},signal);if(!alive.current)return;setToken(s.access_token);setExpires(s.expires_at);setNotice('Save your recovery token privately before starting.');}
  });
 }
 async function list(offset=0){await run(async signal=>{const p=await api<Page>(`/api/v1/drafts?limit=5&offset=${offset}`,token,undefined,signal);if(alive.current)setPage(old=>offset?{items:[...(old?.items??[]),...p.items],next_offset:p.next_offset}:p);});}
 async function open(id:string){if(pending)return;await run(signal=>current(id,token,signal));}
 async function send(p:Pending){
  await run(async signal=>{
   let reply:Draft|{draft:Draft};
   try{reply=await api(p.path,token,p.body,signal);if(!reply||!('draft_id' in reply||'draft' in reply))throw new ApiError('The action response could not be read.',true);}
   catch(e){if(alive.current){setPending(e instanceof ApiError&&e.uncertain?p:null);if(e instanceof ApiError&&e.status===409)setMustRefresh(true);}throw e;}
   if(!alive.current)return;const receipt='draft' in reply?reply.draft:reply;setPending(null);setMustRefresh(true);
   setDraft(old=>old?.draft_id===receipt.draft_id&&old.revision>receipt.revision?old:receipt);
   setNotice('Action recorded. Loading the current saved state…');
   await current(receipt.draft_id,token,signal);
   if(alive.current)setNotice('Saved. Your roster and budget are up to date.');
  });
 }
 function act(command:string,fields:Record<string,unknown>={}){if(!draft||pending||mustRefresh||guard.current||labGuard.current||(command!=='abandon'&&challengeContext?.challenge?.status==='closed'))return;void send({path:`/api/v1/drafts/${draft.draft_id}/${command}`,body:{request_id:crypto.randomUUID(),expected_revision:draft.revision,...fields}});}
 function create(genre:string,tier:string){if(pending||guard.current||labGuard.current)return;void send({path:'/api/v1/drafts',body:{request_id:crypto.randomUUID(),mode:'classic',genre_id:genre,tier}});}
 function clearDraft(){if(pending||guard.current||labGuard.current)return;setDraft(null);setRoster(null);setChallengeContext(null);setMustRefresh(false);setError('');setNotice('Previous films remain saved in this session.');}
 function forget(){if(pending||guard.current||labGuard.current)return;setAccount(null);setChallengeContext(null);setToken('');setExpires('');setDraft(null);setRoster(null);setPage(null);setMustRefresh(false);setError('');setNotice('Session closed on this screen. Restore it with your saved token.');}
 async function signIn(kind:'login'|'register',username:string,password:string){
  if(pending||guard.current||labGuard.current)return;
  await run(async signal=>{
   let value:{access_token:string;expires_at:string;account:Account};
   try{value=await api('/api/v1/accounts/'+kind,'',{username,password},signal);}
   catch(e){if(e instanceof ApiError&&e.uncertain)throw new Error('The account response was interrupted. Try signing in with the same username and password; registration may have completed.');throw e;}
   if(!alive.current)return;setToken(value.access_token);setExpires(value.expires_at);setAccount(value.account);setDraft(null);setRoster(null);setChallengeContext(null);setPage(null);setMustRefresh(false);setNotice('Signed in. Your session stays in this tab until you sign out or it expires.');
  });
 }
 async function accountAction(kind:'logout'|'claim-guest'|'password',body:Record<string,unknown>={}){
  if(pending||guard.current||labGuard.current)return;
  await run(async signal=>{
   try{const result=await api<{films?:number}>('/api/v1/accounts/'+kind,token,body,signal);
    if(!alive.current)return;
    if(kind==='claim-guest'){setNotice(`Claimed ${result.films??0} film(s). The old guest token is now revoked. Load my films to see them.`);return;}
   }catch(e){
    if(kind==='claim-guest'||(kind==='password'&&e instanceof ApiError&&e.code==='invalid_credentials'))throw e;
    if(!(e instanceof ApiError&&e.uncertain)&&!(e instanceof ApiError&&e.status===401))throw e;
    setNotice(kind==='password'?'Session cleared. Sign in with the new password; if the request did not complete, the old password still works.':'Session cleared on this screen. Sign-out could not be confirmed; the server session expires within eight hours.');
    setAccount(null);setToken('');setExpires('');setDraft(null);setRoster(null);setPage(null);setChallengeContext(null);setMustRefresh(false);return;
   }
   setAccount(null);setToken('');setExpires('');setDraft(null);setRoster(null);setPage(null);setChallengeContext(null);setMustRefresh(false);setNotice(kind==='password'?'Password changed. All account sessions were revoked. Sign in again.':'Signed out.');
  });
 }
 function startChallenge(id:string){if(!account||pending||guard.current||labGuard.current)return;void send({path:`/api/v1/challenges/${encodeURIComponent(id)}/attempts`,body:{request_id:crypto.randomUUID()}});}
 async function resumeChallenge(id:string){if(!account||pending||guard.current||labGuard.current)return;await run(async signal=>{const mine=await api<{draft_id:string|null}>(`/api/v1/challenges/${encodeURIComponent(id)}/mine`,token,undefined,signal);if(mine.draft_id)await current(mine.draft_id,token,signal);else setNotice('You have not started this challenge yet.');});}
 function startReplay(){if(!draft||draft.status!=='results_available'||!challengeContext||challengeContext.challenge?.results_hidden||pending||mustRefresh||guard.current||labGuard.current)return;void send({path:`/api/v1/drafts/${draft.draft_id}/replay`,body:{request_id:crypto.randomUUID()}});}
 async function exportEvents(){if(!draft||!challengeContext||challengeContext.challenge?.results_hidden||pending||mustRefresh)return;
  await run(async signal=>{const data=await api<{schema_version:string;session_key:string}>(`/api/v1/drafts/${draft.draft_id}/analytics-events`,token,undefined,signal);
   if(data.schema_version!=='gameplay-events-1.0'||!/^[a-f0-9]{64}$/.test(data.session_key))throw new Error('Update the API to Phase 12 and retry the export.');
   const href=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));const link=document.createElement('a');link.href=href;link.download=`gameplay-${data.session_key.slice(0,12)}.json`;document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(href),1000);setNotice('Gameplay events exported. Use the Phase 12 README to build your local dashboard.');});
 }
 const challengeClosed=challengeContext?.challenge?.status==='closed';
 return {startReplay,exportEvents,catalog,catalogError,loadCatalog,token,expires,account,challengeContext,challengeClosed,draft,roster,page,busy:busy||labBusy,studioBusy:busy,setLabLock,error,notice,pending,mustRefresh,locked:busy||labBusy||!!pending||mustRefresh||challengeClosed,session,list,open,send,act,create,clearDraft,forget,signIn,accountAction,startChallenge,resumeChallenge};
}
export type StudioState=ReturnType<typeof useStudio>;
