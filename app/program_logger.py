import logging, os, sys
from datetime import datetime
import colorlog

def setup_logger(log_dir):
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, f"runtime_log_{datetime.now().strftime('%Y%m%d%H%M')}.log")

    logger = logging.getLogger()
    if logger.hasHandlers():
        return logger

    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s]: %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # File Handler
    file_handler = logging.FileHandler(log_path, encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console Handler with colors if colorlog is available
    if colorlog:
        color_formatter = colorlog.ColoredFormatter(
            "%(log_color)s%(asctime)s [%(levelname)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold_red",
            },
        )
        console_handler = colorlog.StreamHandler(sys.stdout)
        console_handler.setFormatter(color_formatter)
    else:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    return logger

def cleanup_logger(logger):
    handlers = logger.handlers[:]
    for handler in handlers:
        try:
            handler.flush()
            handler.close()
        except Exception:
            pass
        logger.removeHandler(handler)