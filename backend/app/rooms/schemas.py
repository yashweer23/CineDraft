from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID
from pydantic import Field, SecretStr, field_validator
from app import contracts as c
from app.drafting.schemas import LiveDraft, RosterMember
import re

class Invitation(c.Contract):
    invite_code: SecretStr

    @field_validator('invite_code')
    @classmethod
    def code_shape(cls, value):
        if not re.fullmatch(r'[A-Za-z0-9_-]{43}', value.get_secret_value()):
            raise ValueError('Use a 32-byte random base64url invitation.')
        return value

class CreateRoom(Invitation, c.CreateDraftRequest):
    turn_seconds: Annotated[int, Field(strict=True, ge=30, le=180)] = 60

class JoinRoom(Invitation):
    request_id: UUID

class RoomPick(c.PickRequest):
    pass

class RoomEvent(c.Contract):
    turn: int
    seat: Literal[0, 1]
    slot: str
    person_id: UUID
    automatic: bool

class RoomView(c.Contract):
    room_id: UUID
    revision: c.Revision
    state: Literal['waiting', 'active', 'complete', 'cancelled']
    seat: Literal[0, 1]
    guest_joined: bool
    turn_seat: Literal[0, 1] | None
    turn_seconds: int
    deadline: datetime | None
    server_time: datetime
    draft: LiveDraft
    members: list[RosterMember]
    events: list[RoomEvent]
