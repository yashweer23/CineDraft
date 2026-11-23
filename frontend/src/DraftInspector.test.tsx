import {render,screen,waitFor} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {afterEach,expect,it,vi} from 'vitest';
import DraftInspector,{type Draft} from './DraftInspector';
afterEach(()=>vi.unstubAllGlobals());
const token='t'.repeat(43);
const catalog={catalog_id:'draft-catalog:test',dataset_id:'fixture:test',synthetic:true,tiers:[{tier:'indie',talent_budget_usd:6500000,enabled:false,minimum_cost_usd:7000000,reason:'The cheapest complete roster exceeds this talent budget.'},{tier:'studio',talent_budget_usd:32500000,enabled:true,minimum_cost_usd:7000000,reason:null}]};
const candidate=(id:string,selectable=true)=>({card:{person_id:id,name:'Synthetic '+id,role:'director',hiring_fee_usd:150000,source:'fixture',talent_strength:55,genre_fit:60,coverage:'low: 1 eligible films',notable_works:[{movie_id:'film',title:'Synthetic film',year:null,credited_jobs:['Director']}]},selectable,blocked_reason:selectable?null:'The remaining roles cannot be completed within the talent budget.'});
const draft:Draft={draft_id:'draft-id',status:'awaiting_pick',genre_id:'drama',revision:0,synthetic:true,budget:{talent_budget_usd:32500000,talent_spend_usd:0,talent_remaining_usd:32500000,reserve_usd:17500000},picks:[],current_offer:{offer_id:'offer-id',slot:'director',kind:'pick',generated_at_revision:0,shortage_message:'Only 2 alternatives in this frozen role pool.',candidates:[candidate('A'),candidate('B',false)]},rerolls_used:0,recasts_used:0,can_reroll:true,reroll_unavailable_reason:null,minimum_remaining_cost_usd:7000000,snapshot_hash:null,versions:{catalog_id:'draft-catalog:test',graph_id:'graph:test'}};
function response(value:unknown,status=200){return new Response(JSON.stringify(value),{status});}
function basic(url:string,init?:RequestInit){
 if(url.endsWith('/catalog'))return response(catalog);
 if(url.endsWith('/sessions'))return response({access_token:token,expires_at:'2030-01-01T00:00:00Z'});
 if(url.includes('/drafts?')||url.endsWith('/drafts')&&init?.method==='GET')return response({items:[draft],next_offset:null});
 return response(draft);
}
async function start(){render(<DraftInspector/>);await userEvent.click(screen.getByRole('button',{name:'Load draft catalog'}));await userEvent.click(screen.getByRole('button',{name:'Create guest session'}));await userEvent.click(await screen.findByRole('button',{name:'Start draft'}));await screen.findByRole('button',{name:'Pick Synthetic A'});}
it('only enables feasible tiers, sends capability header and no client prices or seed',async()=>{
 const fetch=vi.fn(async(url:string,init?:RequestInit)=>basic(url,init));vi.stubGlobal('fetch',fetch);
 const local=vi.spyOn(Storage.prototype,'setItem');await start();
 expect(screen.getByRole('option',{name:'indie (unavailable)'})).toBeDisabled();
 expect(screen.getByRole('button',{name:'Pick Synthetic B'})).toBeDisabled();
 expect(screen.getByLabelText('Your recovery token')).toHaveAttribute('type','password');expect(local).not.toHaveBeenCalled();
 const creation=fetch.mock.calls.find(([u,i])=>u.endsWith('/drafts')&&i?.method==='POST')!;
 expect(creation[1]?.headers).toMatchObject({Authorization:'Bearer '+token});
 expect(Object.keys(JSON.parse(String(creation[1]?.body))).sort()).toEqual(['genre_id','mode','request_id','tier']);
 expect(JSON.parse(String(creation[1]?.body)).tier).toBe('studio');
 local.mockRestore();
});
it('keeps uncertain action and retries exactly the same request ID and body',async()=>{
 let failed=true;const fetch=vi.fn(async(url:string,init?:RequestInit)=>url.endsWith('/picks')&&failed?response({error:{message:'Database unavailable'}},503):basic(url,init));vi.stubGlobal('fetch',fetch);await start();
 await userEvent.click(screen.getByRole('button',{name:'Pick Synthetic A'}));
 expect(await screen.findByRole('alert')).toHaveTextContent('Database unavailable');
 expect(screen.getByRole('button',{name:'Pick Synthetic A'})).toBeDisabled();
 failed=false;await userEvent.click(screen.getByRole('button',{name:'Retry same request'}));
 await waitFor(()=>expect(screen.queryByRole('button',{name:'Retry same request'})).not.toBeInTheDocument());
 const calls=fetch.mock.calls.filter(([u])=>u.endsWith('/picks'));expect(calls).toHaveLength(2);expect(calls[0][1]?.body).toBe(calls[1][1]?.body);
 expect(Object.keys(JSON.parse(String(calls[0][1]?.body))).sort()).toEqual(['expected_revision','offer_id','person_id','request_id']);
});
it('also preserves the request after an unreadable successful response',async()=>{
 vi.stubGlobal('fetch',vi.fn(async(url:string,init?:RequestInit)=>url.endsWith('/picks')?new Response('<html>not API</html>'):basic(url,init)));await start();
 await userEvent.click(screen.getByRole('button',{name:'Pick Synthetic A'}));
 expect(await screen.findByRole('button',{name:'Retry same request'})).toBeInTheDocument();
});
it('surfaces stale revision, refreshes current state and uses the new revision',async()=>{
 let revision=0;const fetch=vi.fn(async(url:string,init?:RequestInit)=>{
  if(url.endsWith('/picks')){revision=2;return response({error:{message:'Draft changed. Refresh before trying a new action.'}},409);}
  if(url.endsWith('/drafts/draft-id')&&init?.method==='GET')return response({...draft,revision});
  return basic(url,init);
 });vi.stubGlobal('fetch',fetch);await start();await userEvent.click(screen.getByRole('button',{name:'Pick Synthetic A'}));
 expect(await screen.findByRole('alert')).toHaveTextContent('Draft changed');expect(screen.queryByRole('button',{name:'Retry same request'})).not.toBeInTheDocument();
 await userEvent.click(screen.getByRole('button',{name:'Refresh draft'}));await screen.findByText(/Revision 2/);
 await userEvent.click(screen.getByRole('button',{name:'Pick Synthetic A'}));
 const bodies=fetch.mock.calls.filter(([u])=>u.endsWith('/picks')).map(([,i])=>JSON.parse(String(i?.body)));
 expect(bodies.map(b=>b.expected_revision)).toEqual([0,2]);expect(bodies[0].request_id).not.toBe(bodies[1].request_id);
});
it('restores session, lists drafts and resumes saved server state',async()=>{
 const fetch=vi.fn(async(url:string,init?:RequestInit)=>basic(url,init));vi.stubGlobal('fetch',fetch);render(<DraftInspector/>);
 await userEvent.type(screen.getByLabelText('Recovery token'),token);await userEvent.click(screen.getByRole('button',{name:'Restore session'}));
 await userEvent.click(await screen.findByRole('button',{name:/Open draft-id/}));
 expect(await screen.findByRole('button',{name:'Pick Synthetic A'})).toBeInTheDocument();
 expect(fetch.mock.calls.every(([,i])=>(i?.headers as Record<string,string>).Authorization==='Bearer '+token)).toBe(true);
});
it('renders exhausted rerolls and requires confirmation before abandoning',async()=>{
 const fetch=vi.fn(async(url:string,init?:RequestInit)=>url.endsWith('/drafts')&&init?.method==='POST'?response({...draft,can_reroll:false,rerolls_used:2,reroll_unavailable_reason:'Both offer rerolls have been used.'}):basic(url,init));vi.stubGlobal('fetch',fetch);await start();
 expect(screen.getByRole('button',{name:'Reroll this offer'})).toBeDisabled();
 await userEvent.click(screen.getByRole('button',{name:'Abandon draft…'}));expect(fetch.mock.calls.some(([u])=>u.endsWith('/abandon'))).toBe(false);
 await userEvent.click(screen.getByRole('button',{name:'Keep draft'}));expect(screen.queryByRole('button',{name:'Confirm abandon'})).not.toBeInTheDocument();
 await userEvent.click(screen.getByRole('button',{name:'Abandon draft…'}));await userEvent.click(screen.getByRole('button',{name:'Confirm abandon'}));expect(fetch.mock.calls.some(([u])=>u.endsWith('/abandon'))).toBe(true);
});
it('closes recast preview before finalization and displays the frozen hash',async()=>{
 const roster=['director','lead','co_lead','supporting_1','supporting_2','writer','cinematographer','composer'].map((slot,i)=>({slot,person_id:'p'+i,locked_fee_usd:100000,offer_id:'o'+i}));
 let current:Draft={...draft,status:'recast_available',revision:8,picks:roster,current_offer:null};
 vi.stubGlobal('fetch',vi.fn(async(url:string,init?:RequestInit)=>{
  if(url.endsWith('/recast/preview'))current={...current,status:'recast_preview',revision:9,current_offer:{...draft.current_offer!,kind:'recast'}};
  if(url.endsWith('/recast/cancel'))current={...current,status:'recast_available',revision:10,current_offer:null};
  if(url.endsWith('/finalize'))current={...current,status:'production_finalized',revision:11,snapshot_hash:'a'.repeat(64)};
  if(url.includes('/drafts'))return response(current);return basic(url,init);
 }));render(<DraftInspector/>);await userEvent.click(screen.getByRole('button',{name:'Load draft catalog'}));await userEvent.click(screen.getByRole('button',{name:'Create guest session'}));await userEvent.click(await screen.findByRole('button',{name:'Start draft'}));
 await userEvent.click(await screen.findByRole('button',{name:'Preview recast'}));
 expect(await screen.findByRole('button',{name:'Cancel recast preview'})).toBeInTheDocument();expect(screen.queryByRole('button',{name:'Finalize production'})).not.toBeInTheDocument();
 await userEvent.click(screen.getByRole('button',{name:'Cancel recast preview'}));await userEvent.click(await screen.findByRole('button',{name:'Finalize production'}));
 expect(await screen.findByText(/Snapshot SHA-256: aaaa/)).toBeInTheDocument();expect(screen.getByText(/Production inputs are frozen/)).toBeInTheDocument();
});
it('reports a missing catalog without inventing playable tiers',async()=>{
 vi.stubGlobal('fetch',vi.fn(async()=>response({error:{message:'Prepare and activate a compatible drafting catalog from the Phase 7 README.'}},503)));render(<DraftInspector/>);await userEvent.click(screen.getByRole('button',{name:'Load draft catalog'}));
 expect(await screen.findByRole('alert')).toHaveTextContent('Prepare and activate');expect(screen.queryByLabelText('Draft budget')).not.toBeInTheDocument();
});
it('retries an uncertain release with the same command and unwraps its receipt',async()=>{
 let current:Draft={...draft,status:'production_finalized',revision:9,current_offer:null,snapshot_hash:'a'.repeat(64)};let fail=true;
 const request=vi.fn(async(url:string,init?:RequestInit)=>{
  if(url.endsWith('/simulation'))return response({status:current.status,latest_attempt:null,result_available:false});
  if(url.endsWith('/release')){if(fail)return response({error:{message:'Connection outcome uncertain'}},503);current={...current,status:'results_available',revision:10};return response({draft:current,attempt:{status:'succeeded',attempt_number:1}});}
  if(url.includes('/drafts'))return response(current);return basic(url,init);
 });vi.stubGlobal('fetch',request);render(<DraftInspector/>);
 await userEvent.click(screen.getByRole('button',{name:'Load draft catalog'}));await userEvent.click(screen.getByRole('button',{name:'Create guest session'}));await userEvent.click(await screen.findByRole('button',{name:'Start draft'}));
 await waitFor(()=>expect(screen.getByRole('button',{name:'Run release simulation'})).toBeEnabled());await userEvent.click(screen.getByRole('button',{name:'Run release simulation'}));
 const retry=await screen.findByRole('button',{name:'Retry same request'});fail=false;await userEvent.click(retry);
 expect(await screen.findByText(/Revision 10/)).toBeInTheDocument();
 const calls=request.mock.calls.filter(([url])=>url.endsWith('/release'));expect(calls).toHaveLength(2);expect(calls[0][1]?.body).toBe(calls[1][1]?.body);
 expect(Object.keys(JSON.parse(String(calls[0][1]?.body))).sort()).toEqual(['expected_revision','request_id']);
});
