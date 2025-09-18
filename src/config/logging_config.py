"""Logging configuration for the application."""

import logging
from .paths import LOGS_DIR

def setup_logging():
    """Setup application logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(LOGS_DIR / "app.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    return logging.getLogger("tchai")