/** Account/challenge browser checks use invented HTTP responses; never a substitute for DB tests. */
import {createRequire} from 'node:module';
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {resolve} from 'node:path';
import {mkdir,readFile} from 'node:fs/promises';
import assert from 'node:assert/strict';
import {mockAPI} from './mock-api.mjs';
const require=createRequire(import.meta.url);
const {chromium}=require(process.env.CINEDRAFT_PLAYWRIGHT_MODULE||'../../.browser-tools/node_modules/playwright');
const base=process.env.CINEDRAFT_WEB_URL||'http://127.0.0.1:5174';
const output=resolve(process.env.CINEDRAFT_BROWSER_OUTPUT||'test-results/browser-phase12');await mkdir(output,{recursive:true});
let server;
if(process.env.CINEDRAFT_E2E_START==='1'){
 const frontend=fileURLToPath(new URL('../',import.meta.url));server=spawn(process.execPath,[resolve(frontend,'node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port',new URL(base).port||'5174','--strictPort'],{cwd:frontend,stdio:'ignore'});
 let ready=false;for(let i=0;i<150;i++){try{ready=(await fetch(base)).ok;if(ready)break;}catch{}await new Promise(r=>setTimeout(r,100));}if(!ready||server.exitCode!==null){server.kill();throw new Error('Test frontend did not start.');}
}
const browser=await chromium.launch({headless:true}).catch(e=>{server?.kill();throw e;});let passed=0;
try{
 for(const width of [1280,390]){
  const context=await browser.newContext({viewport:{width,height:900},acceptDownloads:true}),page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const mock=mockAPI(),token='g'.repeat(43),id='11111111-1111-4111-8111-111111111111',next='22222222-2222-4222-8222-222222222222';let hidden=true;const replays=[];
  const film={draft_id:id,status:'results_available',genre_id:'drama',revision:10,synthetic:true,budget:{talent_budget_usd:6500000,talent_spend_usd:3200000,talent_remaining_usd:3300000,reserve_usd:3500000},picks:[],current_offer:null,rerolls_used:0,recasts_used:0,can_reroll:false,minimum_remaining_cost_usd:0,snapshot_hash:'a'.repeat(64),versions:{catalog_id:'test'}};
  const child={...film,draft_id:next,status:'awaiting_pick',revision:0,snapshot_hash:null};
  const fixture=JSON.parse(await readFile(new URL('../../docs/phase-12/synthetic-event-example.json',import.meta.url),'utf8'));
  await page.route('**/api/**',async route=>{
   const req=route.request(),path=new URL(req.url()).pathname,reply=(v,status=200)=>route.fulfill({status,contentType:'application/json',body:JSON.stringify(v)});
   if(path==='/api/v1/drafts')return reply({items:[film],next_offset:null});
   if(path.endsWith('/challenge'))return reply({challenge:path.includes(next)?null:{challenge_id:'example',results_hidden:hidden,status:hidden?'open':'closed',closes_at:'2026-11-01T00:00:00Z'},submitted:!path.includes(next)});
   if(path.endsWith('/roster'))return reply({draft_id:path.includes(next)?next:id,revision:path.includes(next)?0:10,members:[]});
   if(path.endsWith('/analytics-events')){assert(!hidden);assert.equal(req.headers().authorization,'Bearer '+token);return reply(fixture);}
   if(path.endsWith('/replay')){assert(!hidden);replays.push(req.postDataJSON());return replays.length===1?reply({error:{message:'Response interrupted'}},503):reply(child);}
   if(path.endsWith('/'+id))return reply(film);if(path.endsWith('/'+next))return reply(child);
   return mock.route(route);
  });
  await page.goto(base);await page.locator('#studio').getByLabel('Recovery token',{exact:true}).fill(token);await page.locator('#studio').getByRole('button',{name:'Restore session',exact:true}).click();await page.getByText(/Session & saved films/).click();await page.getByRole('button',{name:/drama · Film/i}).click();
  await page.getByText(/Reports, seed and rankings stay hidden/).waitFor();assert.equal(await page.getByText('Gameplay analytics & practice replay',{exact:true}).count(),0);
  hidden=false;await page.getByRole('button',{name:'Refresh draft',exact:true}).click();await page.getByText('Gameplay analytics & practice replay',{exact:true}).click();
  const download=page.waitForEvent('download');await page.getByRole('button',{name:'Download my gameplay events',exact:true}).click();const file=await download;assert.match(file.suggestedFilename(),/^gameplay-[a-f0-9]{12}\.json$/);assert.deepEqual(JSON.parse(await readFile(await file.path(),'utf8')),fixture);
  await page.getByRole('button',{name:'Replay this brief',exact:true}).click();assert.equal(replays.length,0);await page.getByRole('button',{name:'Start practice replay',exact:true}).click();await page.getByRole('button',{name:'Retry same request',exact:true}).click();await page.getByText(/Film 22222222 ·/).waitFor();assert.deepEqual(replays[0],replays[1]);assert.deepEqual(Object.keys(replays[0]),['request_id']);
  await page.goto(new URL('../../docs/phase-12/demo-dashboard.html',import.meta.url).href);await page.getByRole('heading',{name:'Gameplay analytics'}).waitFor();await page.getByText('Inspect all 12 trace rows',{exact:true}).click();assert.equal(await page.locator('#trace tbody tr').count(),12);assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));await page.screenshot({path:resolve(output,`analytics-${width}.png`)});
  assert.deepEqual(errors,[]);await context.close();passed++;
 }
 console.log(JSON.stringify({journeys_passed:passed,widths:[1280,390],mode:'mock API; actual file download and offline SQL-generated dashboard',checks:['embargo','owner export','download contents','replay confirmation','exact retry','new draft','trace evidence','page reflow']}));
}finally{await browser.close();server?.kill();}
