import logging

import httpx
import pytest

from ticketing_system.agent import tools


@pytest.mark.parametrize(
    ("error_type", "expected_message"),
    [
        (httpx.ConnectError, "Cannot reach the ticketing API."),
        (httpx.ReadTimeout, "The ticketing API timed out."),
    ],
)
def test_api_network_failure_returns_actionable_error(
    monkeypatch, error_type, expected_message
):
    request = httpx.Request("POST", "http://127.0.0.1:8000/tickets")

    def fail_request(**kwargs):
        assert kwargs["timeout"] == 10.0
        raise error_type("internal network detail", request=request)

    monkeypatch.setattr(tools.httpx, "request", fail_request)

    result = tools.create_ticket("Broken screen", "The screen is blank")

    assert result["success"] is False
    assert result["status_code"] is None
    assert result["error"].startswith(expected_message)
    assert "internal network detail" not in result["error"]
    if error_type is httpx.ReadTimeout:
        assert "check the ticket state before trying again" in result["error"]


@pytest.fixture
def transport(monkeypatch):
    """Exercise HTTPX request construction without opening a network socket."""

    def install(handler):
        client = httpx.Client(transport=httpx.MockTransport(handler))
        monkeypatch.setattr(tools, "BASE_URL", "http://ticket-api.test")
        monkeypatch.setattr(tools.httpx, "request", client.request)
        return client

    return install


@pytest.mark.parametrize(
    "status_code,body,expected",
    [
        (
            422,
            {
                "detail": [
                    {
                        "loc": ["body", "title"],
                        "msg": "Field required",
                        "type": "missing",
                    }
                ]
            },
            [{"loc": ["body", "title"], "msg": "Field required", "type": "missing"}],
        ),
        (502, {"message": "upstream unavailable"}, "upstream unavailable"),
    ],
)
def test_http_errors_preserve_details_and_have_fallbacks(
    transport, status_code, body, expected
):
    requests = []

    def handler(request):
        requests.append(request)
        if isinstance(body, str):
            return httpx.Response(status_code, text=body)
        return httpx.Response(status_code, json=body)

    with transport(handler):
        result = tools.update_ticket(999, status="PROGRESS")
    assert len(requests) == 1
    assert result == {"success": False, "status_code": status_code, "error": expected}


def test_malformed_success_response_does_not_raise_or_retry(transport):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(201, text="<html>Unexpected upstream response</html>")

    with transport(handler):
        result = tools.create_ticket("Keyboard", "Broken")
    assert len(requests) == 1
    assert result["success"] is False
    assert result["status_code"] == 201
    assert "invalid JSON" in result["error"]
    assert "check the ticket state" in result["error"]


def test_ambiguous_write_failure_warns_without_repeating_write(transport):
    from ticketing_system.api.store import TicketStore

    store = TicketStore()
    requests = []

    def handler(request):
        requests.append(request)
        # Simulate the server committing before the client observes a failure.
        store.create("New", "Description")
        raise httpx.ReadError("private transport detail", request=request)

    with transport(handler):
        result = tools.create_ticket("New", "Description")

    assert len(requests) == 1
    assert requests[0].method == "POST"
    assert result["success"] is False
    assert result["status_code"] is None
    assert "may have completed" in result["error"]
    assert "check the ticket state before trying again" in result["error"]
    assert "private transport detail" not in result["error"]
    assert len(store.get_all()) == 1


def test_read_failure_can_recommend_retry(transport):
    def handler(request):
        raise httpx.ReadError("private transport detail", request=request)

    with transport(handler):
        result = tools.list_tickets()

    assert result == {
        "success": False,
        "status_code": None,
        "error": "The ticketing API request failed. Please try again.",
    }


@pytest.mark.parametrize(
    "status_code,body",
    [
        (
            422,
            {"detail": [{"msg": "Invalid input", "input": "PRIVATE_ERROR_CANARY"}]},
        ),
        (500, "<html>PRIVATE_ERROR_CANARY</html>"),
    ],
)
def test_error_details_reach_model_but_are_not_logged(
    transport, monkeypatch, caplog, status_code, body
):
    monkeypatch.setenv("LOG_CONVERSATIONS", "false")

    def handler(request):
        if isinstance(body, str):
            return httpx.Response(status_code, text=body)
        return httpx.Response(status_code, json=body)

    # Application logging disables propagation; capture its actual log records.
    tools.logger.addHandler(caplog.handler)
    try:
        with (
            caplog.at_level(logging.INFO, logger=tools.logger.name),
            transport(handler),
        ):
            result = tools.update_ticket(1, status="PRIVATE_ERROR_CANARY")
    finally:
        tools.logger.removeHandler(caplog.handler)

    expected = (
        body if isinstance(body, str) else body.get("detail", body.get("message"))
    )
    assert result == {
        "success": False,
        "status_code": status_code,
        "error": expected,
    }
    assert "PRIVATE_ERROR_CANARY" not in caplog.text
    assert f"PATCH /tickets/1 failed | HTTP {status_code}" in caplog.text
