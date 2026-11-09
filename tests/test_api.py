
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
    assert response.json()["detail"] == (
        "Ticket with ID 999 not found."
    )

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

    # Invalid updates shouldnt change the existing ticket
    unchanged = client.get(f"/tickets/{created['id']}")
    assert unchanged.json()["status"] == "OPEN"


def test_update_nonexistent_ticket(client):
    response = client.patch(
        "/tickets/999",
        json={"status": "CLOSED"},
    )

    assert response.status_code == 404

### Testing deleting tickets


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

    # Verify that the ticket is actually gone.
    response = client.get(f"/tickets/{ticket_id}")

    assert response.status_code == 404


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
        json={"status": "RESOLVED"},
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

