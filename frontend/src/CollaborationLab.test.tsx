import {render,screen,within,waitFor} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {afterEach,expect,it,vi} from 'vitest';
import CollaborationLab from './CollaborationLab';
afterEach(()=>vi.unstubAllGlobals());
const a={person_id:'person-a',name:'Synthetic Director',role:'director',source:'fixture',source_key:'fixture:a',film_count:6};
const b={person_id:'person-b',name:'Synthetic Actor',role:'actor',source:'fixture',source_key:'fixture:b',film_count:6};
const version={graph_id:'graph:test',dataset_id:'fixture:graph-test',source:'fixture',report:{nodes:2,edges:1,evidence_rows:6,isolated_nodes:0}};
const edge={edge_id:'edge-test',a,b,shared_movie_count:6,bonus:12,capped:true};
const film=(n:number)=>({movie_id:`film-${n}`,title:`Synthetic shared film ${n}`,year:null,source:'fixture',source_url:null,poster_url:null,jobs_a:['Director'],jobs_b:['Actor']});
function response(value:unknown,status=200){return new Response(JSON.stringify(value),{status});}
function fixtureRequest(url:string){
 if(url.includes('/versions'))return response({items:[version],next_offset:null});
 if(url.includes('/nodes'))return response({items:[a,b,{...a,role:'writer'}],next_offset:null});
 if(url.includes('/pair'))return response({graph_id:version.graph_id,dataset_id:version.dataset_id,edge:{...edge,edge_id:null,shared_movie_count:0,bonus:0,capped:false},message:'No shared credits found in this dataset.'});
 if(url.includes('/films'))return response({items:url.includes('offset=5')?[film(6)]:[1,2,3,4,5].map(film),next_offset:url.includes('offset=5')?null:5});
 return response({items:[edge],next_offset:null});
}
async function load(){render(<CollaborationLab/>);await userEvent.click(screen.getByRole('button',{name:'Load collaboration graphs'}));}
it('shows actionable empty graph state without invented collaborations',async()=>{
 vi.stubGlobal('fetch',vi.fn(async()=>response({items:[],next_offset:null})));await load();
 expect(await screen.findByText(/No published collaboration graphs yet/)).toBeInTheDocument();
 expect(screen.queryByText('Synthetic Director')).not.toBeInTheDocument();
});
it('shows exact roles, cap and every evidence page with missing years labeled',async()=>{
 vi.stubGlobal('fetch',vi.fn(async(url:string)=>fixtureRequest(url)));await load();
 await userEvent.click(await screen.findByRole('button',{name:'Inspect shared films'}));
 expect(await screen.findByText('Synthetic shared film 1')).toBeInTheDocument();
 expect(screen.getByText(/Bonus capped at 12/)).toBeInTheDocument();
 expect(screen.getAllByText('(Year unavailable)')).toHaveLength(5);
 expect(screen.getByText('Showing 1–5 of 6 shared films. Each movie counts once.')).toBeInTheDocument();
 await userEvent.click(screen.getByRole('button',{name:'Next shared films'}));
 expect(await screen.findByText('Synthetic shared film 6')).toBeInTheDocument();
 expect(screen.queryByText('Synthetic shared film 1')).not.toBeInTheDocument();
 expect(screen.getByRole('button',{name:'Next shared films'})).toBeDisabled();
});
it('compares role identities, prevents self-selection and explains zero evidence',async()=>{
 const request=vi.fn(async(url:string)=>fixtureRequest(url));vi.stubGlobal('fetch',request);await load();
 const first=await screen.findByLabelText('Person A credited role');
 await waitFor(()=>expect(within(first).getAllByRole('option')).toHaveLength(4));
 await userEvent.selectOptions(first,'person-a/director');
 const second=screen.getByLabelText('Person B credited role');
 expect(within(second).queryByRole('option',{name:/Synthetic Director/})).not.toBeInTheDocument();
 await userEvent.selectOptions(second,'person-b/actor');
 await userEvent.click(screen.getByRole('button',{name:'Compare credited roles'}));
 expect(await screen.findByText(/This is not evidence that they never collaborated/)).toHaveTextContent('No shared credits found in this dataset.');
 expect(request.mock.calls.some(([url])=>url.includes('person_a=person-a&role_a=director&person_b=person-b&role_b=actor'))).toBe(true);
 expect(screen.queryByText('Synthetic shared film 1')).not.toBeInTheDocument();
});
it('uses role filter and person search in requests',async()=>{
 const request=vi.fn(async(url:string)=>fixtureRequest(url));vi.stubGlobal('fetch',request);await load();
 await userEvent.selectOptions(await screen.findByLabelText('Connection role filter'),'composer');
 await waitFor(()=>expect(request.mock.calls.some(([url])=>url.includes('/edges?')&&url.includes('role=composer'))).toBe(true));
 await userEvent.type(screen.getByLabelText('Person A name search'),'Synthetic');
 await userEvent.click(screen.getByRole('button',{name:'Search person a'}));
 await waitFor(()=>expect(request.mock.calls.some(([url])=>url.includes('q=Synthetic'))).toBe(true));
});
it('recovers after unavailable API without showing fabricated records',async()=>{
 let failed=true;vi.stubGlobal('fetch',vi.fn(async(url:string)=>failed?response({},503):fixtureRequest(url)));await load();
 expect(await screen.findByRole('alert')).toHaveTextContent('Phase 6 migration');
 failed=false;await userEvent.click(screen.getByRole('button',{name:'Load collaboration graphs'}));
 expect(await screen.findByRole('button',{name:'Inspect shared films'})).toBeInTheDocument();
 expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});
it('retries film evidence failures',async()=>{
 let failed=true;vi.stubGlobal('fetch',vi.fn(async(url:string)=>url.includes('/films')&&failed?response({},503):fixtureRequest(url)));await load();
 await userEvent.click(await screen.findByRole('button',{name:'Inspect shared films'}));
 const retry=await screen.findByRole('button',{name:'Retry evidence'});failed=false;await userEvent.click(retry);
 expect(await screen.findByText('Synthetic shared film 1')).toBeInTheDocument();
});
it('clears old evidence when changing the published graph',async()=>{
 vi.stubGlobal('fetch',vi.fn(async(url:string)=>url.includes('/versions')?response({items:[version,{...version,graph_id:'graph:empty'}],next_offset:null}):url.includes('graph%3Aempty')?response({items:[],next_offset:null}):fixtureRequest(url)));
 await load();await userEvent.click(await screen.findByRole('button',{name:'Inspect shared films'}));
 await screen.findByText('Synthetic shared film 1');
 await userEvent.selectOptions(screen.getByLabelText('Published collaboration graph'),'graph:empty');
 expect(await screen.findByText(/No shared credits found in this dataset for this filter/)).toBeInTheDocument();
 expect(screen.queryByText('Synthetic shared film 1')).not.toBeInTheDocument();
});
