import logging
from unittest.mock import Mock, patch

from openai import OpenAIError
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.usage import UsageLimits

from ticketing_system.agent.cli import main


def test_cli_conversation():
    """Verify that the CLI uses the configured usage limits."""

    mock_result = Mock()
    mock_result.output = "There are no open tickets."
    mock_result.all_messages.return_value = ["mock history"]

    with (
        patch(
            "builtins.input",
            side_effect=["Show me all open tickets", "exit"],
        ),
        patch(
            "ticketing_system.agent.cli.agent.run_sync",
            return_value=mock_result,
        ) as mock_run,
    ):
        main()

    mock_run.assert_called_once()

    args, kwargs = mock_run.call_args

    assert args == ("Show me all open tickets",)
    assert kwargs["message_history"] == []

    limits = kwargs["usage_limits"]

    assert isinstance(limits, UsageLimits)
    assert limits.request_limit == 5
    assert limits.tool_calls_limit == 5


def test_cli_usage_limit(capsys):
    """Verify that the CLI handles exceeded limits gracefully."""

    with (
        patch(
            "builtins.input",
            side_effect=["Show me all open tickets", "exit"],
        ),
        patch(
            "ticketing_system.agent.cli.agent.run_sync",
            side_effect=UsageLimitExceeded("Model request limit exceeded"),
        ),
    ):
        main()

    output = capsys.readouterr().out

    assert "exceeded the" in output
    assert "Goodbye!" in output


def test_cli_model_failure_shows_safe_message(capsys):
    with (
        patch("builtins.input", side_effect=["Create a ticket", "exit"]),
        patch(
            "ticketing_system.agent.cli.agent.run_sync",
            side_effect=OpenAIError("internal model detail"),
        ),
    ):
        main()

    output = capsys.readouterr().out
    assert "language model request failed" in output
    assert "Check your connection and API key" in output
    assert "internal model detail" not in output


def test_cli_conversation_logging_enabled(monkeypatch, caplog):
    """Prompts and responses are logged when explicitly enabled."""
    from unittest.mock import MagicMock

    from ticketing_system.agent import cli

    monkeypatch.setenv("LOG_CONVERSATIONS", "true")
    monkeypatch.setattr(cli, "setup_logging", lambda: None)

    inputs = iter(["List all tickets", "exit"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    mock_result = MagicMock()
    mock_result.output = "There are no tickets."
    mock_result.all_messages.return_value = []

    mock_agent = MagicMock()
    mock_agent.run_sync.return_value = mock_result
    monkeypatch.setattr(cli, "agent", mock_agent)

    with caplog.at_level(logging.INFO, logger=cli.logger.name):
        cli.logger.addHandler(caplog.handler)
        try:
            cli.main()
        finally:
            cli.logger.removeHandler(caplog.handler)

    assert "User prompt: List all tickets" in caplog.text
    assert "LLM response: There are no tickets." in caplog.text


def test_cli_conversation_logging_disabled(monkeypatch, caplog):
    """Prompts and responses are not logged when disabled."""
    from unittest.mock import MagicMock

    from ticketing_system.agent import cli

    monkeypatch.setenv("LOG_CONVERSATIONS", "false")
    monkeypatch.setattr(cli, "setup_logging", lambda: None)

    inputs = iter(["List all tickets", "exit"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    mock_result = MagicMock()
    mock_result.output = "There are no tickets."
    mock_result.all_messages.return_value = []

    mock_agent = MagicMock()
    mock_agent.run_sync.return_value = mock_result
    monkeypatch.setattr(cli, "agent", mock_agent)

    with caplog.at_level(logging.INFO, logger=cli.logger.name):
        cli.logger.addHandler(caplog.handler)
        try:
            cli.main()
        finally:
            cli.logger.removeHandler(caplog.handler)

    assert "User prompt:" not in caplog.text
    assert "LLM response:" not in caplog.text


def test_cli_forwards_history_to_second_turn():
    first = Mock(output="Created ticket 7")
    first.all_messages.return_value = ["first turn history"]
    second = Mock(output="Ticket 7 is open")
    second.all_messages.return_value = ["both turns"]
    with (
        patch("builtins.input", side_effect=["Create a ticket", "Show it", "exit"]),
        patch(
            "ticketing_system.agent.cli.agent.run_sync", side_effect=[first, second]
        ) as run,
    ):
        main()
    assert run.call_args_list[0].kwargs["message_history"] == []
    assert run.call_args_list[1].args == ("Show it",)
    assert run.call_args_list[1].kwargs["message_history"] == ["first turn history"]


def test_model_failure_after_write_warns_without_repeating_write(monkeypatch, capsys):
    from pydantic_ai.messages import ModelResponse, ToolCallPart
    from pydantic_ai.models.function import FunctionModel

    from ticketing_system.agent import tools
    from ticketing_system.agent.agent import agent
    from ticketing_system.api.store import TicketStore

    store = TicketStore()
    calls = 0

    def create(title, description):
        ticket = store.create(title, description)
        return {
            "success": True,
            "status_code": 201,
            "data": ticket.model_dump(mode="json"),
        }

    def model(messages, info):
        nonlocal calls
        calls += 1
        if calls == 1:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        "create_ticket", {"title": "Keyboard", "description": "Broken"}
                    )
                ]
            )
        raise OpenAIError("Simulated failure after the write")

    monkeypatch.setattr(tools, "create_ticket", create)
    with (
        agent.override(model=FunctionModel(model)),
        patch("builtins.input", side_effect=["Create a keyboard ticket", "exit"]),
    ):
        main()
    assert len(store.get_all()) == 1
    assert calls == 2
    output = capsys.readouterr().out
    assert "Ticket operations may already have completed" in output
    assert "check the ticket state before repeating a write" in output
    assert "Goodbye!" in output
