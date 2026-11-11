import os
from typing import Literal

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from ticketing_system.agent import tools

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY", "test-key-not-for-production")

base_url = os.getenv(
    "OPENAI_BASE_URL",
    "https://models.genie.gn.group/openai/v1",
)

model_name = os.getenv(
    "OPENAI_MODEL",
    "gpt-6-luna",
)

client = AsyncOpenAI(
    api_key=api_key,
    base_url=base_url,
    default_headers={"api-key": api_key},
)

model = OpenAIChatModel(
    model_name,
    provider=OpenAIProvider(openai_client=client),
)

agent = Agent(
    model,
    instructions=(
        "You are a support ticket assistant. "
        "Use tools for ticket operations. "
        "Never invent ticket information. "
        "When a tool returns success=True and data=[], "
        "explain that no matching tickets exist. "
        "When a tool returns success=False, explain the "
        "error using the information returned by the API. "
        "Deleting a ticket is reversible: the API soft-deletes "
        "tickets instead of permanently removing them. "
        "After a successful deletion, inform the user that "
        "the ticket can be restored. "
        "If the user asks to undo a deletion, use the "
        "restore_ticket tool with the appropriate ticket ID. "
        "Use conversation history to identify the ticket "
        "when possible, but ask for the ID if it is unclear. "
        "Only report a ticket as deleted or restored when "
        "the corresponding API tool returns success=True. "
        "Never invent or infer resolution notes. "
        "When resolving a ticket, a resolution note must be "
        "explicitly provided by the user. "
        "If no resolution note has been provided for the "
        "requested resolution, ask the user for one before "
        "calling the update tool."
    ),
    model_settings={
        "openai_reasoning_effort": "none",
    },
)


@agent.tool_plain
def list_tickets(
    status: Literal["OPEN", "RESOLVED", "CLOSED"] | None = None,
) -> dict:
    """Retrieve all tickets, optionally filtering by status."""
    return tools.list_tickets(status=status)


@agent.tool_plain
def get_ticket(ticket_id: int) -> dict:
    """Retrieve the details of a single ticket by its ID."""
    return tools.get_ticket(ticket_id=ticket_id)


@agent.tool_plain
def create_ticket(title: str, description: str) -> dict:
    """Create a new support ticket with a title and description."""
    return tools.create_ticket(
        title=title,
        description=description,
    )


@agent.tool_plain
def update_ticket(
    ticket_id: int,
    title: str | None = None,
    description: str | None = None,
    status: str | None = None,
    resolution: str | None = None,
) -> dict:
    """Update fields of an existing ticket by its ID."""
    return tools.update_ticket(
        ticket_id=ticket_id,
        title=title,
        description=description,
        status=status,
        resolution=resolution,
    )


@agent.tool_plain
def delete_ticket(ticket_id: int) -> dict:
    """Soft-delete a ticket. The operation is reversible."""
    return tools.delete_ticket(ticket_id=ticket_id)


@agent.tool_plain
def restore_ticket(ticket_id: int) -> dict:
    """Restore a previously deleted ticket by its ID."""
    return tools.restore_ticket(ticket_id=ticket_id)
