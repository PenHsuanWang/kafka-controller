# app/models/ws_events.py
from typing import Any, Literal
from pydantic import BaseModel

class WSEvent(BaseModel):
    type: Literal["group.snapshot", "group.rates"]
    payload: Any
