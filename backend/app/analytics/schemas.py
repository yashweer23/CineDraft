from datetime import datetime
from typing import Literal,Annotated
from uuid import UUID
from pydantic import Field, AwareDatetime
from app.contracts import Contract,CreateDraftRequest,Money
from app.domain import Slot

class ReplayRequest(Contract):request_id:UUID
class ReplayBrief(CreateDraftRequest):
    source_id:UUID  # Server-only namespace in creation receipt digest.
    purpose:Literal['replay']='replay'

class Event(Contract):
    event_key:str
    kind:Literal['start','replay_start','pick','reroll','preview_recast','cancel_recast','confirm_recast','finalize','abandon','release','release_failed','whatif']
    at:AwareDatetime
    revision:int=Field(ge=0)
    slot:Slot|None=None
    person:str|None=None
    offer:str|None=None
    fee:Money|None=None
    score:int|None=Field(default=None,ge=0,le=100)
    profit:int|None=None

class Opportunity(Contract):
    kind:Literal['pick','recast']
    offer:str
    person:str
    name:str
    slot:Slot
    at:AwareDatetime
    event_key:str   # Receipt that first issued this offer.

class Stream(Contract):
    schema_version:Literal['gameplay-events-1.0']='gameplay-events-1.0'
    origin:Literal['owner_export','generated_demo']='owner_export'
    session_key:str
    started:AwareDatetime
    captured:AwareDatetime
    genre:str
    tier:str
    catalog:str
    rules:str
    scoring:str
    simulation:str
    fixture:bool
    mode:Literal['practice','closed_challenge']
    total:Money
    allowance:Money
    reserve:Money
    events:list[Event]
    opportunities:list[Opportunity]
