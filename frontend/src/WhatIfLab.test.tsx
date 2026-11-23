import {render,screen,waitFor} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {afterEach,expect,it,vi} from 'vitest';
import WhatIfLab,{ComparisonReport,type SavedComparison} from './WhatIfLab';
import fixture from './testdata/whatif-example.phase11.json';
const saved=fixture.saved as SavedComparison,original=saved.comparison.baseline_card,replacement=saved.comparison.alternative_card;
afterEach(()=>vi.unstubAllGlobals());
function setup(interrupt=false){
 const onLock=vi.fn();let first=true;
 const fetcher=vi.fn(async(url:string,init?:RequestInit)=>{
  const response=(v:unknown,status=200)=>new Response(JSON.stringify(v),{status});
  if(init?.method==='POST'){if(interrupt&&first){first=false;return response({error:{message:'Interrupted receipt'}},503);}return response(saved);}
  if(url.includes('/candidates?'))return response({original,available_after_refund_usd:3656250,items:[{card:replacement,is_original:false,selectable:true,blocked_reason:null,hypothetical_spend_usd:3293750},{card:{...replacement,person_id:'expensive',name:'Unaffordable director'},is_original:false,selectable:false,blocked_reason:'Exceeds the original hiring allowance after refund.',hypothetical_spend_usd:99999999}],next_offset:null});
  if(url.includes('?limit='))return response({items:[{analysis_id:saved.analysis_id,slot:'director',name:replacement.name,unchanged:false,created_at:saved.created_at}],next_offset:null});
  return response(saved);
 });vi.stubGlobal('fetch',fetcher);render(<WhatIfLab draftId="film-one" token={'x'.repeat(43)} disabled={false} onLock={onLock}/>);return{fetcher,onLock};
}
it('loads candidates only on request, shows pinned cards, and blocks unaffordable choices',async()=>{
 const {fetcher}=setup();expect(fetcher).not.toHaveBeenCalled();await userEvent.click(screen.getByRole('button',{name:'Open what-if lab'}));expect(await screen.findByRole('button',{name:'Compare '+replacement.name})).toBeEnabled();expect(screen.getByRole('button',{name:'Compare Unaffordable director'})).toBeDisabled();expect(screen.getByText(/3,656,250/)).toBeInTheDocument();
});
it('keeps uncertain requests locked, retries the exact body and displays the saved report',async()=>{
 const {fetcher,onLock}=setup(true);await userEvent.click(screen.getByRole('button',{name:'Open what-if lab'}));await userEvent.click(await screen.findByRole('button',{name:'Compare '+replacement.name}));await screen.findByText('Interrupted receipt');expect(onLock).toHaveBeenLastCalledWith(true);expect(screen.getByLabelText('Role to explore')).toBeDisabled();await userEvent.click(screen.getByRole('button',{name:'Retry same comparison'}));await screen.findByRole('region',{name:'Hypothetical comparison report'});expect(onLock).toHaveBeenLastCalledWith(false);
 const posts=fetcher.mock.calls.filter(([,init])=>init?.method==='POST');expect(posts).toHaveLength(2);expect(posts[0][1]?.body).toBe(posts[1][1]?.body);expect(Object.keys(JSON.parse(String(posts[0][1]?.body))).sort()).toEqual(['person_id','request_id','slot']);expect(screen.getByLabelText('Role to explore')).toBeEnabled();
});
it('loads saved history without creating another comparison',async()=>{
 const {fetcher}=setup();await userEvent.click(screen.getByRole('button',{name:'Open what-if lab'}));await userEvent.click(await screen.findByRole('button',{name:'Load comparison history'}));await userEvent.click(await screen.findByRole('button',{name:'director · '+replacement.name}));await screen.findByRole('region',{name:'Hypothetical comparison report'});expect(fetcher.mock.calls.some(([,init])=>init?.method==='POST')).toBe(false);
});
it('clears the uncertain lock on a definitive expired-session response',async()=>{
 const {fetcher,onLock}=setup();const originalFetch=fetcher.getMockImplementation()!;fetcher.mockImplementation((u,i)=>i?.method==='POST'?Promise.resolve(new Response(JSON.stringify({error:{message:'Session expired'}}),{status:401})):originalFetch(u,i));await userEvent.click(screen.getByRole('button',{name:'Open what-if lab'}));await userEvent.click(await screen.findByRole('button',{name:'Compare '+replacement.name}));await screen.findByText('Session expired');expect(onLock).toHaveBeenLastCalledWith(false);expect(screen.queryByRole('button',{name:'Retry same comparison'})).not.toBeInTheDocument();
});
it('presents paired changes, descriptive ranges and evidence separately from official results',async()=>{
 render(<ComparisonReport saved={saved}/>);expect(screen.getByRole('table',{name:'Scenario medians and paired changes'})).toBeInTheDocument();await userEvent.click(screen.getByText('Scenario ranges and counts'));expect(screen.getByText(/not a confidence interval/)).toBeInTheDocument();expect(screen.getByText(/official release and challenge score stay unchanged/)).toBeInTheDocument();await userEvent.click(screen.getByText('Why the result changed'));expect(screen.getByText(/Talent strength: 80 → 90/)).toBeInTheDocument();
});
it('unmount releases its parent lock and aborts pending reads',async()=>{
 const onLock=vi.fn();vi.stubGlobal('fetch',vi.fn(()=>new Promise(()=>{})));const {unmount}=render(<WhatIfLab draftId="film" token="test" disabled={false} onLock={onLock}/>);await userEvent.click(screen.getByRole('button',{name:'Open what-if lab'}));await waitFor(()=>expect(onLock).toHaveBeenLastCalledWith(true));unmount();expect(onLock).toHaveBeenLastCalledWith(false);
});
