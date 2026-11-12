from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from time import sleep

from ticketing_system.api import store as store_module
from ticketing_system.api.models import TicketUpdate
from ticketing_system.api.store import TicketStore


def test_concurrent_creates_keep_every_ticket(monkeypatch):
    store = TicketStore()
    ticket_model = store_module.Ticket
    start = Barrier(8)

    def slow_ticket(**kwargs):
        # Widen the interval after reading next_id to expose an unlocked race.
        sleep(0.005)
        return ticket_model(**kwargs)

    monkeypatch.setattr(store_module, "Ticket", slow_ticket)

    def create(index):
        start.wait(timeout=5)
        return store.create(str(index), "Concurrent create")

    with ThreadPoolExecutor(max_workers=8) as pool:
        created = list(pool.map(create, range(8)))

    assert sorted(ticket.id for ticket in created) == list(range(1, 9))
    assert {ticket.title for ticket in store.get_all()} == {str(i) for i in range(8)}
    assert store.next_id == 9


def test_concurrent_updates_do_not_lose_other_fields(monkeypatch):
    store = TicketStore()
    ticket = store.create("Original", "Original")
    validate = store_module.Ticket.model_validate
    start = Barrier(2)

    def slow_validate(data):
        # Without a lock, both calls merge against the same stale ticket.
        sleep(0.01)
        return validate(data)

    monkeypatch.setattr(store_module.Ticket, "model_validate", slow_validate)

    def update(changes):
        start.wait(timeout=5)
        return store.update(ticket.id, TicketUpdate(**changes))

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(
            pool.map(
                update, [{"title": "New title"}, {"description": "New description"}]
            )
        )

    result = store.get(ticket.id)
    assert result.title == "New title"
    assert result.description == "New description"
