import logging
import os
import sys
from pathlib import Path


def setup_logging(log_level: int = logging.INFO) -> None:
    """Configures structured, local-only logging for TRIAD."""
    log_dir = Path(os.environ.get("LOCALAPPDATA", ".")) / "TRIAD" / "logs"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "triad.log"
    except Exception:
        log_file = None

    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if log_file:
        try:
            handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
        except Exception:
            pass

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
        force=True,
    )


def get_logger(name: str) -> logging.Logger:
    """Returns a logger instance with TRIAD namespace."""
    return logging.getLogger(f"triad.{name}")

