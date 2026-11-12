import logging

from fastapi import FastAPI, HTTPException, status
from pydantic import ValidationError

from ticketing_system.api.models import (
    Ticket,
    TicketCreate,
    TicketStatus,
    TicketUpdate,
)
from ticketing_system.api.store import TicketStore
from ticketing_system.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

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
    created_ticket = store.create(
        title=ticket.title,
        description=ticket.description,
    )

    logger.info("Ticket %s created successfully", created_ticket.id)

    return created_ticket


@app.get("/tickets", response_model=list[Ticket])
def get_tickets(status: TicketStatus | None = None):
    tickets = store.get_all(status=status)

    logger.info(
        "Retrieved %s tickets | Status filter: %s",
        len(tickets),
        status.value if status is not None else "ALL",
    )

    return tickets


@app.get("/tickets/{ticket_id}", response_model=Ticket)
def get_ticket(ticket_id: int):
    ticket = store.get(ticket_id)

    if ticket is None:
        logger.warning("Ticket %s not found", ticket_id)

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket with ID {ticket_id} not found.",
        )

    logger.info("Ticket %s retrieved successfully", ticket_id)

    return ticket


@app.patch("/tickets/{ticket_id}", response_model=Ticket)
def update_ticket(ticket_id: int, updates: TicketUpdate):
    if store.get(ticket_id) is None:
        logger.warning("Cannot update ticket %s: not found", ticket_id)

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket with ID {ticket_id} not found.",
        )

    # Reject explicit null values for fields that cannot be null.
    if any(
        field in updates.model_fields_set and getattr(updates, field) is None
        for field in ("title", "description", "status")
    ):
        logger.warning(
            "Cannot update ticket %s: invalid null field",
            ticket_id,
        )

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Title, description, and status cannot be null.",
        )

    try:
        ticket = store.update(ticket_id, updates)

    except ValidationError as error:
        logger.warning(
            "Cannot update ticket %s: validation error",
            ticket_id,
        )

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=error.errors(
                include_input=False,
                include_context=False,
                include_url=False,
            ),
        ) from error

    except ValueError as error:
        logger.warning(
            "Cannot update ticket %s: %s",
            ticket_id,
            type(error).__name__,
        )

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error

    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket with ID {ticket_id} not found.",
        )

    logger.info(
        "Ticket %s updated successfully | Fields: %s",
        ticket_id,
        ", ".join(sorted(updates.model_fields_set)),
    )

    return ticket


@app.delete(
    "/tickets/{ticket_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_ticket(ticket_id: int):
    if not store.delete(ticket_id):
        logger.warning("Cannot delete ticket %s: not found", ticket_id)

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket with ID {ticket_id} not found.",
        )

    logger.info("Ticket %s soft-deleted successfully", ticket_id)


@app.post(
    "/tickets/{ticket_id}/restore",
    response_model=Ticket,
    status_code=status.HTTP_200_OK,
)
def restore_ticket(ticket_id: int):
    try:
        restored_ticket = store.restore(ticket_id)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    if restored_ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket with ID {ticket_id} not found.",
        )

    logger.info("Ticket %s restored successfully", ticket_id)

    return restored_ticket
