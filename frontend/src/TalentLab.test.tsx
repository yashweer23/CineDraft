import { render,screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach,expect,it,vi } from 'vitest';
import TalentLab from './TalentLab';
afterEach(()=>vi.unstubAllGlobals());
const version={pricing_id:'pricing:synthetic-v1',dataset_id:'fixture:demo',source:'fixture'};
const profile={person_id:'fixture-person',name:'Synthetic Director',role:'director',source:'fixture',profile_url:null,hiring_fee_usd:1250000,talent_strength:62.3,genre_fit:40,genre_evidence_movies:0,genre_catalog_gap:true,coverage:{level:'low',eligible_movies:2,rated_movies:0,reception_prior_only:true},notable_works:[{movie_id:'fixture-movie',title:'Synthetic Film',year:null,poster_url:null,audience_rating:null,credited_jobs:['Director'],rank:1}]};
it('shows an actionable empty build state',async()=>{
 vi.stubGlobal('fetch',vi.fn(async()=>new Response(JSON.stringify({items:[],next_offset:null}))));
 render(<TalentLab/>);await userEvent.click(screen.getByRole('button',{name:'Load talent catalog'}));
 expect(await screen.findByText(/No published talent builds yet/)).toBeInTheDocument();
});
it('renders real response fields with null and prior warnings, no invented works',async()=>{
 const request=vi.fn(async(url:string)=>new Response(JSON.stringify({items:url.includes('/versions')?[version]:[profile],next_offset:null})));
 vi.stubGlobal('fetch',request);render(<TalentLab/>);
 await userEvent.click(screen.getByRole('button',{name:'Load talent catalog'}));
 expect(await screen.findByText('Synthetic Director')).toBeInTheDocument();
 expect(screen.getByText('$1,250,000')).toBeInTheDocument();
 expect(screen.getByText('No audience rating')).toBeInTheDocument();
 expect(screen.getByText(/No rated-film evidence/)).toBeInTheDocument();
 expect(screen.getByText(/Catalog gap for this role/)).toBeInTheDocument();
 expect(screen.getByText('1 verified films shown')).toBeInTheDocument();
 expect(screen.getByRole('button',{name:'Next profiles'})).toBeDisabled();
 await userEvent.selectOptions(screen.getByLabelText('Professional role'),'actor');
 await screen.findByText('Synthetic Director');
 expect(request).toHaveBeenLastCalledWith(expect.stringContaining('role=actor'),expect.any(Object));
 await userEvent.selectOptions(screen.getByLabelText('Genre fit'),'crime');
 await screen.findByText('$1,250,000');
 expect(request).toHaveBeenLastCalledWith(expect.stringContaining('genre=crime'),expect.any(Object));
});
it('recovers from an API failure without displaying fabricated profiles',async()=>{
 let failed=true;
 vi.stubGlobal('fetch',vi.fn(async()=>failed?new Response('{}',{status:503}):new Response(JSON.stringify({items:[],next_offset:null}))));
 render(<TalentLab/>);await userEvent.click(screen.getByRole('button',{name:'Load talent catalog'}));
 expect(await screen.findByRole('alert')).toHaveTextContent('Catalog unavailable');
 failed=false;await userEvent.click(screen.getByRole('button',{name:'Load talent catalog'}));
 expect(await screen.findByText(/No published talent builds yet/)).toBeInTheDocument();
 expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});
