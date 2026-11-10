# GN Ticketing Agent

A local support-ticketing system with a **FastAPI REST API** and a **Pydantic AI agent** that can create, retrieve, filter, update, and delete tickets through natural-language requests. The agent uses HTTP tools to interact with the API and turns business-rule errors into useful feedback instead of crashing.

Built for GN's *End-to-End Fault-Tolerant GenAI Agent System* take-home assessment.

## Implementation status

| Assessment component | Status |
| --- | --- |
| Part 1 — Mock Ticketing API | Implemented; API tests passed |
| Part 2 — GenAI agent, HTTP tools, and CLI | Implemented; six required live scenarios demonstrated |
| Part 3 — LLM pull-request reviewer / GitHub Actions | Not yet implemented |
| Part 4 — Azure Terraform skeleton | Not yet implemented |
| Optional MCP server | Not implemented |

## Tech stack

- **Python 3.11+** with a `src/` package layout
- **FastAPI**, **Uvicorn**, and **Pydantic** for the ticketing API and validation
- **Pydantic AI** (`pydantic-ai-slim[openai]`) for agent orchestration and typed tool registration
- **OpenAI Python SDK** to access GN's OpenAI-compatible hosted model (`gpt-6-luna`)
- **HTTPX** for agent-to-API requests
- **python-dotenv** for environment configuration
- **pytest**, FastAPI **TestClient**, Pydantic AI **FunctionModel**, and `unittest.mock` for tests
- **Ruff** for linting and formatting

## Architecture

```text
User
  |
  v
CLI (agent/cli.py)  <--- conversation history, usage limits
  |
  v
Pydantic AI agent (agent/agent.py) <----> GN-hosted LLM (gpt-6-luna)
  |                  selects tools and writes responses
  v
Registered tools: list / get / create / update / delete
  |
  v
HTTP client and error handling (agent/tools.py)
  |                   ^
  | HTTP requests     | JSON / HTTP 404 / 422
  v                   |
FastAPI (api/main.py)
  |-- Pydantic request/response models (api/models.py)
  `-- In-memory ticket store (api/store.py)
```

The model **selects a tool and supplies arguments**; Python executes the registered tool. The tools make real HTTP requests to FastAPI—they **do not access the ticket store directly**. The API remains responsible for enforcing business rules. Tool results carry structured success/error information back to the LLM so it can explain failures in natural language.

### Project structure

```text
gn-ticketing-agent/
├── src/
│   └── ticketing_system/
│       ├── __init__.py
│       ├── api/
│       │   ├── __init__.py
│       │   ├── main.py          # FastAPI routes
│       │   ├── models.py        # Ticket models and status enum
│       │   └── store.py         # In-memory TicketStore
│       └── agent/
│           ├── __init__.py
│           ├── agent.py         # Pydantic AI agent and registered tools
│           ├── tools.py         # HTTPX operations and structured errors
│           └── cli.py           # Interactive CLI
├── tests/
│   ├── test_api.py              # API contract and validation tests
│   ├── test_agent.py            # Mocked agent/tool orchestration tests
│   └── test_cli.py              # Mocked CLI and usage-limit tests
├── pyproject.toml
├── .env.example                 # Safe configuration placeholders
├── .gitignore
└── README.md
```

Parts 3 and 4 will add their own scripts, workflow, and infrastructure files when implemented.

## Getting started

### Prerequisites

- Python **3.11 or newer**
- Git
- A valid credential for the **GN-provided LLM endpoint** to use Part 2; **Part 1 and mocked tests do not require it**

### 1. Install

```bash
git clone https://github.com/leeonora/gn-ticketing-agent
cd gn-ticketing-agent
python -m venv .venv
```

Activate the environment:

```bash
# macOS/Linux — Bash or Zsh
source .venv/bin/activate

# Fish shell — use this instead
# source .venv/bin/activate.fish
```

On Windows PowerShell, run `.venv\Scripts\Activate.ps1`.

Install the project and its development dependencies:

```bash
python -m pip install -e ".[dev]"
```

**Dependency note:** `pyproject.toml` must include `pydantic-ai-slim[openai]` in its project dependencies in addition to FastAPI, Uvicorn, Pydantic, HTTPX, OpenAI, and python-dotenv. This is required for the implemented agent.

### 2. Configure the agent

Copy the environment template:

```bash
cp .env.example .env
```

The template should contain **placeholder values only**:

```dotenv
OPENAI_API_KEY=your_gn_api_key_here
OPENAI_BASE_URL=https://models.genie.gn.group/openai/v1
OPENAI_MODEL=gpt-6-luna
TICKETING_API_BASE_URL=http://127.0.0.1:8000
```

Insert the authorized GN credential **only into your local `.env`**. The project follows GN's supplied OpenAI-compatible `/openai/v1` endpoint and `api-key` header pattern. The model is configured for Chat Completions with `openai_reasoning_effort="none"` because GN's endpoint rejects function tools with reasoning enabled in that mode. No `api_version` is needed for the endpoint shown above.

Never commit `.env`, credentials, or the original assessment PDF containing the credential. If a secret has been committed, simply deleting it in a subsequent commit does **not** remove it from Git history; rotate the credential and clean the history as appropriate.

### 3. Run FastAPI (terminal 1)

```bash
uvicorn ticketing_system.api.main:app --reload
```

API documentation: **http://127.0.0.1:8000/docs**
Health check: **http://127.0.0.1:8000/health**

### 4. Run the agent CLI (terminal 2)

Activate the same virtual environment in a second terminal, from the repository root:

```bash
python -m ticketing_system.agent.cli
```

Example interaction:

```text
GN Ticketing Agent
Type 'exit' to quit.

You: Create a new ticket about a keyboard not working.
Agent: Created ticket #1: Keyboard not working. It's currently OPEN.

You: Retrieve all open tickets.
Agent: There is 1 open ticket: #1 — Keyboard not working.

You: Update ticket 1 to have status PROGRESS.
Agent: PROGRESS is not a valid status. Available statuses: OPEN, RESOLVED, CLOSED.

You: exit
Goodbye!
```

The CLI keeps message history between turns, accepts `exit`/`quit` (or Ctrl+C/Ctrl+D), and handles agent execution errors. It applies per-turn **Pydantic AI usage limits** of **5 model requests** and **5 tool calls** to bound agent execution. A limit is not a hard dollar/token budget, and a tool may already have changed a ticket before a later failure.

To suppress Pydantic AI's informational startup banner in **Fish**, run this in the agent terminal before starting the CLI:

```fish
set -x PYDANTIC_AI_NO_BANNER 1
python -m ticketing_system.agent.cli
```

For Bash/Zsh, use `export PYDANTIC_AI_NO_BANNER=1` instead. Logfire is **not required** to use the project.

**Note:** The mock API stores tickets in memory. Restarting the API clears tickets and resets ticket IDs. Use the ID returned by the creation request, rather than assuming it is always `1`.

## Ticketing API

| Method | Endpoint | Purpose | Successful response |
| --- | --- | --- | --- |
| `GET` | `/health` | Health check | `200 OK` |
| `POST` | `/tickets` | Create a ticket | `201 Created` |
| `GET` | `/tickets` | List tickets; optional `?status=OPEN` filter | `200 OK` |
| `GET` | `/tickets/{ticket_id}` | Retrieve a ticket | `200 OK` |
| `PATCH` | `/tickets/{ticket_id}` | Partially update a ticket | `200 OK` |
| `DELETE` | `/tickets/{ticket_id}` | Delete a ticket | `204 No Content` |

Ticket properties are `id`, `title`, `description`, `created`, `status`, and `resolution`. New tickets start with status `OPEN`, a generated ID, and a UTC creation timestamp. Valid statuses are `OPEN`, `RESOLVED`, and `CLOSED`.

Example direct API calls (do not use GN LLM tokens):

```bash
curl -X POST http://127.0.0.1:8000/tickets \
  -H "Content-Type: application/json" \
  -d '{"title":"Keyboard not working","description":"Keyboard is unresponsive."}'

# Replace 1 with an existing ticket ID
curl http://127.0.0.1:8000/tickets/1
curl 'http://127.0.0.1:8000/tickets?status=OPEN'

curl -X PATCH http://127.0.0.1:8000/tickets/1 \
  -H "Content-Type: application/json" \
  -d '{"status":"RESOLVED","resolution":"Replaced faulty cable"}'

curl -i -X DELETE http://127.0.0.1:8000/tickets/1
```

### Error handling

The API enforces its rules and returns HTTP errors with details:

- **404:** nonexistent ticket ID (e.g. `Ticket with ID 999 not found.`)
- **422:** invalid status in an update (e.g. `PROGRESS`, with `OPEN`, `RESOLVED`, and `CLOSED` listed as valid values)
- **422:** invalid input such as an empty title or an invalid update body

The API validates a complete merged ticket before saving an update, so invalid updates do not partially change a ticket. The agent's HTTPX layer converts HTTP outcomes into structured results, for example:

```json
{"success": false, "status_code": 422, "error": "Invalid status 'PROGRESS'. Valid statuses are: OPEN, RESOLVED, CLOSED."}
```

It also distinguishes network failures from API validation errors and handles empty-body `204` responses. The LLM receives these results and can explain the specific failure rather than inventing a success message.

## Testing

Run all automated tests:

```bash
python -m pytest -v
```

The automated tests use local `TestClient` and mocks / Pydantic AI testing models; **they do not require a running Uvicorn server and do not call GN's LLM**.

| Test file | Coverage |
| --- | --- |
| `tests/test_api.py` | 10 API tests covering CRUD, filtering, validation, `404`/`422`, and unchanged state after rejected updates |
| `tests/test_agent.py` | 6 parameterized mocked tool scenarios: list, missing ticket, create, invalid status, resolve, delete; verifies tool arguments and results forwarded to the model |
| `tests/test_cli.py` | 2 mocked CLI scenarios: message dispatch with usage limits and graceful handling when limits are exceeded |

These test counts reflect the implementation developed for this assessment; run the full suite in your own environment for the latest aggregate result. Mocked models verify wiring and tool-result propagation; **they do not establish whether GN's actual model chooses the right tools or explains failures well**.


## Logging and Observability

The application uses Python's built-in `logging` module to provide
basic observability across the FastAPI server, HTTP tools, and agent CLI.

Logs are written to both the console and `logs/ticketing.log`.

### Logged Events

- API operations, including ticket creation, retrieval, updates, and deletion.
- HTTP requests, response status codes, and execution times.
- Expected business errors (404 and 422) at WARNING level.
- Network and server failures at ERROR level.
- CLI session starts, agent execution times, and usage-limit errors.

### Log Rotation

Logs use Python's `RotatingFileHandler` with the following configuration:

- Maximum file size: 5 MiB
- Maximum backups: 3
- Maximum total storage: approximately 20 MiB

The `logs/` directory is excluded from version control.

### Optional Conversation Logging

For debugging LLM behavior, user prompts and final agent responses
can optionally be logged.

Add the following setting to your local `.env` file:

```dotenv
LOG_CONVERSATIONS=true
```

Conversation logging is disabled by default (`false`).

When enabled, prompts and responses are recorded in both the console
and rotating log files. This is intended for local testing with
non-sensitive data.

Conversation logs may contain sensitive information and should not
be committed or shared. Disabling the setting does not delete
previously recorded conversations.

### Production Considerations

For a production deployment, logging should use centralized,
structured logs with appropriate access controls, retention
policies, and sensitive-data redaction.

The current implementation prioritizes simplicity and local
debugging for this assessment.


### Live end-to-end scenarios

The following six GN-required requests were exercised through the CLI against GN's hosted LLM and the running FastAPI server on **9 November 2026**, with appropriate responses observed:

1. `Create a new ticket about a keyboard not working.` — ticket created with `OPEN` status.
2. `Retrieve all open tickets.` — open ticket listed.
3. `Get details for ticket 1.` — ticket details returned.
4. `Update ticket 1 to have status PROGRESS.` — agent explained invalid status and listed allowed values from the API's `422` detail.
5. `Update ticket 1 to RESOLVED, adding 'Replaced faulty cable' as the resolution.` — agent confirmed status and resolution.
6. `Update ticket 999 to CLOSED.` — agent explained that the nonexistent ticket could not be updated (`404`).

For a fresh demonstration, replace `1` with the actual created ticket ID. You can inspect final stored state via `GET /tickets/{ticket_id}` or Swagger UI without an LLM request. GN monitors usage, so keep live calls focused; use mocked tests during development.

Optional code quality checks:

```bash
python -m ruff check .
python -m ruff format --check .
```

## Production considerations

**Persistence:** The in-memory dictionary is deliberately simple but loses tickets after restarts and cannot share state across server processes. In production, use a database while preserving API contracts and error semantics.

Further production improvements would include authentication/authorization, explicit confirmation for destructive operations, stronger timeout/retry policy, durable audit logs, observability, and persisted conversations. The optional requirement to require a resolution note when resolving a ticket was not implemented in this mock API.

## Remaining scope

**Part 3:** Implement a PR-diff analysis script that calls an LLM and posts one review comment, with GitHub Actions triggered on pull requests (`opened` and `synchronize`).

**Part 4:** Add a minimal valid Azure Terraform configuration under `infra/` (`main.tf`, `variables.tf`, `outputs.tf`). Deployment is not required.

The optional MCP server has not been implemented.
