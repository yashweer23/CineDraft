import {render,screen,waitFor,act} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {afterEach,expect,it,vi} from 'vitest';
import RoomLobby,{newer,invitation,type Room} from './RoomLobby';

const token='p'.repeat(43),id='11111111-1111-4111-8111-111111111111';
function state(seat:0|1=0):Room {
 return {room_id:id,revision:2,state:'active',seat,guest_joined:true,turn_seat:0,turn_seconds:60,deadline:new Date(Date.now()+60000).toISOString(),server_time:new Date().toISOString(),members:[],events:[],draft:{draft_id:id,status:'awaiting_pick',genre_id:'thriller',revision:0,synthetic:true,budget:{talent_budget_usd:130000000,talent_spend_usd:0,talent_remaining_usd:130000000,reserve_usd:70000000},picks:[],rerolls_used:0,recasts_used:0,can_reroll:false,reroll_unavailable_reason:null,minimum_remaining_cost_usd:100,snapshot_hash:null,versions:{catalog_id:'demo',graph_id:'demo'},current_offer:{offer_id:id,slot:'director',kind:'pick',generated_at_revision:0,shortage_message:null,candidates:[{card:{person_id:id,name:'Synthetic Director',role:'director',hiring_fee_usd:100,source:'fixture',talent_strength:60,genre_fit:70,coverage:'practice',notable_works:[]},selectable:true,blocked_reason:null}]}}};
}
class Socket {
 static OPEN=1;static instances:Socket[]=[];readyState=0;onopen=()=>{};onmessage=(_:MessageEvent)=>{};onclose=()=>{};onerror=()=>{};
 send=vi.fn();close=vi.fn();constructor(readonly url:string){Socket.instances.push(this);}
}
afterEach(()=>{vi.unstubAllGlobals();Socket.instances=[];});
function setup(value=state(),uncertain=false) {
 vi.stubGlobal('WebSocket',Socket);let current=value;
 const posts:string[]=[];
 const fetch=vi.fn(async(url:string,init?:RequestInit)=>{
  const ok=(v:unknown,status=200)=>new Response(JSON.stringify(v),{status});
  if(url==='/api/v1/sessions')return ok({access_token:token});
  if(url==='/api/v1/rooms')return ok(current);
  if(url.endsWith('/picks')) {
   posts.push(String(init?.body));
   current={...current,revision:3,turn_seat:1,draft:{...current.draft,revision:1}};
   if(uncertain&&posts.length===1)return ok({error:{message:'Response lost'}},503);
   return ok(value); // deliberately old receipt: GET must win
  }
  return ok(current);
 });vi.stubGlobal('fetch',fetch);
 return {fetch,posts};
}
async function open(){render(<RoomLobby/>);await userEvent.click(screen.getByRole('button',{name:'New room player'}));await userEvent.click(await screen.findByRole('button',{name:'Create co-op room'}));await screen.findByRole('button',{name:'Hire Synthetic Director'});}
it('generates random invitations and refuses older snapshots',()=>{
 expect(invitation()).toMatch(/^[A-Za-z0-9_-]{43}$/);expect(invitation()).not.toBe(invitation());
 const current=state();expect(newer(current,{...current,revision:1})).toBe(current);
 expect(newer(current,{...current,revision:3,draft:{...current.draft,revision:-1}})).toBe(current);
});
it('blocks partner picks and never puts credentials in socket URL',async()=>{
 setup(state(1));await open();expect(screen.getByRole('button',{name:'Hire Synthetic Director'})).toBeDisabled();
 const ws=Socket.instances[0];expect(ws.url).not.toContain(token);expect(ws.url).not.toContain('?');
 act(()=>ws.onopen());expect(ws.send).toHaveBeenCalledWith(JSON.stringify({token}));
});
it('retries identical uncertain command and refreshes past an old receipt',async()=>{
 const {posts}=setup(state(),true);await open();await userEvent.click(screen.getByRole('button',{name:'Hire Synthetic Director'}));
 expect(await screen.findByRole('button',{name:'Retry same room request'})).toBeEnabled();
 expect(screen.getByRole('button',{name:'Hire Synthetic Director'})).toBeDisabled();
 await userEvent.click(screen.getByRole('button',{name:'Retry same room request'}));
 await waitFor(()=>expect(screen.queryByRole('button',{name:'Retry same room request'})).not.toBeInTheDocument());
 expect(posts).toHaveLength(2);expect(posts[0]).toBe(posts[1]);expect(screen.getByRole('heading',{name:/Partner’s turn/})).toBeInTheDocument();
});
it('accepts a live turn update and keeps automatic picks visible',async()=>{
 const value=state(1);setup(value);await open();
 const next={...value,revision:3,turn_seat:1,events:[{turn:1,seat:0,slot:'director',person_id:id,automatic:true}],members:[{slot:'director',locked_fee_usd:100,card:value.draft.current_offer!.candidates[0].card}],draft:{...value.draft,revision:1}};
 act(()=>Socket.instances[0].onmessage({data:JSON.stringify({type:'room',room:next})} as MessageEvent));
 expect(screen.getByRole('button',{name:'Hire Synthetic Director'})).toBeEnabled();expect(screen.getByText(/Auto-picked/)).toBeInTheDocument();
});
it('does not enable picks after a displayed deadline',async()=>{
 setup({...state(),deadline:new Date(Date.now()-1000).toISOString()});await open();
 expect(screen.getByRole('button',{name:'Hire Synthetic Director'})).toBeDisabled();expect(screen.getByText(/Waiting for the server’s automatic pick/)).toBeInTheDocument();
});
