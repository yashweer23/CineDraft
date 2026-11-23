// Browser-only invented responses. Never imported by application code.
import {readFileSync} from 'node:fs';
const example=JSON.parse(readFileSync(new URL('../../data/phase8-simulation-example.json',import.meta.url)));
const slots=['director','lead','co_lead','supporting_1','supporting_2','writer','cinematographer','composer'];
const token='s'.repeat(43);
export function mockAPI(){
 const id=example.result.draft_id;
 const cards=(slot,n)=>({person_id:`${slot}-${n}`,name:['Mira Sen','Theo Hart','Elena Roy'][n%3]+' · '+slot,role:slot.includes('lead')||slot.includes('supporting')?'actor':slot,hiring_fee_usd:350000+n*50000,source:'fixture',talent_strength:78+n,genre_fit:84-n,coverage:'12 verified films · 9 with audience ratings',specialties:['drama','thriller'],versions:{dataset_id:'fixture:browser',pricing_id:'pricing:browser',graph_id:'graph:browser'},notable_works:Array.from({length:5},(_,i)=>({movie_id:'film'+i,title:['The Last Train Through the Valley of a Thousand Forgotten Names','A Map of Small Departures','Between Two Summers','The Quiet Hour','Letters from the Moon'][i],year:2020+i,credited_jobs:[slot==='writer'?'Screenplay':slot==='director'?'Director':'Actor'],audience_rating:7.2,poster_url:'/missing-poster.png'}))});
 let members=[];const receipts=new Map();const commands=[];let interrupted=false;
 const d={draft_id:id,status:'awaiting_pick',genre_id:'drama',revision:0,synthetic:true,budget:{talent_budget_usd:6500000,talent_spend_usd:0,talent_remaining_usd:6500000,reserve_usd:3500000},picks:[],current_offer:null,rerolls_used:0,recasts_used:0,can_reroll:true,reroll_unavailable_reason:null,minimum_remaining_cost_usd:2800000,snapshot_hash:null,versions:{catalog_id:'draft:browser',graph_id:'graph:browser'}};
 function offer(slot,kind='pick'){d.current_offer={offer_id:slot+'-'+kind+'-'+d.rerolls_used,slot,kind,generated_at_revision:d.revision,shortage_message:null,candidates:[0,1,2].map(i=>({card:cards(slot,i+(kind==='recast'?3:0)),selectable:i<2,blocked_reason:i===2?'Would leave too little for the remaining roles.':null}))};}offer('director');
 const copy=x=>structuredClone(x);
 async function route(route){
  const req=route.request();const u=new URL(req.url());const path=u.pathname;const result=(v,status=200)=>route.fulfill({status,contentType:'application/json',body:JSON.stringify(v)});
  if(path==='/api/v1/challenges')return result({items:[],next_offset:null});
  if(path.endsWith('/challenge'))return result({challenge:null,submitted:false});
  if(path==='/api/health')return result({status:'ok',service:'cinedraft-api',version:'0.9.0'});
  if(path==='/api/health/ready')return result({status:'ready',database:'connected'});
  if(path==='/api/v1/catalog')return result({catalog_id:'draft:browser',synthetic:true,tiers:[{tier:'indie',total_budget_usd:10000000,talent_budget_usd:6500000,enabled:true,reason:null},{tier:'studio',total_budget_usd:50000000,talent_budget_usd:32500000,enabled:true,reason:null},{tier:'blockbuster',total_budget_usd:200000000,talent_budget_usd:130000000,enabled:false,reason:'No feasible roster in this practice catalog.'}]});
  if(path==='/api/v1/sessions')return result({access_token:token,expires_at:'2030-01-01T00:00:00Z'});
  if(path.includes('/films'))return result({items:cards('director',0).notable_works,next_offset:u.searchParams.get('offset')==='0'?10:null});
  if(path.includes('/api/talent/'))return result({reception:78,experience:80,versatility:73,genre_evidence_movies:8,genre_catalog_gap:false,coverage:{eligible_movies:12,rated_movies:9}});
  if(path.includes('/pair'))return result({edge:{edge_id:null,shared_movie_count:0,bonus:0},message:'No shared credits.'});
  if(req.method()==='POST'){
   const body=req.postDataJSON();commands.push({path,body});if(receipts.has(body.request_id))return result(receipts.get(body.request_id));
   if(path==='/api/v1/drafts'){const v=copy(d);receipts.set(body.request_id,v);return result(v);}
   if(path.endsWith('/picks')||path.endsWith('/recast/confirm')){
    const c=d.current_offer.candidates.find(x=>x.card.person_id===body.person_id).card,slot=d.current_offer.slot;
    d.picks=d.picks.filter(p=>p.slot!==slot).concat({slot,person_id:c.person_id,locked_fee_usd:c.hiring_fee_usd,offer_id:d.current_offer.offer_id});members=members.filter(m=>m.slot!==slot).concat({slot,locked_fee_usd:c.hiring_fee_usd,card:c});d.budget.talent_spend_usd=members.reduce((v,m)=>v+m.locked_fee_usd,0);d.budget.talent_remaining_usd=6500000-d.budget.talent_spend_usd;d.revision++;
    if(path.endsWith('/recast/confirm')){d.recasts_used=1;d.status='review_locked';d.current_offer=null;}
    else if(d.picks.length===8){d.status='recast_available';d.current_offer=null;}
    else offer(slots[d.picks.length]);
   }else if(path.endsWith('/rerolls')){d.rerolls_used++;d.revision++;d.can_reroll=d.rerolls_used<2;offer(d.current_offer.slot);}
   else if(path.endsWith('/recast/preview')){d.status='recast_preview';d.revision++;offer(body.slot,'recast');}
   else if(path.endsWith('/recast/cancel')){d.status='recast_available';d.revision++;d.current_offer=null;}
   else if(path.endsWith('/finalize')){d.status='production_finalized';d.snapshot_hash='a'.repeat(64);d.revision++;}
   else if(path.endsWith('/release')){d.status='results_available';d.revision++;}
   const value=path.endsWith('/release')?{draft:copy(d),attempt:{status:'succeeded',attempt_number:1}}:copy(d);receipts.set(body.request_id,value);
   if(path.endsWith('/picks')&&!interrupted){interrupted=true;return result({error:{message:'Test interruption after commit. Retry the same request.'}},503);}
   return result(value);
  }
  if(path.endsWith('/roster'))return result({draft_id:id,revision:d.revision,members});
  if(path.endsWith('/simulation'))return result({status:d.status,result_available:d.status==='results_available',latest_attempt:null});
  if(path.endsWith('/result'))return result(example);
  if(path==='/api/v1/drafts')return result({items:[d],next_offset:null});
  return result(d);
 }
 return{route,commands};
}
