/** Account/challenge browser checks use invented HTTP responses; never a substitute for DB tests. */
import {createRequire} from 'node:module';
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {resolve} from 'node:path';
import {mkdir} from 'node:fs/promises';
import assert from 'node:assert/strict';
import {mockAPI} from './mock-api.mjs';
const require=createRequire(import.meta.url);
const {chromium}=require(process.env.CINEDRAFT_PLAYWRIGHT_MODULE||'../../.browser-tools/node_modules/playwright');
const base=process.env.CINEDRAFT_WEB_URL||'http://127.0.0.1:5174';
const output=resolve(process.env.CINEDRAFT_BROWSER_OUTPUT||'test-results/browser-phase10');await mkdir(output,{recursive:true});
let server;
if(process.env.CINEDRAFT_E2E_START==='1'){
 const frontend=fileURLToPath(new URL('../',import.meta.url));server=spawn(process.execPath,[resolve(frontend,'node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port',new URL(base).port||'5174','--strictPort'],{cwd:frontend,stdio:'ignore'});
 let ready=false;for(let i=0;i<150;i++){try{ready=(await fetch(base)).ok;if(ready)break;}catch{}await new Promise(r=>setTimeout(r,100));}if(!ready||server.exitCode!==null){server.kill();throw new Error('Test frontend did not start.');}
}
const browser=await chromium.launch({headless:true}).catch(e=>{server?.kill();throw e;});let passed=0;
try{
 for(const width of [1280,390]){
  const context=await browser.newContext({viewport:{width,height:900},reducedMotion:'reduce'}),page=await context.newPage();const mock=mockAPI();const errors=[];let closed=false,entered=false,resultRequests=0;
  page.on('pageerror',e=>errors.push(e.message));
  const challenge=()=>({challenge_id:'daily-drama',opens_at:'2026-10-31T00:00:00Z',closes_at:'2026-11-01T00:00:00Z',timezone:'UTC',status:closed?'closed':'open',genre_id:'drama',tier:'indie',catalog_id:'draft:browser',config_hash:'c'.repeat(64),seed_commitment:'a'.repeat(64),configuration:{},results_hidden:!closed,synthetic:true});
  await page.route('**/api/**',async route=>{
   const path=new URL(route.request().url()).pathname;const reply=(v,status=200)=>route.fulfill({status,contentType:'application/json',body:JSON.stringify(v)});
   if(path.endsWith('/register')||path.endsWith('/login'))return reply({access_token:'acct_'+'x'.repeat(43),expires_at:'2030-01-01T08:00:00Z',account:{account_id:'one',username:'studio_one'}});
   if(path.endsWith('/logout'))return reply({signed_out:true});
   if(path==='/api/v1/challenges')return reply({items:[challenge()],next_offset:null});
   if(path.endsWith('/challenge'))return reply({challenge:entered?challenge():null,submitted:mock.commands.some(c=>c.path.endsWith('/release'))});
   if(path.endsWith('/attempts'))entered=true;
   if(path.endsWith('/leaderboard'))return reply({challenge:challenge(),items:closed?[{rank:1,username:'studio_one',studio_score:82,profit_usd:10000}]:[],next_offset:null,message:closed?'Ranked official releases.':'Rankings unlock after closing.'});
   if(path.endsWith('/audit'))return reply({seed:'b'.repeat(64),seed_commitment:'a'.repeat(64)});
   if(path.endsWith('/result')){resultRequests++;if(!closed)return reply({error:{message:'Hidden until close.'}},423);}
   return mock.route(route);
  });
  await page.goto(base);await page.getByLabel('Account action').selectOption('register');await page.getByLabel('Public username',{exact:true}).fill('studio_one');await page.getByLabel('Account password',{exact:true}).fill('a private test passphrase!');await page.getByRole('button',{name:'Create account',exact:true}).click();await page.getByText('Account · studio_one',{exact:true}).waitFor();assert.equal(await page.getByLabel('Your recovery token',{exact:true}).count(),0);
  await page.getByText('Daily challenges & leaderboards',{exact:true}).click();await page.getByRole('button',{name:'Enter challenge',exact:true}).click();await page.getByRole('button',{name:'Start my one attempt',exact:true}).click();await page.getByRole('region',{name:'Candidate offers'}).waitFor();
  for(let i=0;i<8;i++){
   const choose=page.getByRole('button',{name:/^Select /}).first();await choose.click();await page.getByRole('button',{name:'Confirm selection',exact:true}).click();if(i===0)await page.getByRole('button',{name:'Retry same request',exact:true}).click();
   if(i<7)await page.getByRole('heading',{name:'Choose your '+['director','lead','co lead','supporting 1','supporting 2','writer','cinematographer','composer'][i+1],exact:true}).waitFor();
  }
  await page.getByRole('button',{name:'Finalize production',exact:true}).first().click();await page.getByRole('button',{name:'Lock roster',exact:true}).click();await page.getByRole('button',{name:'Run release simulation',exact:true}).first().click();await page.getByText(/Your official release is submitted/).waitFor();assert.equal(resultRequests,0,'Report must not load before close');
  await page.getByRole('button',{name:'View rankings',exact:true}).click();await page.getByText('Rankings unlock after closing.',{exact:true}).waitFor();assert.equal(await page.getByRole('button',{name:'Reveal audit seed',exact:true}).count(),0);
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));await page.screenshot({path:resolve(output,`challenge-submitted-${width}.png`),fullPage:true});
  closed=true;await page.getByRole('button',{name:'Refresh draft',exact:true}).click();await page.getByText('Why this score?',{exact:true}).waitFor();await page.getByRole('button',{name:'Refresh rankings',exact:true}).click();await page.getByText('82/100',{exact:true}).waitFor();await page.getByRole('button',{name:'Reveal audit seed',exact:true}).click();await page.getByText('b'.repeat(64),{exact:true}).waitFor();
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));await page.locator('.challenge-panel').screenshot({path:resolve(output,`rankings-${width}.png`)});
  assert.deepEqual(await page.evaluate(()=>({local:Object.keys(localStorage),session:Object.keys(sessionStorage)})),{local:[],session:[]});
  await page.getByRole('button',{name:'Sign out',exact:true}).click();await page.getByRole('button',{name:'Sign in',exact:true}).waitFor();assert.equal(await page.getByRole('button',{name:'Refresh draft',exact:true}).count(),0);assert.deepEqual(errors,[]);await context.close();passed++;
 }
 console.log(JSON.stringify({mode:'mock HTTP; no database claim',journeys_passed:passed,widths:[1280,390],checks:['registration','one attempt confirmation','eight picks','release embargo','closed report','public rankings','seed audit','memory-only session','sign-out','no page overflow']}));
}finally{await browser.close();server?.kill();}
