from typing import Literal

from pydantic import BaseModel


class LiveHealth(BaseModel):
    status: Literal["ok"] = "ok"
    service: Literal["cinedraft-api"] = "cinedraft-api"
    version: str = "0.15.0"


class ReadyHealth(BaseModel):
    status: Literal["ready"] = "ready"
    database: Literal["connected"] = "connected"


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorEnvelope(BaseModel):
    error: ErrorDetail
    request_id: str
