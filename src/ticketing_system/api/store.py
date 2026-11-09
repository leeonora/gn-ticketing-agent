from datetime import datetime, timezone

from ticketing_system.api.models import Ticket, TicketStatus, TicketUpdate


class TicketStore:
    def __init__(self):
        self.tickets: dict[int, Ticket] = {}
        self.next_id = 1

    def create(self, title: str, description: str) -> Ticket:
        ticket = Ticket(
            id=self.next_id,
            title=title,
            description=description,
            created=datetime.now(timezone.utc),
            status=TicketStatus.OPEN,
            resolution=None,
        )

        self.tickets[ticket.id] = ticket
        self.next_id += 1

        return ticket

    def get(self, ticket_id: int) -> Ticket | None:
        return self.tickets.get(ticket_id)

    def get_all(
        self,
        status: TicketStatus | None = None,
    ) -> list[Ticket]:
        tickets = list(self.tickets.values())

        if status is not None:
            tickets = [
                ticket for ticket in tickets
                if ticket.status == status
            ]

        return tickets
    
    def update(
        self, ticket_id: int, updates: TicketUpdate
    ) -> Ticket | None:
        ticket = self.get(ticket_id)

        if ticket is None:
            return None

        # Extract only explicitly provided fields.
        update_data = updates.model_dump(exclude_unset=True)

        # Validate the requested status against our allowed values.
        if "status" in update_data:
            new_status = update_data["status"]

            if new_status not in [status.value for status in TicketStatus]:
                valid_statuses = ", ".join(
                    status.value for status in TicketStatus
                )
                raise ValueError(
                    f"Invalid status '{new_status}'. "
                    f"Valid statuses are: {valid_statuses}."
                )

        # Combine the existing ticket with the requested changes.
        ticket_data = ticket.model_dump()
        ticket_data.update(update_data)

        # Validate the complete updated ticket.
        updated_ticket = Ticket.model_validate(ticket_data)

        # Save only after validation succeeds.
        self.tickets[ticket_id] = updated_ticket

        return updated_ticket

    
    def delete(self, ticket_id: int) -> bool:
        if ticket_id not in self.tickets:
            return False

        del self.tickets[ticket_id]
        return True
