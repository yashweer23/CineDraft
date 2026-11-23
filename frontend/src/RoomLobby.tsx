import { useEffect, useRef, useState } from 'react';
import { api, ApiError, type Member, type Pending } from './studioApi';
import type { Draft } from './DraftInspector';
import { usd as money, label } from './StudioParts';

export type Room = {
  room_id: string; revision: number; state: 'waiting'|'active'|'complete'|'cancelled';
  seat: 0|1; guest_joined: boolean; turn_seat: 0|1|null; turn_seconds: number;
  deadline: string|null; server_time: string; draft: Draft; members: Member[];
  events: {turn: number; seat: number; slot: string; person_id: string; automatic: boolean}[];
};
export function invitation() {
  return btoa(String.fromCharCode(...crypto.getRandomValues(new Uint8Array(32))))
    .replaceAll('+','-').replaceAll('/','_').replaceAll('=','');
}
export function newer(current: Room|null, incoming: Room) {
  if (!current || current.room_id !== incoming.room_id) return incoming;
  if (incoming.revision < current.revision || incoming.draft.revision < current.draft.revision) return current;
  return incoming;
}

export default function RoomLobby() {
  const [token,setToken]=useState(''),[proof,setProof]=useState(''),[roomId,setRoomId]=useState('');
  const [invite,setInvite]=useState(''),[genre,setGenre]=useState('thriller'),[tier,setTier]=useState('blockbuster');
  const [room,setRoom]=useState<Room|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  const [pending,setPending]=useState<Pending|null>(null),[connection,setConnection]=useState('Offline');
  const [clock,setClock]=useState(Date.now()),[turnSeconds,setTurnSeconds]=useState(60);
  const lock=useRef(false),alive=useRef(true),offset=useRef(0),epoch=useRef(0);
  useEffect(()=>{alive.current=true;return()=>{alive.current=false;};},[]);
  function accept(value: Room) {
    if (!value?.room_id || !value.draft || !Array.isArray(value.members)) throw new ApiError('Unreadable room response.',true);
    offset.current=Date.parse(value.server_time)-Date.now();
    if(alive.current) {setRoom(old=>newer(old,value));setRoomId(value.room_id);}
  }
  async function refresh(id=room?.room_id,cap=token) {
    if(!id)return;
    const generation=epoch.current;
    const value=await api<Room>('/api/v1/rooms/'+id,cap);
    if(generation===epoch.current)accept(value);
  }
  useEffect(()=>{
    if(!pending)return;
    const warn=(event:BeforeUnloadEvent)=>{event.preventDefault();event.returnValue='';};
    window.addEventListener('beforeunload',warn);return()=>window.removeEventListener('beforeunload',warn);
  },[pending]);
  useEffect(()=>{
    if(!room?.room_id||!token)return;
    const id=room.room_id;
    let stopped=false,socket:WebSocket|undefined,timer:ReturnType<typeof setTimeout>,attempt=0;
    let polling=false;
    const update=(value:Room)=>{if(!stopped)accept(value);};
    const connect=()=>{
      if(stopped)return;
      setConnection('Connecting');
      const url=new URL(`/api/v1/rooms/${id}/live`,window.location.href);
      url.protocol=url.protocol==='https:'?'wss:':'ws:';
      socket=new WebSocket(url);
      socket.onopen=()=>{socket?.send(JSON.stringify({token}));};
      socket.onmessage=event=>{
        try {const value=JSON.parse(event.data);if(value.type==='room'){update(value.room);attempt=0;setConnection('Live');}}
        catch {setConnection('Refresh needed');}
      };
      socket.onclose=()=>{
        if(stopped)return;
        setConnection('Reconnecting · HTTP refresh available');
        timer=setTimeout(connect,Math.min(8000,1000*2**attempt++));
      };
      socket.onerror=()=>socket?.close();
    };
    connect();
    // Fallback refresh also repairs missed messages. GET cannot make a pick.
    const poll=setInterval(()=>{
      if(polling||stopped||socket?.readyState===WebSocket.OPEN)return;
      polling=true;
      void api<Room>('/api/v1/rooms/'+id,token).then(update).catch(()=>{}).finally(()=>{polling=false;});
    },3000);
    const tick=setInterval(()=>setClock(Date.now()),250);
    return()=>{stopped=true;clearTimeout(timer);clearInterval(poll);clearInterval(tick);socket?.close();};
  },[room?.room_id,token]);

  async function send(command:Pending) {
    if(lock.current)return;
    lock.current=true;setBusy(true);setError('');
    try {
      let receipt:Room;
      try {receipt=await api<Room>(command.path,token,command.body);accept(receipt);}
      catch(e){if(alive.current)setPending(e instanceof ApiError&&e.uncertain?command:null);throw e;}
      if(alive.current)setPending(null);
      await refresh(receipt.room_id);
    } catch(e){
      if(alive.current)setError((e as Error).message);
      if(e instanceof ApiError && e.status===409)await refresh().catch(()=>{});
    } finally {lock.current=false;if(alive.current)setBusy(false);}
  }
  async function session(makeNew:boolean) {
    if(lock.current||pending)return;
    lock.current=true;setBusy(true);setError('');
    try {
      let cap=proof.trim();
      if(makeNew)cap=(await api<{access_token:string}>('/api/v1/sessions','',{})).access_token;
      else await api('/api/v1/drafts?limit=1',cap);
      if(alive.current){epoch.current++;setToken(cap);setRoom(null);setRoomId('');setInvite('');}
    }catch(e){if(alive.current)setError((e as Error).message);}
    finally{lock.current=false;if(alive.current)setBusy(false);}
  }
  function act(name:string,extra:Record<string,unknown>={}) {
    if(!room||pending)return;
    void send({path:`/api/v1/rooms/${room.room_id}/${name}`,body:{request_id:crypto.randomUUID(),expected_revision:room.revision,...extra}});
  }
  const disabled=busy||!!pending;
  const remaining=room?.deadline?Math.min(room.turn_seconds,Math.max(0,Math.ceil((Date.parse(room.deadline)-clock-offset.current)/1000))):0;
  const mine=room?.state==='active'&&room.turn_seat===room.seat;
  return <section id="rooms" className="room-panel" aria-labelledby="rooms-title">
    <p className="eyebrow">Two players / One film</p><h2 id="rooms-title">Co-op draft room</h2>
    <p>Alternate eight picks with a partner. Share one budget and hire each person once. A missed turn picks the cheapest legal card on offer. The eighth pick locks your film for release.</p>
    <p className="small muted">No rerolls or recasts in this mode. The host owns the completed film; your partner can follow the roster here. Rooms use their own session controls.</p>
    {error&&<p className="callout" role="alert">{error}</p>}
    {!token?<div className="room-controls"><button className="button-primary" disabled={disabled} onClick={()=>void session(true)}>New room player</button>
      <label>Existing recovery or account token<input type="password" autoComplete="off" value={proof} onChange={e=>setProof(e.target.value)}/></label>
      <button className="button-secondary" disabled={disabled||!proof.trim()} onClick={()=>void session(false)}>Restore room player</button></div>:
      <><details><summary>Save your private player token</summary><p className="small">Keep this privately to reconnect. Share only your room ID and invitation with your partner.</p><code className="room-secret">{token}</code></details>
      {!room?<><div className="room-controls">
        <label>Film genre<select value={genre} onChange={e=>setGenre(e.target.value)} disabled={disabled}>{['thriller','drama','comedy','action','crime','horror','romance','science_fiction'].map(g=><option key={g} value={g}>{label(g)}</option>)}</select></label>
        <label>Shared budget<select value={tier} onChange={e=>setTier(e.target.value)} disabled={disabled}><option value="blockbuster">Blockbuster · $200M</option><option value="studio">Studio · $50M</option><option value="indie">Indie · $10M</option></select></label>
        <label>Seconds per turn<select value={turnSeconds} onChange={e=>setTurnSeconds(Number(e.target.value))} disabled={disabled}>{[30,60,120,180].map(n=><option key={n}>{n}</option>)}</select></label>
        <button className="button-primary" disabled={disabled} onClick={()=>{const code=invitation();setInvite(code);void send({path:'/api/v1/rooms',body:{request_id:crypto.randomUUID(),genre_id:genre,tier,turn_seconds:turnSeconds,invite_code:code}});}}>Create co-op room</button>
      </div><div className="room-controls">
        <label>Room ID<input value={roomId} onChange={e=>setRoomId(e.target.value)} disabled={disabled}/></label>
        <label>Invitation code<input autoComplete="off" value={invite} onChange={e=>setInvite(e.target.value)} disabled={disabled}/></label>
        <button className="button-secondary" disabled={disabled||!roomId.trim()||!invite.trim()} onClick={()=>void send({path:`/api/v1/rooms/${roomId.trim()}/join`,body:{request_id:crypto.randomUUID(),invite_code:invite.trim()}})}>Join partner</button>
        <button className="button-secondary" disabled={disabled||!roomId.trim()} onClick={()=>void refresh(roomId.trim()).catch(e=>setError(e.message))}>Reopen saved room</button>
      </div></>:
      <><div className="room-status"><p role="status">{connection} · You are {room.seat===0?'the host':'the partner'} · {room.state}</p><p className="room-secret">Room ID: <strong>{room.room_id}</strong></p>
        {room.seat===0&&room.state==='waiting'&&invite&&<p className="room-secret">Invitation: <strong>{invite}</strong></p>}
        <button className="button-secondary" disabled={busy} onClick={()=>void refresh().catch(e=>setError(e.message))}>Refresh room</button></div>
        {room.state==='waiting'&&<><p>{room.guest_joined?'Your partner has joined. The host can start.':'Waiting for your partner. Send the room ID and invitation privately.'}</p>{room.seat===0&&<button className="button-primary" disabled={disabled||!room.guest_joined} onClick={()=>act('start')}>Start alternating picks</button>}</>}
        {room.state==='active'&&<><h3>{mine?'Your turn':'Partner’s turn'} · {label(room.draft.current_offer?.slot??'')}</h3><p>Time left: <strong>{remaining}s</strong>{remaining===0?' · Waiting for the server’s automatic pick.':''}</p>
          <p>Shared hiring balance: <strong>{money(room.draft.budget.talent_remaining_usd)}</strong></p>
          <div className="room-cards">{room.draft.current_offer?.candidates.map(candidate=><article className="room-card" key={candidate.card.person_id}><p className="eyebrow">{label(candidate.card.role)}</p><h4>{candidate.card.name}</h4><p>{money(candidate.card.hiring_fee_usd)}</p><p className="small">Talent {candidate.card.talent_strength??'—'} · Genre fit {candidate.card.genre_fit??'—'}</p><ul>{candidate.card.notable_works.slice(0,3).map(work=><li key={work.movie_id}>{work.title}</li>)}</ul>{candidate.blocked_reason&&<p>{candidate.blocked_reason}</p>}<button className="button-primary" disabled={disabled||!mine||remaining===0||!candidate.selectable} onClick={()=>act('picks',{offer_id:room.draft.current_offer!.offer_id,person_id:candidate.card.person_id})}>Hire {candidate.card.name}</button></article>)}</div></>}
        {room.members.length>0&&<><h3>Our film · {room.members.length}/8 hired</h3><ol className="room-roster">{room.members.map((member,i)=><li key={member.slot}><span>{label(member.slot)} · <strong>{member.card.name}</strong></span><span>{money(member.locked_fee_usd)}{room.events[i]?.automatic?' · Auto-picked':''}</span></li>)}</ol></>}
        {room.state==='complete'&&<div className="callout"><h3>Your film is locked.</h3><p>The host can restore the same player token in <a href="#studio">Your studio</a>, load saved films and open <code className="room-secret">{room.draft.draft_id}</code> to run its release. Shared roster choices are preserved.</p></div>}
        {room.seat===0&&['waiting','active'].includes(room.state)&&<button className="button-secondary" disabled={disabled} onClick={()=>{if(window.confirm('Cancel this shared film for both players?'))act('cancel');}}>Cancel shared film</button>}
      </>}
      <button className="button-secondary" disabled={disabled} onClick={()=>{if(window.confirm('Close this screen? Save your token, room ID and invitation first. The server timer keeps running.')){epoch.current++;setToken('');setRoom(null);setProof('');setInvite('');setRoomId('');}}}>Close room screen</button>
      </>}
    {pending&&<div className="callout" role="alert"><p>The last command has an uncertain outcome. Retry the exact request below. Save it with your private token before leaving.</p><button className="button-primary" disabled={busy} onClick={()=>void send(pending)}>Retry same room request</button><details><summary>Exact request for recovery</summary><pre>{JSON.stringify(pending,null,2)}</pre></details></div>}
  </section>;
}
