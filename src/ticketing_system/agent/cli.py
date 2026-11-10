import logging
import os
import time

os.environ["PYDANTIC_AI_NO_BANNER"] = "1"

from openai import OpenAIError
from pydantic_ai import UsageLimits
from pydantic_ai.exceptions import AgentRunError, UsageLimitExceeded

from ticketing_system.agent.agent import agent
from ticketing_system.logging_config import setup_logging

logger = logging.getLogger(__name__)


def main() -> None:
    """Run the interactive ticketing agent."""

    setup_logging()

    log_conversations = os.getenv("LOG_CONVERSATIONS", "false").lower() == "true"

    logger.info("CLI session started")

    print("GN Ticketing Agent")
    print("Type 'exit' to quit.\n")

    message_history = []

    usage_limits = UsageLimits(
        request_limit=5,
        tool_calls_limit=5,
    )

    while True:
        try:
            user_input = input("You: ").strip()

        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            logger.info("CLI session ended")
            break

        if user_input.lower() in {"exit", "quit"}:
            print("Goodbye!")
            logger.info("CLI session ended")
            break

        if not user_input:
            continue

        start_time = time.perf_counter()
        logger.info("Agent run started")

        if log_conversations:
            logger.info("User prompt: %s", user_input)

        try:
            result = agent.run_sync(
                user_input,
                message_history=message_history,
                usage_limits=usage_limits,
            )

            print(f"\nAgent: {result.output}\n")

            message_history = result.all_messages()

            if log_conversations:
                logger.info("LLM response: %s", result.output)

            duration = time.perf_counter() - start_time

            logger.info(
                "Agent run completed successfully | %.3f seconds",
                duration,
            )

        except UsageLimitExceeded:
            duration = time.perf_counter() - start_time

            logger.warning(
                "Agent run exceeded usage limits | %.3f seconds",
                duration,
            )

            print(
                "\nAgent: This request exceeded the "
                "allowed number of model or tool calls.\n"
            )

        except (AgentRunError, OpenAIError) as exc:
            duration = time.perf_counter() - start_time

            logger.error(
                "Agent run failed | %s | %.3f seconds",
                type(exc).__name__,
                duration,
            )

            print(f"\nAgent error: {exc}\n")
            print("Please try again.")


if __name__ == "__main__":
    main()
