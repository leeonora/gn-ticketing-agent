import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(
    log_level: int = logging.INFO,
    log_dir: str | Path = "logs",
) -> logging.Logger:
    """Configure console and rotating file logging for the ticketing system."""

    logger = logging.getLogger("ticketing_system")
    logger.setLevel(log_level)

    # Avoid adding duplicate handlers if setup_logging is called twice.
    if getattr(logger, "_ticketing_configured", False):
        return logger

    # Create the logs directory if it does not exist.
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Define a consistent format for all log messages.
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Handler 1: Display log messages in the terminal.
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)

    # Handler 2: Save log messages to a rotating file.
    file_handler = RotatingFileHandler(
        filename=log_path / "ticketing.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)

    # Attach both handlers to our application's logger.
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    # Prevent forwarding our log records to the root logger.
    logger.propagate = False

    logger._ticketing_configured = True

    return logger
