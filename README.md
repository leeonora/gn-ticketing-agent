# GN Ticketing Agent

A fault-tolerant support ticketing system built for an end-to-end GenAI agent technical assessment. The project currently provides a **working, locally hosted REST API** for managing support tickets, with validation, meaningful HTTP errors, and automated tests. An LLM-powered agent, pull-request review bot, and infrastructure configuration are planned as subsequent parts of the assessment.

## Current status

**Part 1 — Mock Ticketing API: implemented and manually tested.** The most recent reported test run (9 November 2026) completed **10 tests passed, 2 deprecation warnings**. The warnings concerned a renamed HTTP 422 status constant; they do not indicate test failures.

| Component | Status |
| --- | --- |
| Ticket CRUD API, status filtering, and validation | Implemented |
| API tests with pytest | 10 passing tests |
| GenAI agent and CLI | Planned — Part 2 |
| LLM pull-request review workflow | Planned — Part 3 |
| Azure Terraform skeleton | Planned — Part 4 |
| MCP integration | Optional bonus; not implemented |

## Tech stack

- **Python 3.11+** with a `src/` package layout
- **FastAPI** and **Uvicorn** for the HTTP API
- **Pydantic** for request, response, and ticket-data validation
- **pytest** and FastAPI's **TestClient** for automated tests
- **HTTPX**, **OpenAI Python SDK**, and **python-dotenv** installed in preparation for the agent
- **Ruff** for linting and formatting

## Project structure

```text
gn-ticketing-agent/
├── src/
│   └── ticketing_system/
│       ├── __init__.py
│       └── api/
│           ├── __init__.py
│           ├── main.py         # FastAPI application and HTTP routes
│           ├── models.py       # Ticket, TicketCreate, TicketUpdate, TicketStatus
│           └── store.py        # In-memory TicketStore
├── tests/
│   └── test_api.py             # Automated API tests
├── pyproject.toml              # Project metadata and dependencies
├── .env.example                # Environment variable placeholders
├── .gitignore
└── README.md
```

The `agent/`, `scripts/`, `infra/`, and `.github/workflows/` directories will be added as their corresponding parts are implemented. Only document them here as existing after they have been created.

## Getting started

### Prerequisites

- Python **3.11 or newer**
- Git

### Installation

Clone this repository (replace the placeholder with the actual repository URL):

```bash
git clone https://github.com/leeonora/gn-ticketing-agent
cd gn-ticketing-agent
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it using your shell:

```bash
# macOS/Linux (Bash or Zsh)
source .venv/bin/activate

# Fish shell (run this instead if using Fish)
source .venv/bin/activate.fish
```

On Windows PowerShell, use `.venv\Scripts\Activate.ps1` instead.

Install the project and development tools:

```bash
python -m pip install -e ".[dev]"
```

### Run the API

From the repository root with the virtual environment activated:

```bash
uvicorn ticketing_system.api.main:app --reload
```

Open the interactive Swagger UI at **http://127.0.0.1:8000/docs**. The health check is available at **http://127.0.0.1:8000/health**.

The API uses an **in-memory** ticket store. Tickets are reset whenever the server process restarts; no external database or API credentials are required to run **Part 1**.

## API endpoints

| Method | Route | Purpose | Success response |
| --- | --- | --- | --- |
| `GET` | `/health` | Health check | `200 OK` |
| `POST` | `/tickets` | Create a new ticket | `201 Created` |
| `GET` | `/tickets` | List tickets, optionally filter by status | `200 OK` |
| `GET` | `/tickets/{ticket_id}` | Get a ticket by ID | `200 OK` |
| `PATCH` | `/tickets/{ticket_id}` | Update selected ticket fields | `200 OK` |
| `DELETE` | `/tickets/{ticket_id}` | Delete a ticket | `204 No Content` |

Ticket fields: `id`, `title`, `description`, `created`, `status`, and `resolution`.

Valid status values are `OPEN`, `RESOLVED`, and `CLOSED`. New tickets start in `OPEN`; the server generates the ID and a timezone-aware **UTC** creation timestamp.

### Example: create a ticket

```bash
curl -X POST http://127.0.0.1:8000/tickets \
  -H "Content-Type: application/json" \
  -d '{"title":"Keyboard not working","description":"Keyboard is unresponsive."}'
```

The response includes a generated ticket ID. Use that ID for subsequent requests:

```bash
# Replace 1 with an existing ticket ID
curl http://127.0.0.1:8000/tickets/1

curl -X PATCH http://127.0.0.1:8000/tickets/1 \
  -H "Content-Type: application/json" \
  -d '{"status":"RESOLVED","resolution":"Replaced faulty cable"}'

curl 'http://127.0.0.1:8000/tickets?status=OPEN'

curl -i -X DELETE http://127.0.0.1:8000/tickets/1
```

### Validation and error handling

The API checks incoming data using Pydantic and applies ticket business rules. Examples:

- **404 Not Found:** requesting, updating, or deleting a nonexistent ticket, e.g. `{"detail":"Ticket with ID 999 not found."}`
- **422 Unprocessable Content:** an invalid status such as `PROGRESS`, with a message identifying valid statuses: `OPEN`, `RESOLVED`, `CLOSED`
- **422 validation error:** an empty ticket title, an invalid path parameter, or an invalid update body

Failed validation must not partially modify an existing ticket. The ticket-update implementation revalidates the merged ticket before saving it.

## Automated tests

Run the suite from the repository root:

```bash
python -m pytest -v
```

The API tests use FastAPI's `TestClient`, so **Uvicorn does not need to be running**. Each test receives a fresh in-memory ticket store to keep tests independent.

| Test | What it checks |
| --- | --- |
| `test_create_ticket` | Ticket creation, `201`, generated ID, default status and timestamp |
| `test_get_ticket` | Retrieval of an existing ticket |
| `test_get_nonexistent_ticket` | `404` and descriptive error for missing ID |
| `test_update_ticket` | Valid status and resolution update |
| `test_invalid_status` | `422` for `PROGRESS`, allowed statuses in message, unchanged ticket |
| `test_update_nonexistent_ticket` | `404` for a missing ticket on PATCH |
| `test_delete_ticket` | `204`, empty body, ticket subsequently absent |
| `test_filter_tickets_by_status` | Filtered GET returns matching tickets only |
| `test_create_ticket_with_empty_title` | `422` for an empty title |
| `test_update_with_null_description` | `422` and unchanged data after an invalid PATCH |

**Latest reported result:** `10 passed, 2 warnings in 0.25s` (9 November 2026). To eliminate those deprecation warnings, replace `status.HTTP_422_UNPROCESSABLE_ENTITY` with `status.HTTP_422_UNPROCESSABLE_CONTENT` where used, and rerun the suite.

Optional code quality checks:

```bash
python -m ruff check .
python -m ruff format --check .
```

## Planned GenAI agent (Part 2)

The next component will expose the API operations to an LLM through custom tools and provide a simple command-line interface. The agent should use HTTP requests to the API rather than accessing the in-memory store directly. It must translate API `404` and `422` response details into clear, actionable feedback for users.

Future parts also require a pull-request review script integrated with GitHub Actions (Part 3), and a minimal Azure Terraform configuration under `infra/` (Part 4). These components are **not yet available to run**.

### Credentials for future LLM integration

Once the agent is implemented, copy the environment template and supply the LLM credentials locally:

```bash
cp .env.example .env
```

The `.env.example` file must contain **placeholders only**. Never commit API keys, `.env`, or the original assessment PDF if it contains credentials. If a secret has already been committed, removing the file from a later commit does not erase it from Git history; arrange credential rotation and history cleanup as needed.

## Production considerations

**Design decision to revisit:** In-memory storage keeps the exercise minimal and easy to run, but it is not durable and will not work as shared state across multiple application processes. In production, replace `TicketStore`'s dictionary with persistent storage (for example, a database) while keeping the API contracts and error semantics stable.

## Scope

This README reflects the API implementation and test results reported during development. Additional integration tests, concurrency handling, authentication, and persistent storage are outside the current mock API scope. The optional requirement to mandate a resolution note when changing a ticket to `RESOLVED` has not been implemented.
