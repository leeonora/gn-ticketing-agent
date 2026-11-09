from openai import OpenAIError
from pydantic_ai import UsageLimits
from pydantic_ai.exceptions import AgentRunError, UsageLimitExceeded

from ticketing_system.agent.agent import agent


def main() -> None:
    """Run the interactive ticketing agent."""

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
            break

        if user_input.lower() in {"exit", "quit"}:
            print("Goodbye!")
            break

        if not user_input:
            continue

        try:
            result = agent.run_sync(
                user_input,
                message_history=message_history,
                usage_limits=usage_limits,
            )

            print(f"\nAgent: {result.output}\n")

            message_history = result.all_messages()

        except UsageLimitExceeded:
            print(
                "\nAgent: This request exceeded the "
                "allowed number of model or tool calls.\n"
            )

        except (AgentRunError, OpenAIError) as exc:
            print(f"\nAgent error: {exc}\n")
            print("Please try again.")


if __name__ == "__main__":
    main()
