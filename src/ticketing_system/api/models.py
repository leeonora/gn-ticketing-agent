from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class TicketStatus(str, Enum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


# Complete ticket stored + returned by API
class Ticket(BaseModel):
    id: int
    title: str = Field(min_length=1)
    description: str
    created: datetime
    status: TicketStatus = TicketStatus.OPEN
    resolution: str | None = None
    deleted: bool = False


# Validates user data
class TicketCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    description: str


# Defines which fields can be updated
class TicketUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1)
    description: str | None = None
    status: str | None = None
    resolution: str | None = None
