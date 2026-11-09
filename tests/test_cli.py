from unittest.mock import Mock, patch

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
