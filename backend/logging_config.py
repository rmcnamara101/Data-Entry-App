# logging_config.py

import logging
import logging.handlers
import sys
from typing import Optional

def setup_logging(
    log_level: int = logging.INFO,
    log_to_file: bool = False,
    log_file_path: str = "app.log",
    max_bytes: int = 10**6,  # 1MB
    backup_count: int = 5
) -> None:
    """
    Sets up the logging configuration.

    Args:
        log_level (int): Logging level (e.g., logging.DEBUG, logging.INFO).
        log_to_file (bool): Whether to log to a file in addition to the console.
        log_file_path (str): Path to the log file.
        max_bytes (int): Maximum size in bytes before rotating the log file.
        backup_count (int): Number of backup log files to keep.
    """
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Define log format
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if log_to_file:
        # File handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            log_file_path, maxBytes=max_bytes, backupCount=backup_count
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)