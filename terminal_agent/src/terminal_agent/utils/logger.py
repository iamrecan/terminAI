"""Logging configuration for Terminal Agent."""

import logging
import sys
from pathlib import Path
from terminal_agent.core.config import LOG_LEVEL, PROJECT_ROOT

# Create logs directory if it doesn't exist
log_dir = PROJECT_ROOT / "logs"
log_dir.mkdir(exist_ok=True)

# Configure logging
log_file = log_dir / "terminal_agent.log"

# Create formatter
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create file handler
file_handler = logging.FileHandler(log_file)
file_handler.setFormatter(formatter)

# Create console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)

# Create logger
logger = logging.getLogger("terminal_agent")
logger.setLevel(getattr(logging, LOG_LEVEL.upper()))
logger.addHandler(file_handler)
logger.addHandler(console_handler)

def get_logger(name):
    """Get a logger instance for the given name."""
    return logging.getLogger(f"terminal_agent.{name}")
