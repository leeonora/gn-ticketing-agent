from unittest.mock import patch

import pytest
from pydantic_ai.messages import (
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel

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
        # 8. Restore a nonexistent ticket
        (
            "restore_ticket",
            {"ticket_id": 999},
            {"ticket_id": 999},
            {
                "success": False,
                "status_code": 404,
                "error": "Ticket with ID 999 not found.",
            },
        ),
        # 9. Restore a ticket that is not deleted
        (
            "restore_ticket",
            {"ticket_id": 1},
            {"ticket_id": 1},
            {
                "success": False,
                "status_code": 409,
                "error": "Ticket with ID 1 is not deleted.",
            },
        ),
    ],
)
def test_agent_tools(
    tool_name,
    arguments,
    expected_kwargs,
    api_result,
):
    """Verify tool execution and returned API data."""

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

    with (
        patch(
            f"ticketing_system.agent.tools.{tool_name}",
            return_value=api_result,
        ) as mock_tool,
        agent.override(model=FunctionModel(fake_model)),
    ):
        result = agent.run_sync("Execute test operation")

    # Verify the correct Python function and arguments.
    mock_tool.assert_called_once_with(**expected_kwargs)

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
