import {render,screen,waitFor} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {afterEach,expect,it,vi} from 'vitest';
import ReleaseInspector,{displayDecimal,type ReleaseResult} from './ReleaseInspector';
import type {Draft} from './DraftInspector';
afterEach(()=>vi.unstubAllGlobals());
const token='t'.repeat(43);
const draft={draft_id:'film-draft',revision:9,status:'production_finalized'} as Draft;
const result:ReleaseResult={schema_version:'phase8-v1',draft_id:'film-draft',input_hash:'a'.repeat(64),simulation_id:'simulation-id',simulation_version:'simulation-1.0',synthetic:true,versions:{graph_id:'graph:frozen',catalog_id:'draft-catalog:frozen'},studio_score:66,studio_score_unrounded:'65.925',critics:70,audience:64,cast_appeal:'50',score_components:[{name:'genre',value:'60',weight:'0.30',contribution:'18'},{name:'talent',value:'80',weight:'0.30',contribution:'24'},{name:'chemistry',value:'60',weight:'0.25',contribution:'15'},{name:'efficiency',value:'59.5',weight:'0.15',contribution:'8.925'}],production_cost_usd:6750000,marketing_usd:1350000,total_cost_usd:8100000,worldwide_gross_usd:18576000,studio_receipts_usd:9288000,profit_usd:1188000,return_on_total_cost_percent:'14.66666667',weekly_gross_usd:[8000000,5000000,3500000,2076000],unused_talent_budget_usd:3250000,explanation:{note:'Fictional game simulation, not a prediction of a real film.',finance_note:'Marketing is an additional modeled cost.',rows:[{slot:'director',name:'Synthetic Director',genre_contribution:'11.5',hiring_fee_usd:400000},{slot:'writer',name:'Synthetic Writer',genre_contribution:'10.7',hiring_fee_usd:400000}],top_genre_contributors:['director','writer'],chemistry_edges:[{slot_a:'director',slot_b:'lead',person_id_a:'d',person_id_b:'a',canonical_a:['a','actor'],canonical_b:['d','director'],name_a:'Synthetic Director',name_b:'Synthetic Actor',role_a:'director',role_b:'actor',edge_id:'edge-1',shared_movie_count:6,bonus:12,message:'Shared credits found in this dataset.'}],warnings:['director: low source coverage; values are game proxies.']},reproducibility:{manifest:{simulation_version:'simulation-1.0'},seed:'synthetic-only'}};
const saved={output_hash:'b'.repeat(64),result};
function response(value:unknown,status=200){return new Response(JSON.stringify(value),{status});}
function requests(url:string){
 if(url.endsWith('/simulation'))return response({status:'results_available',latest_attempt:{status:'succeeded',attempt_number:1,message:'Saved'},result_available:true});
 if(url.includes('/films'))return response({items:[{movie_id:'m1',title:'Synthetic Shared Film',year:2001,jobs_a:['Actor'],jobs_b:['Director']}],next_offset:null});
 return response(saved);
}
it('requires a confirmed finalized state before offering release and respects pending writes',async()=>{
 vi.stubGlobal('fetch',vi.fn(async()=>response({status:'production_finalized',latest_attempt:null,result_available:false})));const action=vi.fn();
 const view=render(<ReleaseInspector draft={draft} token={token} disabled={false} onAction={action}/>);
 const button=screen.getByRole('button',{name:'Run release simulation'});expect(button).toBeDisabled();
 await waitFor(()=>expect(button).toBeEnabled());await userEvent.click(button);expect(action).toHaveBeenCalledWith('release');
 view.rerender(<ReleaseInspector draft={draft} token={token} disabled={true} onAction={action}/>);expect(button).toBeDisabled();
});
it('shows separate score, simulated reviews, financial reconciliation and exact weekly total',async()=>{
 const fetch=vi.fn(async(url:string)=>requests(url));vi.stubGlobal('fetch',fetch);
 render(<ReleaseInspector draft={{...draft,status:'results_available',revision:10}} token={token} disabled={false} onAction={vi.fn()}/>);
 expect(await screen.findByText('Synthetic practice release')).toBeInTheDocument();
 expect(screen.getByText('Studio score')).toBeInTheDocument();expect(screen.getByText('Simulated critics')).toBeInTheDocument();
 expect(screen.getByText('Profit after marketing')).toBeInTheDocument();expect(screen.getByText('$1,188,000')).toBeInTheDocument();
 expect(screen.getByText(/Weeks sum to \$18,576,000/)).toBeInTheDocument();expect(screen.getByText(/14.67%/)).toBeInTheDocument();
 expect(screen.getByText(/Synthetic Director \(director\); Synthetic Writer \(writer\)/)).toBeInTheDocument();
 expect(screen.queryByRole('button',{name:'Run release simulation'})).not.toBeInTheDocument();
 expect(fetch.mock.calls.every(([url])=>url.startsWith('/api/v1/drafts/film-draft/'))).toBe(true);
});
it('retrieves only frozen graph evidence and labels jobs with the correct people',async()=>{
 const fetch=vi.fn(async(url:string)=>requests(url));vi.stubGlobal('fetch',fetch);
 render(<ReleaseInspector draft={{...draft,status:'results_available'}} token={token} disabled={false} onAction={vi.fn()}/>);
 await userEvent.click(await screen.findByText('The twelve chemistry relationships'));await userEvent.click(screen.getByRole('button',{name:'Inspect shared films'}));
 expect(await screen.findByText('Synthetic Shared Film (2001)')).toBeInTheDocument();
 expect(screen.getByText('Synthetic Director (director): Director · Synthetic Actor (actor): Actor')).toBeInTheDocument();
 expect(fetch.mock.calls.some(([url])=>url.includes('/graph%3Afrozen/edges/edge-1/films'))).toBe(true);
 expect(screen.getByRole('button',{name:'Next evidence'})).toBeDisabled();
});
it('offers a new retry only after a confirmed failed simulation',async()=>{
 vi.stubGlobal('fetch',vi.fn(async()=>response({status:'simulation_failed',latest_attempt:{attempt_number:1,status:'failed',error_code:'engine_error',message:'Simulation could not complete. Retry uses the same frozen inputs and seed.'},result_available:false})));
 const action=vi.fn();render(<ReleaseInspector draft={{...draft,status:'simulation_failed',revision:10}} token={token} disabled={false} onAction={action}/>);
 await waitFor(()=>expect(screen.getByRole('button',{name:'Retry failed simulation'})).toBeEnabled());
 expect(screen.getByRole('alert')).toHaveTextContent('same frozen inputs and seed');
 await userEvent.click(screen.getByRole('button',{name:'Retry failed simulation'}));expect(action).toHaveBeenCalledWith('retry-simulation');
 expect(screen.queryByRole('button',{name:'Run release simulation'})).not.toBeInTheDocument();
});
it('does not offer release when another tab has already changed server state',async()=>{
 vi.stubGlobal('fetch',vi.fn(async(url:string)=>requests(url)));render(<ReleaseInspector draft={draft} token={token} disabled={false} onAction={vi.fn()}/>);
 expect(await screen.findByText(/The server state changed/)).toBeInTheDocument();await screen.findByText('Synthetic practice release');
 expect(screen.queryByRole('button',{name:'Run release simulation'})).not.toBeInTheDocument();
});
it('recovers from a result-read failure without posting a second simulation',async()=>{
 let fail=true;const fetch=vi.fn(async(url:string)=>url.endsWith('/result')&&fail?response({error:{message:'Saved result temporarily unavailable'}},503):requests(url));vi.stubGlobal('fetch',fetch);
 render(<ReleaseInspector draft={{...draft,status:'results_available'}} token={token} disabled={false} onAction={vi.fn()}/>);
 expect(await screen.findByRole('alert')).toHaveTextContent('Saved result temporarily unavailable');fail=false;
 await userEvent.click(screen.getByRole('button',{name:'Refresh release report'}));expect(await screen.findByText('Synthetic practice release')).toBeInTheDocument();
 expect(fetch.mock.calls.some(([url])=>url.endsWith('/release'))).toBe(false);
});

it('formats saved decimal values with half-up rounding without binary ties',()=>{
 expect(displayDecimal('65.925')).toBe('65.93');expect(displayDecimal('-14.665')).toBe('-14.67');
 expect(displayDecimal('9.999')).toBe('10.00');expect(displayDecimal('-0.0001')).toBe('0.00');
});
