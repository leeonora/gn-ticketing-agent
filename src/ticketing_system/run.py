import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

HOST = "127.0.0.1"
PORT = 8000
HEALTH_URL = f"http://{HOST}:{PORT}/health"
STARTUP_TIMEOUT = 15


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
    if not Path(".env").is_file():
        print("Missing .env file. Copy .env.example to .env and configure it.")
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
