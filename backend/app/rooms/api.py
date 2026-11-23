import asyncio
import json
from uuid import UUID
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from starlette.concurrency import run_in_threadpool
from sqlalchemy.exc import SQLAlchemyError
from app import contracts as c
from app.drafting.api import Token, call
from app.drafting.auth import token_hash
from app.drafting.errors import DraftProblem
from app.rooms import schemas as w, service

router = APIRouter(prefix='/api/v1/rooms', tags=['Cooperative rooms'])

@router.post('', response_model=w.RoomView, status_code=201)
def create(request: Request, token: Token, body: w.CreateRoom):
    return call(request, service.create, token, body)

@router.get('/{room_id}', response_model=w.RoomView)
def read(request: Request, token: Token, room_id: UUID):
    return call(request, service.read, token, room_id)

@router.post('/{room_id}/join', response_model=w.RoomView)
def join(request: Request, token: Token, room_id: UUID, body: w.JoinRoom):
    return call(request, service.join, token, room_id, body)

@router.post('/{room_id}/picks', response_model=w.RoomView)
def pick(request: Request, token: Token, room_id: UUID, body: w.RoomPick):
    return call(request, service.command, token, room_id, 'pick', body)

@router.post('/{room_id}/start', response_model=w.RoomView)
def start(request: Request, token: Token, room_id: UUID, body: c.MutationRequest):
    return call(request, service.command, token, room_id, 'start', body)

@router.post('/{room_id}/cancel', response_model=w.RoomView)
def cancel(request: Request, token: Token, room_id: UUID, body: c.MutationRequest):
    return call(request, service.command, token, room_id, 'cancel', body)

@router.websocket('/{room_id}/live')
async def live(ws: WebSocket, room_id: UUID):
    # Credentials travel only in the first frame, never a URL or subprotocol.
    if ws.headers.get('origin') not in ws.app.state.room_origins or ws.query_params:
        await ws.close(code=1008); return
    await ws.accept()
    try:
        raw = await asyncio.wait_for(ws.receive_text(), timeout=5)
        if len(raw) > 256:
            await ws.close(code=1008); return
        hello = json.loads(raw)
        if not isinstance(hello, dict) or set(hello) != {'token'} or not isinstance(hello['token'], str):
            await ws.close(code=1008); return
        token = hello['token']; token_hash(token)
        while True:
            state = await run_in_threadpool(service.read, ws.app.state.database.engine, token, room_id)
            await ws.send_json({'type': 'room', 'room': state})
            # Read-only stream; polling storage works across workers and restarts.
            # Receiving in parallel with the interval also detects closed browsers promptly.
            try:
                await asyncio.wait_for(ws.receive_text(), timeout=1)
                await ws.close(code=1008); return
            except asyncio.TimeoutError:
                pass
    except WebSocketDisconnect:
        return
    except (DraftProblem, ValueError, TypeError, asyncio.TimeoutError):
        await ws.close(code=1008)
    except SQLAlchemyError:
        await ws.close(code=1013)
