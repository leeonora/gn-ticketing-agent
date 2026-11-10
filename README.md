# GN Ticketing Agent

A mock support-ticketing API, a natural-language agent, and an automated AI pull-request reviewer. Built for GN's **End-to-End Fault-Tolerant GenAI Agent System** assessment.

## Status

| Part | Implementation | Verification |
| --- | --- | --- |
| **1 — Ticketing API** | FastAPI CRUD, filtering, validation, soft delete and restore | 17 API tests passed |
| **2 — GenAI agent** | Pydantic AI CLI with six HTTP-backed tools | 9 agent tests, 4 CLI tests; live GN scenarios demonstrated |
| **3 — PR review bot** | GitHub Actions + Python + Pydantic AI; posts one review comment per run | 7 tests passed; [PR #1 successfully reviewed](https://github.com/leeonora/gn-ticketing-agent/pull/1) |
| **4 — Azure Terraform** | Resource group, Linux App Service plan, and Linux Web App | `terraform init` and `terraform validate` succeeded (10 November 2026) |

**Latest local verification (10 November 2026): 37 tests passed**, Ruff lint checks passed. One non-failing third-party Python 3.13/Pydantic Graph deprecation warning remains. Optional MCP server not implemented.

## Stack and architecture

Python 3.11+, FastAPI, Pydantic, Uvicorn, HTTPX, Pydantic AI (`pydantic-ai-slim[openai]`), OpenAI-compatible GN endpoint, pytest, and Ruff.

```text
User → CLI → Pydantic AI / GN LLM → registered HTTP tools → FastAPI → in-memory tickets
                         ↑                      ↓
                  tool results ← HTTP responses (including 404/409/422)

Pull request → GitHub Actions → scripts/analyze_pr.py
                               ├─ fetch diff (GitHub REST API)
                               ├─ review diff (Pydantic AI / GN LLM)
                               └─ post PR comment (GitHub REST API)
```

The ticketing agent selects tools, but **ticket operations are performed through HTTP** rather than accessing the ticket store directly. FastAPI enforces validation and returns errors for the agent to explain to users.

## Local setup

**Prerequisites:** Python 3.11+, Git, and an authorized GN API key for live agent use. Local tests and the mock API do not require the GN key.

```bash
git clone https://github.com/leeonora/gn-ticketing-agent.git
cd gn-ticketing-agent
python -m venv .venv
source .venv/bin/activate          # Bash / Zsh (macOS/Linux)
# Fish: source .venv/bin/activate.fish
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
cp .env.example .env
```

Set the following values in your local `.env` (the repository's `.env.example` contains placeholders only):

```dotenv
OPENAI_API_KEY=your_gn_api_key_here
OPENAI_BASE_URL=https://models.genie.gn.group/openai/v1
OPENAI_MODEL=gpt-6-luna
TICKETING_API_BASE_URL=http://127.0.0.1:8000
LOG_CONVERSATIONS=false
```

Keep `.env` and credentials out of Git. The GN integration uses an OpenAI-compatible client with an `api-key` header; `openai_reasoning_effort="none"` is used for compatibility with GN's Chat Completions/function-tool behavior.

**Terminal 1 — start the API:**

```bash
uvicorn ticketing_system.api.main:app --reload
```

API docs: <http://127.0.0.1:8000/docs> · Health check: <http://127.0.0.1:8000/health>

**Terminal 2 — start the conversational agent:**

```bash
python -m ticketing_system.agent.cli
```

Type requests such as `Create a ticket about a broken keyboard`, `List open tickets`, or `Restore ticket 1`. Use `exit` or `quit` to end the session. The CLI retains conversation history across turns and applies per-run limits of five model requests and five tool calls. These are execution limits, **not** a guaranteed token or cost budget.

For Fish, you can suppress Pydantic AI's informational banner before starting the CLI with `set -x PYDANTIC_AI_NO_BANNER 1`.

## Part 1 — Ticketing API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Health check |
| `POST` | `/tickets` | Create ticket (`201`) |
| `GET` | `/tickets` | List; optional `?status=OPEN` filter |
| `GET` | `/tickets/{id}` | Retrieve ticket |
| `PATCH` | `/tickets/{id}` | Update fields |
| `DELETE` | `/tickets/{id}` | Soft-delete (`204`) |
| `POST` | `/tickets/{id}/restore` | Restore deleted ticket (`200`) |

Tickets contain `id`, `title`, `description`, UTC `created`, `status`, `resolution`, and `deleted`. Status must be `OPEN`, `RESOLVED`, or `CLOSED` (invalid updates return **422**). Missing/deleted tickets return **404** on normal operations; restoring an active ticket returns **409**. Updates are validated before saving so invalid changes do not partially apply.

Deletion sets `deleted=true`, hides the ticket from normal retrieval/listing, and allows restoration with its original data. **Storage is in memory**: restarting the server loses active and deleted tickets alike.

Example API requests (no LLM usage):

```bash
curl -X POST http://127.0.0.1:8000/tickets \
  -H 'Content-Type: application/json' \
  -d '{"title":"Broken keyboard","description":"Keys are unresponsive"}'
curl 'http://127.0.0.1:8000/tickets?status=OPEN'
curl -i -X DELETE http://127.0.0.1:8000/tickets/1
curl -i -X POST http://127.0.0.1:8000/tickets/1/restore
```

Replace `1` with an ID that exists in your current server session.

## Part 2 — Natural-language ticketing agent

The CLI's Pydantic AI agent registers six HTTPX-backed tools: `list_tickets`, `get_ticket`, `create_ticket`, `update_ticket`, `delete_ticket`, and `restore_ticket`. Tool results contain success/error status and actual API error details; the agent explains these to the user instead of inventing a successful operation.

**Live GN verification (9 November 2026):** All six required assessment scenarios succeeded: create a keyboard ticket, list open tickets, retrieve details, reject `PROGRESS` with valid statuses, resolve with a note, and report a nonexistent ticket (`404`).

**Live GN verification (10 November 2026):** In one multi-turn conversation, the agent created a ticket, soft-deleted it after “Delete that ticket,” and restored it after “Actually, can you undo that?” Direct API retrieval confirmed `deleted=false`. These were live LLM/API interactions; repeatable tests use mocks instead.

## Part 3 — Automated PR review

On pull requests **opened** or **synchronized**, `.github/workflows/pr_review.yml` runs `scripts/analyze_pr.py`. The script retrieves the diff from GitHub, sends it to a dedicated Pydantic AI reviewer using GN's model, and posts **one general PR comment per successful execution** with a summary and suggestions. It does not execute PR code.

**To configure GitHub Actions:** In repository **Settings → Secrets and variables → Actions**, create a repository secret called `GN_API_KEY` containing the authorized GN key. The workflow receives `GITHUB_TOKEN` from GitHub automatically; no personal GitHub token is required. It is limited to **same-repository PRs** (not forks), with `contents: read` and `pull-requests: write` permissions. The workflow installs dependencies with `python -m pip install -e ".[dev]"`.

**Verified end to end:** [Pull request #1](https://github.com/leeonora/gn-ticketing-agent/pull/1) ran the GitHub Actions job successfully and received an automated comment from `github-actions[bot]`, containing a review of the changes and improvement suggestions.

The reviewer limits input to the first **20,000 characters** of the diff and to **one model request per run**. Very large diffs may be reviewed only partially; new workflow runs create new comments rather than updating an earlier one. Model-generated feedback is advisory.

## Part 4 — Azure Terraform skeleton

The `infra/` directory defines a minimal potential Azure hosting setup for the Part 1 FastAPI service:

| Resource | Purpose |
| --- | --- |
| Azure resource group | Groups the application's Azure resources |
| Linux App Service plan (`B1`) | Provides compute capacity for a Linux-hosted application |
| Linux Web App (Python 3.13) | Defines where the FastAPI service could run |

The configuration is split across `main.tf` (provider and resources), `variables.tf` (resource group name, region, web app name), and `outputs.tf` (the web app's HTTPS URL). The generated `.terraform.lock.hcl` records the selected AzureRM provider version.

**Validate locally** (Terraform CLI required; no Azure credentials or GN key needed):

```bash
cd infra
terraform fmt -check
terraform init
terraform validate
```

**Verified locally on 10 November 2026:** `terraform init` succeeded with AzureRM `v4.81.0`, and `terraform validate` reported `Success! The configuration is valid.` The `terraform fmt` command also ran without errors.

**Scope:** This is infrastructure configuration only. It does not package or upload the Python application, install its dependencies in Azure, or define a deployment pipeline or startup command. No `terraform plan` or `terraform apply` was performed, and no Azure resources were created. A real deployment would require additional application deployment configuration and a globally unique Web App name; the current B1 plan would incur charges if provisioned.

## Tests and code quality

```bash
python -m pytest -v
python -m ruff check .
python -m ruff format --check .
```

| Tests | Cases | What they check |
| --- | ---: | --- |
| `tests/test_api.py` | 17 | CRUD, filtering, validation, delete/restore, HTTP errors |
| `tests/test_agent.py` | 9 | Mocked registered tool calls and result forwarding |
| `tests/test_cli.py` | 4 | CLI interaction, limits, optional conversation logging |
| `tests/test_pr_review.py` | 7 | Mocked GitHub diff/comment HTTP calls and review invocation |
| **Total** | **37** | **All passed locally; no GN calls in tests** |

## Logging

Console and rotating logs (`logs/ticketing.log`) record API/tool operations, HTTP status codes, elapsed times, and CLI execution/error events. Rotation uses **5 MiB per file with three backups**. The `logs/` directory is Git-ignored.

`LOG_CONVERSATIONS=false` by default; set it to `true` in local `.env` to log user prompts and final responses. Only enable it with nonsensitive test data; previously captured text is not automatically erased when the setting is disabled. File logging is intended for local development, not multiprocess production logging.

## Part 5 (optional) — Production design decision

The most important production change would be **persistent storage** with a defined deletion-retention policy: the current in-memory store loses all tickets on restart. Other production needs include authentication/authorization, audit trails, stronger observability, and safeguards around destructive actions. The optional rule requiring resolution notes was not implemented.

The optional MCP server (Part 2 bonus) was not implemented. The Azure infrastructure remains intentionally undeployed.
