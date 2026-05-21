"""
Logging configuration for the trading bot.
Sets up both file and console handlers with structured formatting.
"""

import logging
import sys
from pathlib import Path


LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_FILE = LOG_DIR / "trading_bot.log"


def setup_logging(level: str = "INFO") -> logging.Logger:
    """
    Configure and return the root logger for the trading bot.

    File handler: DEBUG+ (captures everything for audit trail)
    Console handler: WARNING+ (keeps CLI output clean)
    """
    LOG_DIR.mkdir(exist_ok=True)

    numeric_level = getattr(logging, level.upper(), logging.INFO)

    logger = logging.getLogger("trading_bot")
    logger.setLevel(logging.DEBUG)          # capture everything at root

    if logger.handlers:
        return logger                        # already configured

    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    datefmt = "%Y-%m-%dT%H:%M:%S"
    formatter = logging.Formatter(fmt, datefmt=datefmt)

    # --- File handler (DEBUG and above) ---
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # --- Console handler (WARNING and above so CLI stays readable) ---
    ch = logging.StreamHandler(sys.stderr)
    ch.setLevel(logging.WARNING)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the 'trading_bot' namespace."""
    return logging.getLogger(f"trading_bot.{name}")
