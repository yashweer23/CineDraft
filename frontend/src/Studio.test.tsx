import {render,screen,within,waitFor,fireEvent} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {afterEach,expect,it,vi} from 'vitest';
import Studio from './Studio';
import {slots} from './StudioParts';
import type {Draft} from './DraftInspector';
import type {Card,Member} from './studioApi';
import example from '../../data/phase8-simulation-example.json';
afterEach(()=>vi.unstubAllGlobals());
const token='p'.repeat(43),id='11111111-1111-4111-8111-111111111111';
const catalog={catalog_id:'draft:test',synthetic:true,tiers:[{tier:'indie',total_budget_usd:10000000,talent_budget_usd:6500000,enabled:false,reason:'Not enough affordable distinct people.'},{tier:'studio',total_budget_usd:50000000,talent_budget_usd:32500000,enabled:true,reason:null}]};
const card=(slot:string,n=0):Card=>({person_id:slot+'-'+n,name:`Practice ${slot} ${n}`,role:slot.includes('lead')||slot.includes('supporting')?'actor':slot,hiring_fee_usd:100000+n*50000,source:'fixture',talent_strength:70,genre_fit:65,coverage:'5 eligible films',specialties:['drama'],notable_works:Array.from({length:5},(_,i)=>({movie_id:'f'+i,title:`Verified ${i+1}: A very long fictional film title that remains readable in a narrow column`,year:2020+i,credited_jobs:['Director'],audience_rating:7,poster_url:'/broken.png'})),versions:{pricing_id:'pricing:pinned',dataset_id:'fixture:pinned',graph_id:'graph:pinned'}});
const blank=():Draft=>({draft_id:id,status:'awaiting_pick',genre_id:'drama',revision:0,synthetic:true,budget:{talent_budget_usd:32500000,talent_spend_usd:0,talent_remaining_usd:32500000,reserve_usd:17500000},picks:[],current_offer:null,rerolls_used:0,recasts_used:0,can_reroll:true,reroll_unavailable_reason:null,minimum_remaining_cost_usd:800000,snapshot_hash:null,versions:{catalog_id:'draft:test',graph_id:'graph:pinned'}});
function fixture(){
 let d=blank();let members:Member[]=[];let selectedSlot='director';const receipts=new Map<string,unknown>();
 const clone=<T,>(x:T):T=>structuredClone(x);
 function offer(slot:string,kind='pick'){d.current_offer={offer_id:slot+'-'+kind+'-'+d.rerolls_used,slot,kind,generated_at_revision:d.revision,shortage_message:null,candidates:[0,1,2].map(i=>({card:card(slot,kind==='recast'?i+3:i),selectable:i<2,blocked_reason:i===2?'Would leave too little for the remaining roles.':null}))};}
 offer('director');
 function money(){d.budget.talent_spend_usd=members.reduce((n,m)=>n+m.locked_fee_usd,0);d.budget.talent_remaining_usd=32500000-d.budget.talent_spend_usd;}
 async function handle(url:string,init?:RequestInit):Promise<Response>{
  const ok=(v:unknown,status=200)=>new Response(JSON.stringify(v),{status});
  if(url.startsWith('/api/v1/challenges'))return ok({items:[],next_offset:null});
  if(url.endsWith('/challenge'))return ok({challenge:null,submitted:false});
  if(url==='/api/v1/catalog')return ok(catalog);
  if(url==='/api/v1/sessions')return ok({access_token:token,expires_at:'2030-01-01T00:00:00Z'});
  if(url.includes('/films?'))return ok({items:card('director').notable_works,next_offset:url.includes('offset=10')?null:10});
  if(url.includes('/api/talent/'))return ok({reception:60,experience:70,versatility:80,genre_evidence_movies:4,genre_catalog_gap:false,coverage:{eligible_movies:12,rated_movies:8}});
  if(url.includes('/pair?'))return ok({edge:{edge_id:null,shared_movie_count:0,bonus:0},message:'No shared credits.'});
  if(init?.method==='POST'){
   const body=JSON.parse(String(init.body));if(receipts.has(body.request_id))return ok(receipts.get(body.request_id));
   if(url.endsWith('/drafts')){const value=clone(d);receipts.set(body.request_id,value);return ok(value);}
   if(url.endsWith('/picks')||url.endsWith('/recast/confirm')){const c=d.current_offer!.candidates.find(c=>c.card.person_id===body.person_id)!.card;const slot=d.current_offer!.slot;const pick={slot,person_id:c.person_id,locked_fee_usd:c.hiring_fee_usd,offer_id:d.current_offer!.offer_id};d.picks=d.picks.filter(p=>p.slot!==slot).concat(pick);members=members.filter(m=>m.slot!==slot).concat({slot,locked_fee_usd:c.hiring_fee_usd,card:c});money();d.revision++;if(url.endsWith('/recast/confirm')){d.recasts_used=1;d.status='review_locked';d.current_offer=null;}else if(d.picks.length===8){d.status='recast_available';d.current_offer=null;}else offer(slots[d.picks.length]);}
   else if(url.endsWith('/rerolls')){d.rerolls_used++;d.revision++;offer(d.current_offer!.slot);}
   else if(url.endsWith('/recast/preview')){selectedSlot=body.slot;d.status='recast_preview';d.revision++;offer(selectedSlot,'recast');}
   else if(url.endsWith('/recast/cancel')){d.status='recast_available';d.revision++;d.current_offer=null;}
   else if(url.endsWith('/finalize')){d.status='production_finalized';d.snapshot_hash='a'.repeat(64);d.current_offer=null;d.revision++;}
   else if(url.endsWith('/release')||url.endsWith('/retry-simulation')){d.status='results_available';d.revision++;const value={draft:clone(d),attempt:{status:'succeeded',attempt_number:1}};receipts.set(body.request_id,value);return ok(value);}
   else if(url.endsWith('/abandon')){d.status='abandoned';d.current_offer=null;d.revision++;}
   const value=clone(d);receipts.set(body.request_id,value);return ok(value);
  }
  if(url.endsWith('/roster'))return ok({draft_id:id,revision:d.revision,members});
  if(url.endsWith('/simulation'))return ok({status:d.status,result_available:d.status==='results_available',latest_attempt:null});
  if(url.endsWith('/result'))return ok(example);
  if(url.includes('/drafts?'))return ok({items:[d],next_offset:null});
  return ok(d);
 }
 function completed(){members=slots.map(s=>({slot:s,card:card(s),locked_fee_usd:100000}));d.picks=members.map(m=>({slot:m.slot,person_id:m.card.person_id,locked_fee_usd:m.locked_fee_usd,offer_id:m.slot+'-pick'}));d.status='recast_available';d.revision=8;d.current_offer=null;money();}
 return{handle,completed,get draft(){return d;},get members(){return members;}};
}
async function start(){render(<Studio/>);await screen.findByRole('radio',{name:/studio/i});await userEvent.click(screen.getByRole('button',{name:'Create guest session'}));await userEvent.click(await screen.findByLabelText('I saved my recovery token privately.'));await userEvent.click(screen.getByRole('button',{name:'Start draft'}));await waitFor(()=>expect(screen.getByRole('button',{name:'Select Practice director 0'})).toBeEnabled());}
async function choose(name:string){await userEvent.click(screen.getByRole('button',{name:'Select '+name}));await userEvent.click(screen.getByRole('button',{name:'Confirm selection'}));}
function setup(){const game=fixture();const request=vi.fn(game.handle);vi.stubGlobal('fetch',request);return{game,request};}
it('requires saving the token, displays all five works and blocks unaffordable cards',async()=>{
 const {request}=setup();const storage=vi.spyOn(Storage.prototype,'setItem');render(<Studio/>);await userEvent.click(screen.getByRole('button',{name:'Create guest session'}));
 expect(await screen.findByRole('button',{name:'Start draft'})).toBeDisabled();await userEvent.click(screen.getByLabelText('I saved my recovery token privately.'));await userEvent.click(screen.getByRole('button',{name:'Start draft'}));
 expect(await screen.findByRole('button',{name:'Select Practice director 2'})).toBeDisabled();expect(within(screen.getByRole('region',{name:'Candidate offers'})).getAllByText(/Verified 5:/)).toHaveLength(3);expect(storage).not.toHaveBeenCalled();
 const create=request.mock.calls.find(([u,i])=>u==='/api/v1/drafts'&&i?.method==='POST')!;expect(Object.keys(JSON.parse(String(create[1]?.body))).sort()).toEqual(['genre_id','mode','request_id','tier']);storage.mockRestore();
});
it('confirms a pick, can cancel, and renders the saved name with next-round focus',async()=>{
 const {request}=setup();await start();await userEvent.click(screen.getByRole('button',{name:'Select Practice director 0'}));expect(request.mock.calls.some(([u])=>u.endsWith('/picks'))).toBe(false);
 await userEvent.click(screen.getByRole('button',{name:'Go back'}));expect(screen.queryByRole('dialog')).not.toBeInTheDocument();await choose('Practice director 0');await waitFor(()=>expect(screen.getByRole('heading',{name:'Choose your lead'})).toHaveFocus());expect(screen.getByRole('button',{name:'Details for Practice director 0'})).toBeInTheDocument();
});
it('replays an uncertain request exactly and reads current state after an older receipt',async()=>{
 const game=fixture();let fail=true;
 const request=vi.fn(async(u:string,i?:RequestInit)=>{const result=await game.handle(u,i);if(u.endsWith('/picks')&&fail){fail=false;game.draft.revision+=1;return new Response(JSON.stringify({error:{message:'Acknowledgment lost'}}),{status:503});}return result;});vi.stubGlobal('fetch',request);await start();await choose('Practice director 0');await screen.findByText('Acknowledgment lost');expect(screen.getByRole('button',{name:'Refresh draft'})).toBeDisabled();
 await userEvent.click(screen.getByRole('button',{name:'Retry same request'}));await waitFor(()=>expect(screen.getByRole('button',{name:'Select Practice lead 0'})).toBeEnabled());expect(screen.getByText(/Revision 2/)).toBeInTheDocument();const posts=request.mock.calls.filter(([u])=>u.endsWith('/picks'));expect(posts).toHaveLength(2);expect(posts[0][1]?.body).toBe(posts[1][1]?.body);
});
it('blocks fresh writes on a stale revision until refreshed',async()=>{
 const game=fixture();let stale=true;vi.stubGlobal('fetch',vi.fn(async(u:string,i?:RequestInit)=>{if(u.endsWith('/picks')&&stale){stale=false;game.draft.revision++;return new Response(JSON.stringify({error:{message:'Another tab changed the draft.'}}),{status:409});}return game.handle(u,i);}));await start();await choose('Practice director 0');await screen.findByText('Another tab changed the draft.');expect(screen.getByRole('button',{name:'Select Practice director 0'})).toBeDisabled();expect(screen.queryByRole('button',{name:'Retry same request'})).not.toBeInTheDocument();await userEvent.click(screen.getByRole('button',{name:'Refresh draft'}));await waitFor(()=>expect(screen.getByRole('button',{name:'Select Practice director 0'})).toBeEnabled());
});
it('does not replay a committed mutation merely because its follow-up read failed',async()=>{
 const game=fixture();let fail=false;const request=vi.fn(async(u:string,i?:RequestInit)=>{if(u.endsWith('/picks')){const result=await game.handle(u,i);fail=true;return result;}if(u.endsWith('/roster')&&fail){fail=false;throw new Error('offline');}return game.handle(u,i);});vi.stubGlobal('fetch',request);await start();await choose('Practice director 0');await screen.findByText(/Refresh draft before the next action/);expect(screen.queryByRole('button',{name:'Retry same request'})).not.toBeInTheDocument();await userEvent.click(screen.getByRole('button',{name:'Refresh draft'}));await waitFor(()=>expect(screen.getByRole('button',{name:'Select Practice lead 0'})).toBeEnabled());expect(request.mock.calls.filter(([u])=>u.endsWith('/picks'))).toHaveLength(1);
});
it('restores names from the roster endpoint without creating or rerolling a draft',async()=>{
 const {game,request}=setup();game.completed();render(<Studio/>);await userEvent.type(screen.getByLabelText('Recovery token'),token);await userEvent.click(screen.getByRole('button',{name:'Restore session'}));await userEvent.click(await screen.findByText(/Session & saved films/));await userEvent.click(screen.getByRole('button',{name:/drama · Film/}));await screen.findByRole('button',{name:'Details for Practice director 0'});expect(request.mock.calls.every(([,i])=>i?.method==='GET')).toBe(true);expect(request.mock.calls.every(([u])=>!u.includes(token))).toBe(true);
});
it('keeps roster and balance on recast cancel and shows exact replacement refund',async()=>{
 const {game}=setup();game.completed();render(<Studio/>);await userEvent.click(screen.getByRole('button',{name:'Create guest session'}));await userEvent.click(await screen.findByLabelText('I saved my recovery token privately.'));await userEvent.click(screen.getByRole('button',{name:'Start draft'}));await waitFor(()=>expect(screen.getByRole('button',{name:'Preview recast'})).toBeEnabled());
 await userEvent.click(screen.getByRole('button',{name:'Preview recast'}));await screen.findByRole('button',{name:'Choose replacement Practice director 3'});expect(screen.getByRole('button',{name:'Details for Practice director 0'})).toBeInTheDocument();await userEvent.click(screen.getByRole('button',{name:'Cancel recast preview'}));await waitFor(()=>expect(screen.getByRole('button',{name:'Preview recast'})).toBeEnabled());expect(game.draft.budget.talent_spend_usd).toBe(800000);
 await userEvent.click(screen.getByRole('button',{name:'Preview recast'}));await userEvent.click(await screen.findByRole('button',{name:'Choose replacement Practice director 3'}));const modal=screen.getByRole('dialog');expect(within(modal).getByText('$150,000')).toBeInTheDocument();await userEvent.click(within(modal).getByRole('button',{name:'Confirm selection'}));await screen.findByRole('button',{name:'Details for Practice director 3'});expect(game.draft.budget.talent_spend_usd).toBe(950000);
});
it('locks only after confirmation, releases once and renders the saved financial report',async()=>{
 const {game,request}=setup();game.completed();render(<Studio/>);await userEvent.click(screen.getByRole('button',{name:'Create guest session'}));await userEvent.click(await screen.findByLabelText('I saved my recovery token privately.'));await userEvent.click(screen.getByRole('button',{name:'Start draft'}));await waitFor(()=>expect(screen.getByRole('button',{name:'Finalize production'})).toBeEnabled());await userEvent.click(screen.getByRole('button',{name:'Finalize production'}));expect(request.mock.calls.some(([u])=>u.endsWith('/finalize'))).toBe(false);await userEvent.click(screen.getByRole('button',{name:'Lock roster'}));await waitFor(()=>expect(screen.getByRole('button',{name:'Run release simulation'})).toBeEnabled());await userEvent.click(screen.getByRole('button',{name:'Run release simulation'}));await screen.findByText('Studio score');expect(await screen.findByText('$1,904,048')).toBeInTheDocument();expect(screen.queryByRole('button',{name:'Run release simulation'})).not.toBeInTheDocument();await userEvent.click(screen.getByRole('button',{name:'Refresh release report'}));expect(request.mock.calls.filter(([u])=>u.endsWith('/release'))).toHaveLength(1);
});
it('loads pinned role filmography, handles failed images and closes details with Escape',async()=>{
 const {request}=setup();await start();const firstImage=document.querySelector('.work-poster')!;fireEvent.error(firstImage);expect(firstImage.isConnected).toBe(false);await userEvent.click(screen.getByRole('button',{name:'View Practice director 0’s dossier'}));await screen.findByText('Full role-specific filmography');await userEvent.click(screen.getByRole('button',{name:'Next films'}));await waitFor(()=>expect(request.mock.calls.some(([u])=>u.includes('fixture%3Apinned')&&u.includes('role=director')&&u.includes('offset=10'))).toBe(true));fireEvent(screen.getByRole('dialog'),new Event('cancel',{cancelable:true}));expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
});
