from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


class TicketStatus(str, Enum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"

# complete ticket stored + returned by api
class Ticket(BaseModel):
    id: int
    title: str = Field(min_length=1)
    description: str
    created: datetime
    status: TicketStatus = TicketStatus.OPEN
    resolution: str | None = None

# validates user data
class TicketCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    description: str

# defines which fields can be updated
class TicketUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1)
    description: str | None = None
    status: str | None = None
    resolution: str | None = None
