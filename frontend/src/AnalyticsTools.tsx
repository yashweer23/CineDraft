import {useState} from 'react';
import type {StudioState} from './studioApi';
import {Modal} from './StudioParts';
export default function AnalyticsTools({s}:{s:StudioState}){
 const [confirm,setConfirm]=useState(false);const d=s.draft;
 if(!d||!s.challengeContext||s.challengeContext.challenge?.results_hidden)return null;
 const disabled=s.busy||!!s.pending||s.mustRefresh;
 return <details className="technical-record analytics-tools"><summary>Gameplay analytics &amp; practice replay</summary><p>Download the events for this film to explore completion, casting and budget decisions in the private SQL dashboard. The file contains draft choices and pseudonymous evidence IDs. Keep it private or give it to your playtest organizer.</p><button className="button-secondary" disabled={disabled} onClick={()=>void s.exportEvents()}>Download my gameplay events</button>
 {d.status==='results_available'&&<><p>Play the same genre, budget and catalog again with a fresh set of offers. The new draft is a practice film.</p><button className="button-secondary" disabled={disabled} onClick={()=>setConfirm(true)}>Replay this brief</button></>}
 {confirm&&<Modal title="Start a practice replay?" onClose={()=>setConfirm(false)}><p>This starts a separate film with the same brief and a new random seed. Your original release and challenge submission stay saved.</p><div className="studio-actions"><button className="button-secondary" onClick={()=>setConfirm(false)}>Go back</button><button className="button-primary" disabled={disabled} onClick={()=>{setConfirm(false);s.startReplay();}}>Start practice replay</button></div></Modal>}
 </details>;
}
