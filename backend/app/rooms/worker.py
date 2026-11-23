import asyncio
import logging
from starlette.concurrency import run_in_threadpool
from app.rooms.service import advance_due

async def sweep(engine):
    while True:
        await asyncio.sleep(1)
        try:
            await run_in_threadpool(advance_due, engine)
        except Exception:
            logging.getLogger('cinedraft').error('Room deadline sweep unavailable; check database and migration.')
