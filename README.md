# GN Ticketing Agent

I prepared this project for GN's recruitment process, and I look forward to discussing it at the second interview! It includes a mock support-ticketing API, a natural-language agent, and an automated pull-request reviewer, as well as a Terraform skeleton.

To try it, start with the [installation instructions](#local-setup). For the big picture, see the [architecture overview](#stack-and-architecture). The implementation details are in [Part 1: Ticketing API](#part-1-ticketing-api), [Part 2: GenAI agent](#part-2-natural-language-ticketing-agent), [Part 3: PR Review and CI](#part-3-automated-pr-review-and-ci), [Part 4: Azure Terraform](#part-4-azure-terraform-skeleton), and [Part 5: Production design decision](#part-5-optional-production-considerations).

## Local setup

**Prerequisites:** Git and an authorized GN API key for live agent use. The recommended setup uses [uv](https://docs.astral.sh/uv/getting-started/installation/), which can install a compatible Python version. If you don't have or prefer not to use uv, see [Alternative installation: pip](#install-with-pip). Local tests and the mock API do not require the GN API key.

### Install and run with uv

From a fresh clone, run these commands in macOS, Linux, or Windows PowerShell:

```bash
git clone https://github.com/leeonora/gn-ticketing-agent.git
cd gn-ticketing-agent
uv sync --extra dev
```

`uv sync` creates `.venv` and installs the project and test tools from `uv.lock`.

Start the API and agent together:

```bash
uv run gn-ticketing
```

If `OPENAI_API_KEY` is missing or still the example placeholder, the launcher asks for it with hidden input and saves it to `.env` for future runs. 
- If `.env` does not exist, the launcher creates it from `.env.example`.
- The file is Git-ignored and restricted to your user account, but it stores the key as plaintext. 
- The prompt requires an interactive terminal.

Alternatively, manually create `.env` from `.env.example` and add your authorized GN key before launching:

```bash
# macOS / Linux
cp .env.example .env
```

```powershell
# Windows PowerShell
Copy-Item .env.example .env
```

Remaining settings (URLs, model selection, and conversation log toggling) are already in `.env.example`. Keep `.env` and credentials out of Git.

The launcher starts FastAPI, waits for its health check, and opens the CLI. Type `exit` to stop both processes. Try `Create a ticket about a broken keyboard` or `List open tickets`. API docs are at <http://127.0.0.1:8000/docs> while it runs.

Startup messages and HTTP tool logs (for example, `Sending POST request to /tickets` and `HTTP 201`) appear in the terminal alongside the agent's answer so the API interaction is easy to follow during this assessment. They are diagnostic output, not part of the agent's reply. In a production interface, these logs would be kept out of the user-facing conversation and routed to application logging instead.

Run checks with:

```bash
uv run --extra dev python -m pytest
uv run --extra dev ruff check .
uv run --extra dev ruff format --check .
```

<details id="install-with-pip">
<summary>Alternative installation: pip</summary>

### Install with pip

After cloning the repository, use Python 3.11 or newer when creating a virtual environment. Upgrade pip inside it before installing the project; older pip versions cannot install this `pyproject.toml` project in editable mode.

**macOS / Linux (Bash or Zsh):**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

For Fish, activate with `source .venv/bin/activate.fish` instead.

**Windows (PowerShell):**

Select a specific installed Python version. The `py -3` shortcut may use an older configured default even when a newer version is installed. Replace `3.11` below with another installed version of 3.11 or newer if needed. `--clear` replaces a virtual environment previously created with the wrong Python version.

```powershell
py -3.11 -m venv --clear .venv
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Create `.env` as shown above. 

Run with:

```powershell
# With the environment activated:
gn-ticketing

# On Windows, without activation:
.\.venv\Scripts\gn-ticketing.exe
```

</details>

### Troubleshooting

If the launcher fails, check that port `8000` is free and inspect `logs/api-server.log`. With pip, `command not found` usually means the virtual environment is not active or the project needs reinstalling. You can also run the launcher with `uv run python -m ticketing_system.run`.

<details>
<summary>Alternative way to run: separate API and CLI terminals</summary>

### Run the API and CLI separately

To debug the services independently, use two terminals after installation:

**Terminal 1: API:**

```bash
uv run uvicorn ticketing_system.api.main:app --reload
```

**Terminal 2: agent:**

```bash
uv run python -m ticketing_system.agent.cli
```

</details>

## Status

| Part                   | Implementation                                                                                     | Verification                                                                                         |
| ---------------------- | -------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| **1. Ticketing API**   | FastAPI CRUD, filtering, validation (including required resolution notes), soft delete and restore | 24 API tests passed                                                                                  |
| **2. AI agent**        | Pydantic AI CLI with six HTTP-backed tools                                                         | 9 agent tests, 7 CLI tests; live GN scenarios demonstrated                                           |
| **3. PR review bot**   | GitHub Actions + Python + Pydantic AI; posts one review comment per run                            | 7 tests passed; [PR #1 successfully reviewed](https://github.com/leeonora/gn-ticketing-agent/pull/1) |
| **4. Azure Terraform** | Resource group, Linux App Service plan, and Linux Web App                                          | `terraform init` and `terraform validate` succeeded                                                  |

**Latest local verification (12 November 2026): 63 tests passed**, Ruff lint and formatting checks passed.

## Stack and architecture

Python 3.11+, FastAPI, Pydantic, Uvicorn, HTTPX, Pydantic AI (`pydantic-ai-slim[openai]`), OpenAI-compatible GN endpoint, pytest, and Ruff.

The ticketing agent selects tools, but **ticket operations are performed through HTTP** rather than accessing the ticket store directly. FastAPI enforces validation and returns errors for the agent to explain to users.

### Ticketing agent architecture

![Ticketing agent architecture](docs/diagrams/architecture_ticketing_agent.png)

_Created with_ [_Miro_](https://miro.com/)_._
### PR review agent architecture

![PR review agent architecture](docs/diagrams/architecture_PR_agent.png)

_Created with_ [_Miro_](https://miro.com/)_._
## Part 1: Ticketing API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Health check |
| `POST` | `/tickets` | Create ticket (`201`) |
| `GET` | `/tickets` | List; optional `?status=OPEN` filter |
| `GET` | `/tickets/{id}` | Retrieve ticket |
| `PATCH` | `/tickets/{id}` | Update fields |
| `DELETE` | `/tickets/{id}` | Soft-delete (`204`) |
| `POST` | `/tickets/{id}/restore` | Restore deleted ticket (`200`) |

- Tickets contain `id`, `title`, `description`, UTC `created`, `status`, `resolution`, and `deleted`. 
- Status must be `OPEN`, `RESOLVED`, or `CLOSED` (invalid updates return **422**). 
- Missing/deleted tickets return **404** on normal operations; restoring an active ticket returns **409**.
- Resolution notes: Resolving a ticket requires a non-empty resolution note (either provided in the request or already present). Missing or blank notes return `422`.
- Updates are validated before saving so invalid changes do not partially apply.
- Deletion sets `deleted=true`, hides the ticket from normal retrieval/listing, and allows restoration with its original data. 
- Store operations use a lock to protect concurrent requests within one server process. Multiple worker processes would still have separate stores.
- **Storage is in memory**: restarting the server loses active and deleted tickets alike.

Example API requests (no LLM usage):

```bash
curl -X POST http://127.0.0.1:8000/tickets \
  -H 'Content-Type: application/json' \
  -d '{"title":"Broken keyboard","description":"Keys are unresponsive"}'
curl 'http://127.0.0.1:8000/tickets?status=OPEN'
curl -i -X PATCH http://127.0.0.1:8000/tickets/1 \
  -H 'Content-Type: application/json' \
  -d '{"status":"RESOLVED","resolution":"Replaced faulty cable"}'
curl -i -X DELETE http://127.0.0.1:8000/tickets/1
curl -i -X POST http://127.0.0.1:8000/tickets/1/restore
```

Replace `1` with an ID that exists in your current server session. Omitting `resolution` when resolving a ticket without an existing note returns **422**:

```json
{"detail":"A resolution note is required when setting a ticket's status to RESOLVED."}
```

The failed update leaves the ticket unchanged.

## Part 2: Natural-language ticketing agent

The Pydantic AI agent uses six HTTPX-backed tools to interact with the ticketing API: `list_tickets`, `get_ticket`, `create_ticket`, `update_ticket`, `delete_ticket`, and `restore_ticket`.

**Error handling:** The agent interprets API errors (e.g., `404`, `422`) and provides actionable feedback. Network and model failures are handled gracefully, with warnings to check ticket state before repeating potentially completed write operations.

**Security:** Ticket content and API responses are treated as untrusted data, not instructions. This provides a prompt-level safeguard against unintended tool calls.

**Verification:** All six required GN scenarios and an additional missing-resolution scenario passed with the live GN-hosted LLM. See [Agent Verification](docs/verification.md) for the recorded results.

## Part 3: Automated PR Review and CI

The project uses two independent GitHub Actions workflows to automate pull request reviews and code quality checks. Both workflows run when a pull request is opened or updated.

### AI Pull Request Reviewer

The PR review workflow (`.github/workflows/pr_review.yml`) runs `scripts/analyze_pr.py`, which uses Pydantic AI and GN's LLM to analyze the pull request diff and post a single review comment containing a summary and suggested improvements.

**Setup:** Add `GN_API_KEY` under **Settings → Secrets and variables → Actions** in the GitHub repository. GitHub provides `GITHUB_TOKEN` automatically.

**Safeguards:** The reviewer installs dependencies from `uv.lock` using `uv sync --locked`. Only same-repository pull requests are reviewed. PR code is not executed, the diff is limited to 20,000 characters, and the reviewer makes one model request per run.

### Continuous Integration (CI)

The CI workflow (`.github/workflows/ci.yml`) runs automatically when a pull request is opened, updated, or reopened. It performs the following checks:

- **pytest:** Runs the automated test suite for the API, agent, CLI, and PR reviewer.
- **Ruff linting:** Identifies potential Python errors and style violations.
- **Ruff formatting:** Checks consistent Python formatting.
- **Terraform formatting:** Checks infrastructure configuration formatting.
- **Terraform validation:** Initializes Terraform without configuring the backend and validates the infrastructure configuration without deploying any resources.

Unlike the AI reviewer, the CI workflow does not require a GN API key or make LLM calls.

### Verification

- **[PR #1](https://github.com/leeonora/gn-ticketing-agent/pull/1):** Demonstrated the initial AI reviewer successfully posting an automated review.
- **[PR #2](https://github.com/leeonora/gn-ticketing-agent/pull/2):** Both GitHub Actions workflows completed successfully. The CI workflow passed all automated checks, while the AI reviewer analyzed the new CI configuration and suggested improvements to Terraform version management and GitHub Actions dependency pinning.

The second pull request also verified the updated PR reviewer, including its trusted-base checkout safeguard.

## Part 4: Azure Terraform skeleton

The `infra/` directory defines a minimal, validated Terraform configuration describing how the FastAPI service could be hosted on Azure, using three resources:

- **Resource group** – Organizes Azure resources.
- **Linux App Service plan** (`B1`) – Provides compute capacity.
- **Linux Web App (Python 3.13)** – Defines the application hosting environment.

The configuration is organized into `main.tf`, `variables.tf`, and `outputs.tf`.

**Validate locally** (Terraform CLI required):

```
cd infra
terraform fmt -check
terraform init
terraform validate
```

**Verification (10 November 2026):** Initialization, formatting, and validation passed locally using AzureRM `v4.81.0`.

**Scope:** Infrastructure configuration only. No Azure resources were deployed, as deployment is not required by the assessment.

## Tests and code quality

Run the automated tests and code quality checks:

```bash
uv run --extra dev python -m pytest -v
uv run --extra dev ruff check .
uv run --extra dev ruff format --check .
```

| Tests | Cases | What they check |
| --- | ---: | --- |
| `tests/test_api.py` | 24 | CRUD, filtering, resolution-note validation, delete/restore, HTTP errors |
| `tests/test_agent.py` | 9 | Registered tools through HTTP: all six assessment scenarios, delete/restore, and retrieval 404; API details forwarded to a scripted model |
| `tests/test_cli.py` | 7 | CLI interaction, history forwarding, limits, partial-write failures, optional conversation logging |
| `tests/test_tools.py` | 9 | Connection/timeout failures, structured API errors, malformed responses, ambiguous writes without retries, and exclusion of raw error details from logs |
| `tests/test_store.py` | 2 | Concurrent creation and updates without lost tickets or fields |
| `tests/test_run.py` | 5 | Launcher API-key prompt, secure saving, example-key detection, non-interactive handling |
| `tests/test_pr_review.py` | 7 | Mocked GitHub diff/comment HTTP calls and review invocation |
| **Total** | **63** | **All passed locally; no GN calls in tests** |

## Logging

API operations, HTTP responses, and CLI errors are recorded in console and rotating file logs (`logs/ticketing.log`). Logs are Git-ignored.

Conversation logging is disabled by default (`LOG_CONVERSATIONS=false`) and can be enabled in `.env` for nonsensitive test data.

HTTP failure logs contain operation metadata (method, endpoint, status or exception type, and duration), without raw API error bodies. Error details are still returned to the agent for user feedback. Enabling conversation logging may record those details in the agent's response.

File logging is intended for local development only.
## Part 5 (optional): Production considerations

The most important production improvement would be replacing the in-memory ticket store with persistent database storage, ensuring tickets survive application restarts. This could be done while preserving the existing API contracts and error handling.

Additional improvements could include authentication, audit logging, and a React frontend for a more accessible user experience.

**MCP bonus:** Not implemented, as the agent already communicates with the API through dedicated HTTP-backed tools. MCP could be added if interoperability with other clients becomes necessary.
