import os

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv(
    "TICKETING_API_BASE_URL",
    "http://127.0.0.1:8000",
)


def _request(
    method: str,
    endpoint: str,
    **kwargs,
) -> dict:
    """Send an HTTP request and return a structured result."""

    try:
        response = httpx.request(
            method=method,
            url=f"{BASE_URL}{endpoint}",
            timeout=10.0,
            **kwargs,
        )

        response.raise_for_status()

        data = response.json() if response.content else None

        return {
            "success": True,
            "status_code": response.status_code,
            "data": data,
        }

    except httpx.HTTPStatusError as exc:
        try:
            detail = exc.response.json().get("detail")
        except (ValueError, AttributeError):
            detail = exc.response.text

        return {
            "success": False,
            "status_code": exc.response.status_code,
            "error": detail,
        }

    except httpx.RequestError as exc:
        return {
            "success": False,
            "status_code": None,
            "error": f"Ticketing API request failed: {type(exc).__name__}",
        }


def list_tickets(status: str | None = None) -> dict:
    """Retrieve tickets, optionally filtered by status."""

    params = {"status": status} if status is not None else {}

    return _request(
        method="GET",
        endpoint="/tickets",
        params=params,
    )


def get_ticket(ticket_id: int) -> dict:
    """Retrieve a ticket by its ID."""

    return _request(
        method="GET",
        endpoint=f"/tickets/{ticket_id}",
    )


def create_ticket(title: str, description: str) -> dict:
    """Create a new support ticket."""

    return _request(
        method="POST",
        endpoint="/tickets",
        json={
            "title": title,
            "description": description,
        },
    )


def update_ticket(
    ticket_id: int,
    title: str | None = None,
    description: str | None = None,
    status: str | None = None,
    resolution: str | None = None,
) -> dict:
    """Update one or more fields of an existing ticket."""

    updates = {
        key: value
        for key, value in {
            "title": title,
            "description": description,
            "status": status,
            "resolution": resolution,
        }.items()
        if value is not None
    }

    return _request(
        method="PATCH",
        endpoint=f"/tickets/{ticket_id}",
        json=updates,
    )


def delete_ticket(ticket_id: int) -> dict:
    """Delete a ticket by its ID."""

    return _request(
        method="DELETE",
        endpoint=f"/tickets/{ticket_id}",
    )
