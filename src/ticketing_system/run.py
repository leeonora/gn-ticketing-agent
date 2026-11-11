import getpass
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from dotenv import load_dotenv, set_key

HOST = "127.0.0.1"
PORT = 8000
HEALTH_URL = f"http://{HOST}:{PORT}/health"
STARTUP_TIMEOUT = 15
EXAMPLE_KEYS = {
    "your_api_key_here",
    "your_gn_api_key_here",
    "your_subscription_key",
    "test-key-not-for-production",
}


def _has_control_character(value: str) -> bool:
    return any(ord(char) < 32 or ord(char) == 127 for char in value)


def ensure_api_key() -> bool:
    """Prompt for a missing example key before starting the agent."""
    load_dotenv(dotenv_path=Path.cwd() / ".env")
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if key and key.lower() not in EXAMPLE_KEYS and not _has_control_character(key):
        return True

    if not sys.stdin.isatty():
        print("Missing OPENAI_API_KEY. Set it in .env or run from a terminal.")
        return False

    while True:
        try:
            key = getpass.getpass("Enter your GN API key (input hidden): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAPI key entry cancelled.")
            return False

        if not _has_control_character(key):
            break
        print(
            "Input contained a control character. Use your terminal's Paste command "
            "instead of Ctrl+V, or enter the key directly in .env."
        )

    if not key or key.lower() in EXAMPLE_KEYS:
        print("No valid API key entered. Add it to .env and try again.")
        return False

    os.environ["OPENAI_API_KEY"] = key
    dotenv_path = Path.cwd() / ".env"
    try:
        if dotenv_path.is_symlink():
            raise OSError("Refusing to replace a symlinked .env file")
        example_path = dotenv_path.with_name(".env.example")
        if not dotenv_path.exists() and example_path.is_file():
            example_contents = example_path.read_text(encoding="utf-8")
            fd = os.open(dotenv_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as env_file:
                env_file.write(example_contents)
        set_key(dotenv_path, "OPENAI_API_KEY", key)
        dotenv_path.chmod(0o600)
    except OSError as exc:
        print(f"Could not save the key to .env ({exc}). It will work for this run.")
    else:
        print("API key saved to .env for future runs.")
    return True


def wait_for_api(process: subprocess.Popen) -> None:
    """Wait until FastAPI is ready to accept requests."""
    deadline = time.monotonic() + STARTUP_TIMEOUT

    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("The API process stopped during startup.")

        try:
            with urlopen(HEALTH_URL, timeout=1) as response:
                if response.status == 200:
                    return
        except (URLError, TimeoutError, OSError):
            pass

        time.sleep(0.2)

    raise RuntimeError("The API did not become ready in time.")


def main() -> int:
    """Start the API, run the agent CLI, then shut down the API."""
    if not ensure_api_key():
        return 1

    try:
        with socket.create_connection((HOST, PORT), timeout=1):
            print(f"Port {PORT} is already in use. Stop the existing server.")
            return 1
    except OSError:
        pass

    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    print("Starting GN Ticketing Agent...", flush=True)

    with (log_dir / "api-server.log").open("a") as log:
        api = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "ticketing_system.api.main:app",
                "--host",
                HOST,
                "--port",
                str(PORT),
            ],
            stdout=log,
            stderr=subprocess.STDOUT,
        )

        try:
            wait_for_api(api)
            print("API ready. Starting agent...\n", flush=True)

            return subprocess.call(
                [
                    sys.executable,
                    "-m",
                    "ticketing_system.agent.cli",
                ]
            )

        except RuntimeError as exc:
            print(f"Startup failed: {exc}")
            print("Check logs/api-server.log for details.")
            return 1

        except KeyboardInterrupt:
            return 130

        finally:
            if api.poll() is None:
                api.terminate()
                try:
                    api.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    api.kill()
                    api.wait()

            print("\nTicketing API stopped.", flush=True)


if __name__ == "__main__":
    sys.exit(main())
