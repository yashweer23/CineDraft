/** Local browser gate. Defaults to mocked HTTP. CINEDRAFT_E2E_LIVE=1 uses real synthetic DB data. */
import {createRequire} from 'node:module';
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {mkdir} from 'node:fs/promises';
import {resolve} from 'node:path';
import assert from 'node:assert/strict';
import {mockAPI} from './mock-api.mjs';
const require=createRequire(import.meta.url);
const {chromium}=require(process.env.CINEDRAFT_PLAYWRIGHT_MODULE||'../../.browser-tools/node_modules/playwright');
const base=process.env.CINEDRAFT_WEB_URL||'http://127.0.0.1:5174';
const live=process.env.CINEDRAFT_E2E_LIVE==='1';
const output=resolve(process.env.CINEDRAFT_BROWSER_OUTPUT||'test-results/browser');await mkdir(output,{recursive:true});
let server;
if(process.env.CINEDRAFT_E2E_START==='1'){
 const frontend=fileURLToPath(new URL('../',import.meta.url));
 server=spawn(process.execPath,[resolve(frontend,'node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port',new URL(base).port||'5174','--strictPort'],{cwd:frontend,stdio:'ignore'});
 let started=false;
 for(let i=0;i<150;i++){try{started=(await fetch(base)).ok;if(started)break;}catch{}await new Promise(r=>setTimeout(r,100));}
 if(!started||server.exitCode!==null){server.kill();throw new Error('Test frontend could not start. Check dependencies and the chosen port.');}
}
const browser=await chromium.launch({headless:true}).catch(error=>{server?.kill();throw error;});let passed=0;
async function ready(locator){await locator.waitFor();for(let i=0;i<300;i++){if(await locator.isEnabled())return;await new Promise(r=>setTimeout(r,100));}throw new Error('Control did not become ready within 30 seconds');}
async function fit(page){assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Horizontal page overflow');}
try{
 for(const width of [1280,390]){
  const context=await browser.newContext({viewport:{width,height:900},reducedMotion:'reduce'});const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  if(live){const r=await context.request.get(base+'/api/v1/catalog');assert(r.ok(),'Activate a synthetic drafting catalog first.');assert((await r.json()).synthetic,'Live browser test requires a synthetic catalog; it creates its own guest film.');}
  const mock=live?null:mockAPI();if(mock)await page.route('**/api/**',mock.route);
  await page.goto(base);await page.getByRole('radio',{name:/indie/i}).waitFor();await fit(page);
  await page.getByRole('button',{name:'Create guest session',exact:true}).first().click();
  const token=await page.getByLabel('Your recovery token',{exact:true}).first().inputValue(); // Never logged or included in screenshots.
  await page.getByLabel('I saved my recovery token privately.').check();await page.getByRole('button',{name:'Start draft',exact:true}).first().click();
  await page.getByRole('region',{name:'Candidate offers'}).waitFor();
  const pick=page.getByRole('button',{name:/^Select /}).first();await ready(pick);await fit(page);
  await page.screenshot({path:resolve(output,`draft-${width}.png`),fullPage:true});
  await page.locator('.candidate-card').first().screenshot({path:resolve(output,`candidate-${width}.png`)});
  if(!live){
   const dossier=page.getByRole('button',{name:/^View .+ dossier$/}).first();await dossier.click();await page.getByRole('heading',{name:'Full role-specific filmography'}).waitFor();await page.keyboard.press('Escape');assert(await dossier.evaluate(el=>el===document.activeElement),'Details close must restore keyboard focus');
   if(width===1280){await page.setViewportSize({width:640,height:450});await fit(page);await page.screenshot({path:resolve(output,'draft-200-percent.png'),fullPage:true});await page.setViewportSize({width:1280,height:900});}
  }
  for(let i=0;i<8;i++){
   const choose=page.getByRole('button',{name:/^Select /}).first();await ready(choose);await choose.click();await page.getByRole('button',{name:'Confirm selection',exact:true}).click();
   if(mock&&i===0){await page.getByRole('button',{name:'Retry same request',exact:true}).click();}
   if(i<7)await page.getByRole('heading',{name:'Choose your '+['director','lead','co lead','supporting 1','supporting 2','writer','cinematographer','composer'][i+1],exact:true}).waitFor();
  }
  await ready(page.getByRole('button',{name:'Preview recast',exact:true}).first());
  await page.getByRole('button',{name:'Preview recast',exact:true}).first().click();await page.getByRole('button',{name:'Cancel recast preview',exact:true}).click();
  await ready(page.getByRole('button',{name:'Finalize production',exact:true}).first());await page.getByRole('button',{name:'Finalize production',exact:true}).first().click();await page.getByRole('button',{name:'Lock roster',exact:true}).click();
  await ready(page.getByRole('button',{name:'Run release simulation',exact:true}).first());await page.getByRole('button',{name:'Run release simulation',exact:true}).first().click();await page.getByText('Why this score?',{exact:true}).waitFor();await fit(page);
  await page.screenshot({path:resolve(output,`report-${width}.png`),fullPage:true});
  await page.locator('.production-content').screenshot({path:resolve(output,`report-detail-${width}.png`)});
  await page.reload();await page.getByLabel('Recovery token',{exact:true}).first().fill(token);await page.getByRole('button',{name:'Restore session',exact:true}).first().click();await page.getByText('Session & saved films',{exact:false}).first().click();await page.getByRole('button',{name:/Film .*results available/}).click();await page.getByText('Why this score?',{exact:true}).waitFor();
  assert(await page.getByRole('button',{name:'Run release simulation',exact:true}).count()===0,'Saved release cannot reroll');
  if(mock){const picks=mock.commands.filter(c=>c.path.endsWith('/picks'));assert.deepEqual(picks[0].body,picks[1].body);assert.equal(mock.commands.filter(c=>c.path.endsWith('/release')).length,1);}
  assert.deepEqual(errors,[],'Browser runtime errors');await context.close();passed++;
 }
 console.log(JSON.stringify({mode:live?'live API and PostgreSQL':'mock HTTP responses',journeys_passed:passed,widths:[1280,390],checks:['complete flow','same-request replay (mock mode)','recast cancel','token restoration','saved report','no page overflow','keyboard Escape/focus (mock mode)','200% equivalent reflow viewport (mock mode)'],screenshots:output}));
}finally{await browser.close();server?.kill();}
