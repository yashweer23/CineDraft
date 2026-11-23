import {render,screen} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {afterEach,expect,it,vi} from 'vitest';
import Studio from './Studio';
const token='acct_'+'x'.repeat(43),id='11111111-1111-4111-8111-111111111111';
const challenge={challenge_id:'daily-drama',opens_at:'2026-10-31T00:00:00Z',closes_at:'2026-11-01T00:00:00Z',timezone:'UTC',status:'open',genre_id:'drama',tier:'indie',catalog_id:'catalog:one',config_hash:'c'.repeat(64),seed_commitment:'a'.repeat(64),configuration:{},results_hidden:true,synthetic:true};
afterEach(()=>vi.unstubAllGlobals());
function setup(){
 let hidden=true,interrupted=false;
 const d={draft_id:id,status:'results_available',genre_id:'drama',revision:10,synthetic:true,budget:{talent_budget_usd:6500000,talent_spend_usd:800000,talent_remaining_usd:5700000,reserve_usd:3500000},picks:[],current_offer:null,rerolls_used:0,recasts_used:0,can_reroll:false,reroll_unavailable_reason:null,minimum_remaining_cost_usd:0,snapshot_hash:'a'.repeat(64),versions:{catalog_id:'catalog:one'}};
 const fetcher=vi.fn(async(url:string,init?:RequestInit)=>{
  void init;const ok=(v:unknown,status=200)=>new Response(JSON.stringify(v),{status});
  if(url==='/api/v1/catalog')return ok({catalog_id:'catalog:one',synthetic:true,tiers:[{tier:'indie',total_budget_usd:10000000,talent_budget_usd:6500000,enabled:true,reason:null}]});
  if(url.includes('/challenges?'))return ok({items:[challenge],next_offset:null});
  if(url.endsWith('/register')||url.endsWith('/login'))return ok({access_token:token,expires_at:'2030-01-01T08:00:00Z',account:{account_id:id,username:'studio_one'}});
  if(url.endsWith('/claim-guest'))return ok({claimed:true,films:2,guest_access_revoked:true});
  if(url.endsWith('/password'))return ok({password_changed:true,all_sessions_revoked:true});
  if(url.endsWith('/logout'))return ok({signed_out:true});
  if(url.endsWith('/attempts')){if(!interrupted){interrupted=true;return ok({error:{message:'Acknowledgment interrupted'}},503);}return ok(d);}
  if(url.endsWith('/mine'))return ok({draft_id:id});
  if(url.endsWith('/challenge'))return ok({challenge:{...challenge,results_hidden:hidden,status:hidden?'open':'closed'},submitted:true});
  if(url.endsWith('/roster'))return ok({draft_id:id,revision:10,members:[]});
  if(url.endsWith('/simulation'))return ok({status:'results_available',result_available:true,latest_attempt:null});
  if(url.endsWith('/result'))return ok({error:{message:'Saved report fixture reached'}},404);
  if(url.includes('/leaderboard?'))return ok({challenge:{...challenge,results_hidden:hidden,status:hidden?'open':'closed'},items:hidden?[]:[{rank:1,username:'studio_one',studio_score:82,profit_usd:10000}],next_offset:null,message:hidden?'Rankings unlock after closing.':'Studio score, then profit, then earlier submission, then draft ID.'});
  if(url.endsWith('/audit'))return ok({seed:'b'.repeat(64),seed_commitment:'a'.repeat(64)});
  if(url.includes('/drafts?'))return ok({items:[d],next_offset:null});
  return ok(d);
 });
 vi.stubGlobal('fetch',fetcher);return{fetcher,close:()=>{hidden=false;}};
}
async function login(){await userEvent.type(screen.getByLabelText('Public username'),'studio_one');await userEvent.type(screen.getByLabelText('Account password'),'a long private passphrase!');await userEvent.click(screen.getByRole('button',{name:'Sign in'}));await screen.findByText('Account · studio_one');}
it('signs in without displaying or persisting the account token; reload requires sign-in',async()=>{
 const {fetcher}=setup();const storage=vi.spyOn(Storage.prototype,'setItem');const mounted=render(<Studio/>);await login();expect(screen.queryByLabelText('Your recovery token')).not.toBeInTheDocument();expect(document.body.textContent).not.toContain(token);expect(screen.queryByLabelText('Public username')).not.toBeInTheDocument();
 await userEvent.click(screen.getByRole('button',{name:'Load my films'}));await screen.findByRole('button',{name:/drama · Film/i});const call=fetcher.mock.calls.find(([u])=>u.includes('/drafts?'))!;expect(call[1]?.headers).toMatchObject({Authorization:'Bearer '+token});expect(storage).not.toHaveBeenCalled();mounted.unmount();render(<Studio/>);expect(screen.getByRole('button',{name:'Sign in'})).toBeInTheDocument();storage.mockRestore();
});
it('requires explicit guest claim acknowledgement and clears sensitive fields',async()=>{
 setup();render(<Studio/>);await login();await userEvent.click(screen.getByText('Claim guest films or change password'));const claim=screen.getByRole('button',{name:'Claim all guest films'});expect(claim).toBeDisabled();await userEvent.type(screen.getByLabelText('Guest token to claim'),'g'.repeat(43));await userEvent.click(screen.getByLabelText('I understand this claims all films and revokes guest access.'));await userEvent.click(claim);await screen.findByText(/Claimed 2 film/);expect(screen.getByLabelText('Guest token to claim')).toHaveValue('');
});
it('revokes all sessions on password change and clears the displayed film',async()=>{
 setup();render(<Studio/>);await login();await userEvent.click(screen.getByText('Claim guest films or change password'));await userEvent.type(screen.getByLabelText('Current password'),'a long private passphrase!');await userEvent.type(screen.getByLabelText('New password'),'another long private passphrase!');await userEvent.click(screen.getByRole('button',{name:'Change password and sign out'}));await screen.findByText(/All account sessions were revoked/);expect(screen.queryByText('Account · studio_one')).not.toBeInTheDocument();expect(screen.getByLabelText('Account password')).toHaveValue('');
});
it('uses one attempt request on retry and never loads a hidden release report',async()=>{
 const {fetcher,close}=setup();render(<Studio/>);await login();await userEvent.click(screen.getByText('Daily challenges & leaderboards'));await userEvent.click(await screen.findByRole('button',{name:'Enter challenge'}));expect(fetcher.mock.calls.some(([u])=>u.endsWith('/attempts'))).toBe(false);await userEvent.click(screen.getByRole('button',{name:'Start my one attempt'}));await userEvent.click(await screen.findByRole('button',{name:'Retry same request'}));await screen.findByText(/Your official release is submitted/);const posts=fetcher.mock.calls.filter(([u])=>u.endsWith('/attempts'));expect(posts).toHaveLength(2);expect(posts[0][1]?.body).toBe(posts[1][1]?.body);expect(Object.keys(JSON.parse(String(posts[0][1]?.body)))).toEqual(['request_id']);expect(fetcher.mock.calls.some(([u])=>u.endsWith('/result'))).toBe(false);
 close();await userEvent.click(screen.getByRole('button',{name:'Refresh draft'}));await screen.findByText('Saved report fixture reached');expect(fetcher.mock.calls.some(([u])=>u.endsWith('/result'))).toBe(true);
});
it('allows anonymous rankings but requires account for entry and waits for close to reveal audit',async()=>{
 const {close}=setup();render(<Studio/>);await userEvent.click(screen.getByText('Daily challenges & leaderboards'));expect(await screen.findByRole('button',{name:'Enter challenge'})).toBeDisabled();await userEvent.click(screen.getByRole('button',{name:'View rankings'}));await screen.findByText('Rankings unlock after closing.');expect(screen.queryByRole('button',{name:'Reveal audit seed'})).not.toBeInTheDocument();close();await userEvent.click(screen.getByRole('button',{name:'Refresh rankings'}));await screen.findByText('82/100');await userEvent.click(screen.getByRole('button',{name:'Reveal audit seed'}));await screen.findByText('b'.repeat(64));
});
it('keeps a valid account session when the current password is incorrect',async()=>{
 const {fetcher}=setup();const original=fetcher.getMockImplementation()!;fetcher.mockImplementation(async(url,init)=>url.endsWith('/password')?new Response(JSON.stringify({error:{code:'invalid_credentials',message:'Current password is incorrect.'}}),{status:401}):original(url,init));
 render(<Studio/>);await login();await userEvent.click(screen.getByText('Claim guest films or change password'));await userEvent.type(screen.getByLabelText('Current password'),'wrong');await userEvent.type(screen.getByLabelText('New password'),'another long private passphrase!');await userEvent.click(screen.getByRole('button',{name:'Change password and sign out'}));await screen.findByText('Current password is incorrect.');expect(screen.getByText('Account · studio_one')).toBeInTheDocument();expect(screen.getByLabelText('Current password')).toHaveValue('');
});
