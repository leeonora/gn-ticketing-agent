"""Network failure behavior for ticketing HTTP tools."""

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
