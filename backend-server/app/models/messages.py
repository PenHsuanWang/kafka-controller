from pydantic import BaseModel


class MessageRecord(BaseModel):
    topic: str
    partition: int
    offset: int
    timestamp: int
    key: bytes | None
    value: bytes | None
