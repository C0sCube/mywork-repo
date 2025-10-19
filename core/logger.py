# core/logger.py
import logging, colorlog, sys, traceback

def get_logger(name="fedup", level=logging.INFO):
    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter(
        "%(log_color)s[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "bold_red",
        }
    ))

    logger = logging.getLogger(name)
    if not logger.hasHandlers():
        logger.addHandler(handler)
        logger.setLevel(level)
    return logger

def trace_exception(logger, msg):
    """Helper to log full traceback with context."""
    logger.error(f"{msg}\n{traceback.format_exc()}")
