from datetime import UTC, datetime
from threading import RLock

from ticketing_system.api.models import Ticket, TicketStatus, TicketUpdate


class TicketStore:
    def __init__(self):
        self.tickets: dict[int, Ticket] = {}
        self.next_id = 1
        # Updates/deletes call get() while holding this same lock.
        self._lock = RLock()

    def create(self, title: str, description: str) -> Ticket:
        with self._lock:
            ticket = Ticket(
                id=self.next_id,
                title=title,
                description=description,
                created=datetime.now(UTC),
                status=TicketStatus.OPEN,
                resolution=None,
            )

            self.tickets[ticket.id] = ticket
            self.next_id += 1

            return ticket

    def get(self, ticket_id: int) -> Ticket | None:
        with self._lock:
            ticket = self.tickets.get(ticket_id)

            # Deleted tickets should be invisible to normal retrieval.
            if ticket is None or ticket.deleted:
                return None

            return ticket

    def get_all(
        self,
        status: TicketStatus | None = None,
    ) -> list[Ticket]:
        with self._lock:
            # Exclude deleted tickets from normal listings.
            tickets = [ticket for ticket in self.tickets.values() if not ticket.deleted]

            if status is not None:
                tickets = [ticket for ticket in tickets if ticket.status == status]

            return tickets

    def update(self, ticket_id: int, updates: TicketUpdate) -> Ticket | None:
        with self._lock:
            ticket = self.get(ticket_id)

            if ticket is None:
                return None

            # Extract only explicitly provided fields.
            update_data = updates.model_dump(exclude_unset=True)

            # Validate the requested status against our allowed values.
            if "status" in update_data:
                new_status = update_data["status"]

                if new_status not in [status.value for status in TicketStatus]:
                    valid_statuses = ", ".join(status.value for status in TicketStatus)
                    raise ValueError(
                        f"Invalid status '{new_status}'. "
                        f"Valid statuses are: {valid_statuses}."
                    )

            # Combine the existing ticket with the requested changes.
            ticket_data = ticket.model_dump()
            ticket_data.update(update_data)

            # A resolved ticket must have a meaningful resolution note.
            if ticket_data["status"] == TicketStatus.RESOLVED and (
                not isinstance(ticket_data["resolution"], str)
                or not ticket_data["resolution"].strip()
            ):
                raise ValueError(
                    "A resolution note is required when setting a ticket's "
                    "status to RESOLVED."
                )

            # Validate the complete updated ticket.
            updated_ticket = Ticket.model_validate(ticket_data)

            # save only after validation succeeds.
            self.tickets[ticket_id] = updated_ticket

            return updated_ticket

    def delete(self, ticket_id: int) -> bool:
        with self._lock:
            ticket = self.get(ticket_id)

            if ticket is None:
                return False

            # Replace the record so concurrent responses retain a stable snapshot.
            self.tickets[ticket_id] = ticket.model_copy(update={"deleted": True})
            return True

    def restore(self, ticket_id: int) -> Ticket | None:
        with self._lock:
            # Access storage directly because get() hides deleted tickets.
            ticket = self.tickets.get(ticket_id)

            if ticket is None:
                return None
            if not ticket.deleted:
                raise ValueError(f"Ticket with ID {ticket_id} is not deleted.")

            restored = ticket.model_copy(update={"deleted": False})
            self.tickets[ticket_id] = restored
            return restored
