from fastapi import FastAPI, HTTPException, status
from pydantic import ValidationError

from ticketing_system.api.models import (
    Ticket,
    TicketCreate,
    TicketStatus,
    TicketUpdate,
)
from ticketing_system.api.store import TicketStore

app = FastAPI(
    title="Mock Ticketing API",
    description="A REST API for managing support tickets.",
    version="0.1.0",
)

store = TicketStore()


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post(
    "/tickets",
    response_model=Ticket,
    status_code=status.HTTP_201_CREATED,
)
def create_ticket(ticket: TicketCreate):
    return store.create(
        title=ticket.title,
        description=ticket.description,
    )


@app.get("/tickets", response_model=list[Ticket])
def get_tickets(status: TicketStatus | None = None):
    return store.get_all(status=status)


@app.get("/tickets/{ticket_id}", response_model=Ticket)
def get_ticket(ticket_id: int):
    ticket = store.get(ticket_id)

    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket with ID {ticket_id} not found.",
        )

    return ticket


@app.patch("/tickets/{ticket_id}", response_model=Ticket)
def update_ticket(ticket_id: int, updates: TicketUpdate):
    if store.get(ticket_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket with ID {ticket_id} not found.",
        )

    # Reject explicit null values for fields that cannot be null.
    if any(
        field in updates.model_fields_set and getattr(updates, field) is None
        for field in ("title", "description", "status")
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Title, description, and status cannot be null.",
        )

    try:
        ticket = store.update(ticket_id, updates)

    except ValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=error.errors(
                include_input=False,
                include_context=False,
                include_url=False,
            ),
        ) from error

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error

    return ticket


@app.delete(
    "/tickets/{ticket_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_ticket(ticket_id: int):
    if not store.delete(ticket_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket with ID {ticket_id} not found.",
        )
