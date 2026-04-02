import logging, os,sys, traceback, functools
from datetime import datetime

DEFAULT_FORMAT = "%(asctime)s [%(levelname)s]: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

def _get_formatter():
    return logging.Formatter(DEFAULT_FORMAT, datefmt=DATE_FORMAT)

def _add_console_handler(logger, level):
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_get_formatter())
    handler.setLevel(level)
    logger.addHandler(handler)

def setup_logger(
    name="app_logger",
    log_dir="logs",
    log_level=logging.INFO,
    to_console=True,
    to_file=True
):
    os.makedirs(log_dir, exist_ok=True)
    logger = logging.getLogger(name)
    if logger.hasHandlers():
        return logger
    logger.setLevel(log_level)
    logger.propagate = False

    if to_file:
        file_path = os.path.join(log_dir, f"{name}.log")
        file_handler = logging.FileHandler(file_path, encoding='utf-8')
        file_handler.setFormatter(_get_formatter())
        file_handler.setLevel(log_level)
        logger.addHandler(file_handler)

    if to_console:
        _add_console_handler(logger, log_level)

    return logger

_active_logger = None

def set_global_logger(logger):
    global _active_logger
    _active_logger = logger

def get_global_logger():
    return _active_logger or logging.getLogger("default_logger")

def log_exceptions(level="error", return_value=None, raise_error=False):
    """
    Logs exceptions with traceback and context.
    If raise_error=True, re-raises after logging.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_global_logger()
            try:
                return func(*args, **kwargs)
            except Exception as e:
                cls_name = args[0].__class__.__name__ if args else ""
                file_name = getattr(args[0], "FILE_NAME", None) if args else None

                context = f"[{cls_name}.{func.__name__}]"
                if file_name:
                    context += f" ({file_name})"

                log_func = getattr(logger, level, logger.error)
                log_func(f"{context} {type(e).__name__}: {e}")
                logger.error(traceback.format_exc())

                if raise_error:
                    raise
                return return_value
        return wrapper
    return decorator
