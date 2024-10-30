import logging
from logging.handlers import RotatingFileHandler
import os
import datetime

# ANSI escape sequences for colors
class ColorFormatter(logging.Formatter):
    """Custom formatter to add colors to log levels"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[41m', # Red background
    }
    RESET = '\033[0m'

    def format(self, record):
        # Add colors only if it's not a file handler
        if isinstance(self.handler, logging.StreamHandler) and not isinstance(self.handler, logging.FileHandler):
            levelname = record.levelname
            if levelname in self.COLORS:
                record.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"
        return super().format(record)

def setup_logger(level=logging.INFO):
    """
    Set up a centralized logger with both console and file handlers
    
    Args:
        level (int): Logging level
    
    Returns:
        logging.Logger: Configured logger instance
    """
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')

    # Create log file with timestamp
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = f'logs/trading_{timestamp}.log'

    # Create formatters
    console_formatter = ColorFormatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Create logger
    logger = logging.getLogger('trading')
    logger.setLevel(level)

    # Clear any existing handlers
    logger.handlers = []

    # Create console handler with colors
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    console_formatter.handler = console_handler  # Set handler reference for color detection
    logger.addHandler(console_handler)

    # Create rotating file handler (10MB per file, max 5 files)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    return logger

# Create and export a single logger instance
logger = setup_logger()
