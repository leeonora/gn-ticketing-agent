# GN Ticketing Agent

A fault-tolerant, AI-powered support ticketing system developed as part of a technical assessment.

The project consists of a REST API for ticket management, an LLM-based agent for interacting with the API, an automated pull request review workflow, and infrastructure configuration for Azure.

## Tech Stack

- **Python** : Application development
- **FastAPI** : REST API
- **Pydantic** : Data validation
- **HTTPX** : HTTP client
- **OpenAI Python SDK** : LLM integration
- **pytest** : Automated testing
- **GitHub Actions** : CI/CD automation
- **Terraform** : Infrastructure as Code

## Project Structure

```text
gn-ticketing-agent/
├── src/
│   └── ticketing_system/
│       ├── api/          # Ticket management REST API
│       └── agent/        # AI agent and API tools (planned)
├── tests/                # Automated tests
├── scripts/              # PR review automation (planned)
├── infra/                # Terraform configuration (planned)
├── pyproject.toml        # Project metadata and dependencies
├── .env.example          # Environment configuration template
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.11 or newer
- Git

### Installation

Clone the repository and navigate to the project directory:

```bash
git clone <repository-url>
cd gn-ticketing-agent
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate the environment:

**macOS/Linux (Bash or Zsh):**

```bash
source .venv/bin/activate
```

**Fish shell:**

```fish
source .venv/bin/activate.fish
```

**Windows PowerShell:**

```powershell
.venv\Scripts\Activate.ps1
```

Install the project and development dependencies:

```bash
python -m pip install -e ".[dev]"
```

### Environment Configuration

Copy the example environment file:

```bash
cp .env.example .env
```

Add the required API credentials to `.env`. Never commit actual API keys or secrets to version control.

## Development Status

This project is under active development.

Planned components:

- [ ] Mock ticketing REST API with CRUD operations
- [ ] Business logic validation and HTTP error handling
- [ ] LLM agent with tool calling
- [ ] Automated tests
- [ ] LLM-based pull request review workflow
- [ ] Terraform configuration for Azure

## Running the Application

Instructions will be added as components are implemented.

## Testing

Once tests have been implemented, run:

```bash
pytest
```
