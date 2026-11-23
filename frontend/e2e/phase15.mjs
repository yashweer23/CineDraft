/** Two-browser room UX using invented HTTP/WebSocket messages. No database claim. */
import {createRequire} from 'node:module';
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {resolve} from 'node:path';
import {mkdir} from 'node:fs/promises';
import assert from 'node:assert/strict';
import {mockAPI} from './mock-api.mjs';
const require=createRequire(import.meta.url);
const {chromium}=require(process.env.CINEDRAFT_PLAYWRIGHT_MODULE||'../../.browser-tools/node_modules/playwright');
const base=process.env.CINEDRAFT_WEB_URL||'http://127.0.0.1:5184';
const output=resolve(process.env.CINEDRAFT_BROWSER_OUTPUT||'test-results/browser-phase15');await mkdir(output,{recursive:true});
let server,browser;
try {
 if(process.env.CINEDRAFT_E2E_START==='1') {
  const frontend=fileURLToPath(new URL('../',import.meta.url));
  server=spawn(process.execPath,[resolve(frontend,'node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port',new URL(base).port,'--strictPort'],{cwd:frontend,stdio:'ignore'});
  let ready=false;for(let i=0;i<150;i++){try{ready=(await fetch(base)).ok;if(ready)break;}catch{}await new Promise(r=>setTimeout(r,100));}
  if(!ready||server.exitCode!==null)throw new Error('Test frontend did not start.');
 }
 browser=await chromium.launch({headless:true});
 const contexts=await Promise.all([1280,390].map(width=>browser.newContext({viewport:{width,height:900}})));
 const pages=await Promise.all(contexts.map(c=>c.newPage())),errors=[],sockets=new Map(),receipts=new Map(),posts=[];
 const tokens=['a'.repeat(43),'b'.repeat(43)],id='11111111-1111-4111-8111-111111111111';let code='',lost=false;
 const slots=['director','lead','co_lead','supporting_1','supporting_2','writer','cinematographer','composer'];
 const draft={draft_id:id,status:'awaiting_pick',genre_id:'thriller',revision:0,synthetic:true,budget:{talent_budget_usd:130000000,talent_spend_usd:0,talent_remaining_usd:130000000,reserve_usd:70000000},picks:[],current_offer:null,rerolls_used:0,recasts_used:0,can_reroll:false,snapshot_hash:null,minimum_remaining_cost_usd:800000,versions:{catalog_id:'fixture:browser'}};
 const room={room_id:id,revision:0,state:'waiting',guest_joined:false,turn_seat:null,turn_seconds:60,deadline:null,draft,members:[],events:[]};
 function offer(){const slot=slots[room.members.length];draft.current_offer={offer_id:slot,slot,kind:'pick',generated_at_revision:draft.revision,shortage_message:null,candidates:[0,1,2].map(n=>({selectable:n<2,blocked_reason:n===2?'Leaves too little for remaining roles.':null,card:{person_id:slot+n,name:`Synthetic ${slot} ${n}`,role:slot,hiring_fee_usd:100000+n,source:'fixture',talent_strength:70,genre_fit:65,coverage:'Practice',notable_works:[{movie_id:'movie',title:'A Fictional Film About Shared Choices',year:2024,credited_jobs:[slot]}]}}))};}offer();
 const snapshot=seat=>structuredClone({...room,seat,server_time:new Date().toISOString()});
 const broadcast=()=>{for(const [seat,socket] of sockets)socket.send(JSON.stringify({type:'room',room:snapshot(seat)}));};
 function commit(automatic=false){const card=draft.current_offer.candidates[0].card,slot=draft.current_offer.slot;
  room.events.push({turn:room.members.length+1,seat:room.members.length%2,slot,person_id:card.person_id,automatic});
  room.members.push({slot,locked_fee_usd:card.hiring_fee_usd,card});draft.picks.push({slot,person_id:card.person_id,locked_fee_usd:card.hiring_fee_usd,offer_id:slot});
  draft.revision++;room.revision++;draft.budget.talent_spend_usd+=card.hiring_fee_usd;draft.budget.talent_remaining_usd-=card.hiring_fee_usd;
  if(room.members.length===8){room.state='complete';room.deadline=null;room.turn_seat=null;draft.current_offer=null;draft.status='production_finalized';draft.revision++;draft.snapshot_hash='a'.repeat(64);}
  else{offer();room.turn_seat=room.members.length%2;room.deadline=new Date(Date.now()+60000).toISOString();}broadcast();
 }
 for(let seat=0;seat<2;seat++) {
  const page=pages[seat],mock=mockAPI();page.on('pageerror',e=>errors.push(e.message));
  await page.routeWebSocket('**/api/v1/rooms/*/live',ws=>{assert(!ws.url().includes('?'));ws.onMessage(message=>{assert.equal(JSON.parse(String(message)).token,tokens[seat]);sockets.set(seat,ws);broadcast();});ws.onClose(()=>sockets.delete(seat));});
  await page.route('**/api/**',async route=>{const req=route.request(),path=new URL(req.url()).pathname;const reply=(v,status=200)=>route.fulfill({status,contentType:'application/json',body:JSON.stringify(v)});
   if(path==='/api/v1/sessions')return reply({access_token:tokens[seat]});
   if(!path.startsWith('/api/v1/rooms'))return mock.route(route);
   assert.equal(req.headers().authorization,'Bearer '+tokens[seat]);
   if(req.method()==='GET')return reply(snapshot(seat));
   const body=req.postDataJSON();
   if(path.endsWith('/picks'))posts.push(body);
   if(receipts.has(body.request_id))return reply(receipts.get(body.request_id));
   if(path==='/api/v1/rooms'){code=body.invite_code;}
   else if(path.endsWith('/join')){assert.equal(body.invite_code,code);room.guest_joined=true;room.revision++;}
   else if(path.endsWith('/start')){room.state='active';room.revision++;room.turn_seat=0;room.deadline=new Date(Date.now()+60000).toISOString();}
   else if(path.endsWith('/picks')){assert.equal(seat,room.turn_seat);assert.equal(body.expected_revision,room.revision);commit();}
   const result=snapshot(seat);receipts.set(body.request_id,result);broadcast();
   if(path.endsWith('/picks')&&!lost){lost=true;return reply({error:{message:'Acknowledgment lost after saved pick'}},503);}
   return reply(result);
  });
  await page.goto(base);await page.locator('#rooms').getByRole('button',{name:'New room player',exact:true}).click();
 }
 const host=pages[0].locator('#rooms'),partner=pages[1].locator('#rooms');
 await host.getByRole('button',{name:'Create co-op room',exact:true}).click();await host.getByText(/Waiting for your partner/).waitFor();
 await partner.getByLabel('Room ID',{exact:true}).fill(id);await partner.getByLabel('Invitation code',{exact:true}).fill(code);await partner.getByRole('button',{name:'Join partner',exact:true}).click();
 await host.getByRole('button',{name:'Start alternating picks',exact:true}).click();await host.getByRole('heading',{name:/Your turn/}).waitFor();
 assert(await partner.getByRole('button',{name:'Hire Synthetic director 0',exact:true}).isDisabled());
 await host.getByRole('button',{name:'Hire Synthetic director 0',exact:true}).click();await host.getByRole('button',{name:'Retry same room request',exact:true}).click();await host.getByRole('button',{name:'Retry same room request',exact:true}).waitFor({state:'detached'});assert.deepEqual(posts[0],posts[1]);
 // An invented timeout notification exercises display; backend deadline behavior has separate tests.
 commit(true);await partner.getByText(/Auto-picked/).waitFor();
 for(let turn=2;turn<8;turn++) {
  const region=turn%2?partner:host;await region.getByRole('button',{name:`Hire Synthetic ${slots[turn]} 0`,exact:true}).click();
  if(turn===2){for(const [i,page] of pages.entries()){assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));await page.locator('#rooms').screenshot({path:resolve(output,`room-${i===0?1280:390}.png`)});}}
 }
 for(const region of [host,partner])await region.getByRole('heading',{name:'Your film is locked.',exact:true}).waitFor();
 // Reload and restore membership: no new create/join or pick.
 await pages[1].reload();await partner.getByLabel('Existing recovery or account token',{exact:true}).fill(tokens[1]);await partner.getByRole('button',{name:'Restore room player',exact:true}).click();await partner.getByLabel('Room ID',{exact:true}).fill(id);await partner.getByRole('button',{name:'Reopen saved room',exact:true}).click();await partner.getByRole('heading',{name:'Your film is locked.',exact:true}).waitFor();
 await partner.getByRole('status').filter({hasText:/^Live/}).waitFor();
 assert.equal(room.members.length,8);assert.deepEqual(errors,[]);
 for(const page of pages){await page.goto('about:blank');await page.unrouteAll({behavior:'wait'});} 
 console.log(JSON.stringify({passed:true,players:2,widths:[1280,390],mode:'mock HTTP and WebSocket',checks:['invitation','alternating turns','exact retry','automatic-pick display','live partner updates','final roster','reload recovery','reflow']}));
} finally {await browser?.close();server?.kill();}
