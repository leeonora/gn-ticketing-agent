import json

import httpx
import pytest
from pydantic_ai.messages import (
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel

from ticketing_system.agent import tools
from ticketing_system.agent.agent import agent


@pytest.mark.parametrize(
    "tool_name, arguments, expected_kwargs, api_result",
    [
        # 1. List open tickets
        (
            "list_tickets",
            {"status": "OPEN"},
            {"status": "OPEN"},
            {
                "success": True,
                "status_code": 200,
                "data": [],
            },
        ),
        # 2. Retrieve a nonexistent ticket
        (
            "get_ticket",
            {"ticket_id": 999},
            {"ticket_id": 999},
            {
                "success": False,
                "status_code": 404,
                "error": "Ticket with ID 999 not found.",
            },
        ),
        # 3. Create a ticket
        (
            "create_ticket",
            {
                "title": "Keyboard not working",
                "description": "Keyboard stopped responding",
            },
            {
                "title": "Keyboard not working",
                "description": "Keyboard stopped responding",
            },
            {
                "success": True,
                "status_code": 201,
                "data": {
                    "id": 1,
                    "title": "Keyboard not working",
                    "status": "OPEN",
                },
            },
        ),
        # 4. Invalid status
        (
            "update_ticket",
            {"ticket_id": 1, "status": "PROGRESS"},
            {
                "ticket_id": 1,
                "title": None,
                "description": None,
                "status": "PROGRESS",
                "resolution": None,
            },
            {
                "success": False,
                "status_code": 422,
                "error": (
                    "Invalid status 'PROGRESS'. "
                    "Valid statuses are: OPEN, RESOLVED, CLOSED."
                ),
            },
        ),
        # 5. Resolve a ticket
        (
            "update_ticket",
            {
                "ticket_id": 1,
                "status": "RESOLVED",
                "resolution": "Replaced faulty cable",
            },
            {
                "ticket_id": 1,
                "title": None,
                "description": None,
                "status": "RESOLVED",
                "resolution": "Replaced faulty cable",
            },
            {
                "success": True,
                "status_code": 200,
                "data": {
                    "id": 1,
                    "status": "RESOLVED",
                    "resolution": "Replaced faulty cable",
                },
            },
        ),
        # 6. Soft-delete a ticket
        (
            "delete_ticket",
            {"ticket_id": 1},
            {"ticket_id": 1},
            {
                "success": True,
                "status_code": 204,
                "data": None,
            },
        ),
        # 7. Restore a deleted ticket
        (
            "restore_ticket",
            {"ticket_id": 1},
            {"ticket_id": 1},
            {
                "success": True,
                "status_code": 200,
                "data": {
                    "id": 1,
                    "title": "Keyboard not working",
                    "status": "OPEN",
                    "deleted": False,
                },
            },
        ),
        # 8. Retrieve an existing ticket (required assessment scenario)
        (
            "get_ticket",
            {"ticket_id": 1},
            {"ticket_id": 1},
            {
                "success": True,
                "status_code": 200,
                "data": {"id": 1, "title": "Keyboard not working", "status": "OPEN"},
            },
        ),
        # 9. Update a nonexistent ticket (required assessment scenario)
        (
            "update_ticket",
            {"ticket_id": 999, "status": "CLOSED"},
            {"ticket_id": 999, "status": "CLOSED"},
            {
                "success": False,
                "status_code": 404,
                "error": "Ticket with ID 999 not found.",
            },
        ),
    ],
)
def test_agent_tools(
    monkeypatch,
    tool_name,
    arguments,
    expected_kwargs,
    api_result,
):
    """Verify registered tools, HTTP requests and API result delivery to the model.

    The model is scripted; these tests do not evaluate natural-language understanding.
    """

    call_count = 0

    def fake_model(messages, info: AgentInfo):
        nonlocal call_count
        call_count += 1

        if call_count == 1:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        tool_name=tool_name,
                        args=arguments,
                    )
                ]
            )

        return ModelResponse(parts=[TextPart(content="Simulated response")])

    ticket_id = arguments.get("ticket_id")
    method, path = {
        "list_tickets": ("GET", "/tickets"),
        "get_ticket": ("GET", f"/tickets/{ticket_id}"),
        "create_ticket": ("POST", "/tickets"),
        "update_ticket": ("PATCH", f"/tickets/{ticket_id}"),
        "delete_ticket": ("DELETE", f"/tickets/{ticket_id}"),
        "restore_ticket": ("POST", f"/tickets/{ticket_id}/restore"),
    }[tool_name]
    fields = {
        key: value
        for key, value in expected_kwargs.items()
        if key != "ticket_id" and value is not None
    }
    requests = []

    def handler(request):
        requests.append(request)
        assert request.method == method
        assert request.url.host == "ticket-api.test"
        assert request.url.path == path
        assert request.extensions["timeout"]["read"] == 10.0
        assert dict(request.url.params) == (
            fields if tool_name == "list_tickets" else {}
        )
        if tool_name in {"create_ticket", "update_ticket"}:
            assert json.loads(request.content) == fields
        else:
            assert request.content == b""

        status_code = api_result["status_code"]
        if status_code == 204:
            return httpx.Response(204)
        body = (
            api_result["data"]
            if api_result["success"]
            else {"detail": api_result["error"]}
        )
        return httpx.Response(status_code, json=body)

    monkeypatch.setattr(tools, "BASE_URL", "http://ticket-api.test")
    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        agent.override(model=FunctionModel(fake_model)),
    ):
        monkeypatch.setattr(tools.httpx, "request", client.request)
        result = agent.run_sync("Execute test operation")

    # Each model tool call produces exactly one HTTP request, including failures.
    assert len(requests) == 1

    # Verify the agent completed the interaction.
    assert result.output == "Simulated response"
    assert call_count == 2

    # Verify the API result was returned to the model.
    tool_returns = [
        part
        for message in result.all_messages()
        for part in message.parts
        if isinstance(part, ToolReturnPart)
    ]

    assert len(tool_returns) == 1
    assert tool_returns[0].content == api_result
