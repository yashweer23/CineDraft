/** Run all existing UI regressions sequentially; each journey covers two widths. */
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
if(process.env.CINEDRAFT_E2E_LIVE==='1') throw new Error('This suite uses mocked HTTP. Run npm run test:browser with CINEDRAFT_E2E_LIVE=1 for the live guest journey.');
const checks=['journey.mjs','phase10.mjs','phase11.mjs','phase12.mjs'];
for(const check of checks){
 const result=spawnSync(process.execPath,[fileURLToPath(new URL(check,import.meta.url))],{
  stdio:'inherit',env:{...process.env,CINEDRAFT_E2E_START:process.env.CINEDRAFT_E2E_START||'1'},
 });
 if(result.error||result.status!==0){console.error('Browser gate failed:',check);process.exit(1);}
}
console.log(JSON.stringify({mode:'mock HTTP',suites_passed:checks.length,journeys_passed:checks.length*2,widths:[1280,390]}));
