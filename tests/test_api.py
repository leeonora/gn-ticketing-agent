import pytest
from fastapi.testclient import TestClient

import ticketing_system.api.main as api_main
from ticketing_system.api.store import TicketStore


@pytest.fixture
def client(monkeypatch):
    # Give every test its own empty ticket store.
    monkeypatch.setattr(api_main, "store", TicketStore())

    with TestClient(api_main.app) as test_client:
        yield test_client


### Testing ticket creation


def test_create_ticket(client):
    response = client.post(
        "/tickets",
        json={
            "title": "Keyboard not working",
            "description": "Keyboard is unresponsive.",
        },
    )

    assert response.status_code == 201

    ticket = response.json()

    assert ticket["id"] == 1
    assert ticket["title"] == "Keyboard not working"
    assert ticket["status"] == "OPEN"
    assert ticket["resolution"] is None
    assert ticket["deleted"] is False
    assert "created" in ticket


### Testing ticket retrieval


def test_get_ticket(client):
    created = client.post(
        "/tickets",
        json={
            "title": "Monitor flickering",
            "description": "Screen flickers occasionally.",
        },
    ).json()

    response = client.get(f"/tickets/{created['id']}")

    assert response.status_code == 200
    assert response.json()["title"] == "Monitor flickering"


def test_get_nonexistent_ticket(client):
    response = client.get("/tickets/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Ticket with ID 999 not found."


### Testing ticket updates


def test_update_ticket(client):
    created = client.post(
        "/tickets",
        json={
            "title": "Broken keyboard",
            "description": "Keyboard is unresponsive.",
        },
    ).json()

    response = client.patch(
        f"/tickets/{created['id']}",
        json={
            "status": "RESOLVED",
            "resolution": "Replaced faulty cable",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "RESOLVED"
    assert response.json()["resolution"] == "Replaced faulty cable"


def test_invalid_status(client):
    created = client.post(
        "/tickets",
        json={
            "title": "Broken keyboard",
            "description": "Keyboard is unresponsive.",
        },
    ).json()

    response = client.patch(
        f"/tickets/{created['id']}",
        json={"status": "PROGRESS"},
    )

    assert response.status_code == 422

    detail = response.json()["detail"]

    assert "PROGRESS" in detail
    assert "OPEN" in detail
    assert "RESOLVED" in detail
    assert "CLOSED" in detail

    # Invalid updates should not change the existing ticket.
    unchanged = client.get(f"/tickets/{created['id']}")
    assert unchanged.json()["status"] == "OPEN"


def test_update_nonexistent_ticket(client):
    response = client.patch(
        "/tickets/999",
        json={"status": "CLOSED"},
    )

    assert response.status_code == 404


@pytest.mark.parametrize("resolution", [None, "", "   "])
def test_resolving_requires_resolution_note(client, resolution):
    created = client.post(
        "/tickets",
        json={"title": "Broken keyboard", "description": "Keyboard is unresponsive."},
    ).json()
    ticket_id = created["id"]

    payload = {"status": "RESOLVED"}
    if resolution is not None:
        payload["resolution"] = resolution

    response = client.patch(f"/tickets/{ticket_id}", json=payload)

    assert response.status_code == 422
    assert "resolution note is required" in response.json()["detail"]

    unchanged = client.get(f"/tickets/{ticket_id}").json()
    assert unchanged["status"] == "OPEN"
    assert unchanged["resolution"] is None


def test_cannot_remove_resolution_note_from_resolved_ticket(client):
    created = client.post(
        "/tickets",
        json={"title": "Broken keyboard", "description": "Keyboard is unresponsive."},
    ).json()
    ticket_id = created["id"]
    resolved = client.patch(
        f"/tickets/{ticket_id}",
        json={"status": "RESOLVED", "resolution": "Replaced faulty cable"},
    )
    assert resolved.status_code == 200

    response = client.patch(f"/tickets/{ticket_id}", json={"resolution": "   "})

    assert response.status_code == 422
    unchanged = client.get(f"/tickets/{ticket_id}").json()
    assert unchanged["status"] == "RESOLVED"
    assert unchanged["resolution"] == "Replaced faulty cable"


def test_resolved_ticket_retains_note_on_unrelated_update(client):
    created = client.post(
        "/tickets",
        json={"title": "Broken keyboard", "description": "Keyboard is unresponsive."},
    ).json()
    ticket_id = created["id"]
    client.patch(
        f"/tickets/{ticket_id}",
        json={"status": "RESOLVED", "resolution": "Replaced faulty cable"},
    )

    response = client.patch(f"/tickets/{ticket_id}", json={"title": "Fixed keyboard"})

    assert response.status_code == 200
    assert response.json()["status"] == "RESOLVED"
    assert response.json()["resolution"] == "Replaced faulty cable"


def test_nonresolved_ticket_does_not_require_resolution_note(client):
    created = client.post(
        "/tickets",
        json={"title": "Broken keyboard", "description": "Keyboard is unresponsive."},
    ).json()

    response = client.patch(f"/tickets/{created['id']}", json={"status": "CLOSED"})

    assert response.status_code == 200
    assert response.json()["status"] == "CLOSED"
    assert response.json()["resolution"] is None


### Testing soft deletion


def test_delete_ticket(client):
    created = client.post(
        "/tickets",
        json={
            "title": "Broken mouse",
            "description": "Mouse is disconnected.",
        },
    ).json()

    ticket_id = created["id"]

    response = client.delete(f"/tickets/{ticket_id}")

    assert response.status_code == 204
    assert response.content == b""

    # Deleted ticket is hidden from normal retrieval.
    response = client.get(f"/tickets/{ticket_id}")
    assert response.status_code == 404

    # The ticket still exists in storage.
    stored_ticket = api_main.store.tickets[ticket_id]
    assert stored_ticket.deleted is True
    assert stored_ticket.title == "Broken mouse"


def test_deleted_ticket_excluded_from_list(client):
    first = client.post(
        "/tickets",
        json={
            "title": "Broken keyboard",
            "description": "Keyboard is unresponsive.",
        },
    ).json()

    second = client.post(
        "/tickets",
        json={
            "title": "Broken mouse",
            "description": "Mouse is disconnected.",
        },
    ).json()

    client.delete(f"/tickets/{first['id']}")

    response = client.get("/tickets")
    assert response.status_code == 200
    assert [ticket["id"] for ticket in response.json()] == [second["id"]]

    # Status filtering should also exclude deleted tickets.
    response = client.get("/tickets", params={"status": "OPEN"})
    assert response.status_code == 200
    assert [ticket["id"] for ticket in response.json()] == [second["id"]]


def test_cannot_update_deleted_ticket(client):
    created = client.post(
        "/tickets",
        json={
            "title": "Broken keyboard",
            "description": "Keyboard is unresponsive.",
        },
    ).json()

    ticket_id = created["id"]
    client.delete(f"/tickets/{ticket_id}")

    response = client.patch(
        f"/tickets/{ticket_id}",
        json={"status": "CLOSED"},
    )

    assert response.status_code == 404
    assert api_main.store.tickets[ticket_id].status.value == "OPEN"


def test_delete_nonexistent_ticket(client):
    response = client.delete("/tickets/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Ticket with ID 999 not found."


def test_delete_already_deleted_ticket(client):
    created = client.post(
        "/tickets",
        json={
            "title": "Broken keyboard",
            "description": "Keyboard is unresponsive.",
        },
    ).json()

    ticket_id = created["id"]

    assert client.delete(f"/tickets/{ticket_id}").status_code == 204

    response = client.delete(f"/tickets/{ticket_id}")

    assert response.status_code == 404


### Testing restoration


def test_restore_deleted_ticket(client):
    created = client.post(
        "/tickets",
        json={
            "title": "Broken keyboard",
            "description": "Keyboard is unresponsive.",
        },
    ).json()

    ticket_id = created["id"]

    # Resolve the ticket before deleting it.
    client.patch(
        f"/tickets/{ticket_id}",
        json={
            "status": "RESOLVED",
            "resolution": "Replaced faulty cable",
        },
    )

    client.delete(f"/tickets/{ticket_id}")

    response = client.post(f"/tickets/{ticket_id}/restore")

    assert response.status_code == 200

    restored = response.json()

    assert restored["id"] == ticket_id
    assert restored["title"] == "Broken keyboard"
    assert restored["description"] == "Keyboard is unresponsive."
    assert restored["status"] == "RESOLVED"
    assert restored["resolution"] == "Replaced faulty cable"
    assert restored["created"] == created["created"]
    assert restored["deleted"] is False

    # The restored ticket is visible again.
    response = client.get(f"/tickets/{ticket_id}")
    assert response.status_code == 200
    assert response.json() == restored


def test_restore_nonexistent_ticket(client):
    response = client.post("/tickets/999/restore")

    assert response.status_code == 404
    assert response.json()["detail"] == "Ticket with ID 999 not found."


def test_restore_active_ticket(client):
    created = client.post(
        "/tickets",
        json={
            "title": "Broken keyboard",
            "description": "Keyboard is unresponsive.",
        },
    ).json()

    response = client.post(f"/tickets/{created['id']}/restore")

    assert response.status_code == 409
    assert response.json()["detail"] == (
        f"Ticket with ID {created['id']} is not deleted."
    )


### Testing filtering


def test_filter_tickets_by_status(client):
    first = client.post(
        "/tickets",
        json={
            "title": "Broken keyboard",
            "description": "Keyboard is unresponsive.",
        },
    ).json()

    second = client.post(
        "/tickets",
        json={
            "title": "Monitor flickering",
            "description": "Screen flickers.",
        },
    ).json()

    client.patch(
        f"/tickets/{second['id']}",
        json={"status": "RESOLVED", "resolution": "Replaced monitor cable"},
    )

    response = client.get("/tickets", params={"status": "OPEN"})

    assert response.status_code == 200

    tickets = response.json()

    assert len(tickets) == 1
    assert tickets[0]["id"] == first["id"]
    assert tickets[0]["status"] == "OPEN"


### Testing request validation


def test_create_ticket_with_empty_title(client):
    response = client.post(
        "/tickets",
        json={
            "title": "",
            "description": "Something is broken.",
        },
    )

    assert response.status_code == 422


def test_update_with_null_description(client):
    created = client.post(
        "/tickets",
        json={
            "title": "Broken keyboard",
            "description": "Keyboard is unresponsive.",
        },
    ).json()

    response = client.patch(
        f"/tickets/{created['id']}",
        json={"description": None},
    )

    assert response.status_code == 422

    unchanged = client.get(f"/tickets/{created['id']}").json()

    assert unchanged["description"] == "Keyboard is unresponsive."
