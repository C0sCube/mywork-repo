import logging, functools, traceback, os,sys
from datetime import datetime

# --- Custom Log Levels ---
TRACE_LEVEL_NUM = 15
SAVE_LEVEL_NUM = 22
NOTICE_LEVEL_NUM = 35

logging.addLevelName(TRACE_LEVEL_NUM, "TRACE")
logging.addLevelName(SAVE_LEVEL_NUM, "SAVE")
logging.addLevelName(NOTICE_LEVEL_NUM, "NOTICE")

# --- Default Format ---
DEFAULT_FORMAT = "%(asctime)s [%(levelname)s]: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

def _get_formatter():
    return logging.Formatter(DEFAULT_FORMAT, datefmt=DATE_FORMAT)

def _add_console_handler(logger, level):
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_get_formatter())
    handler.setLevel(level)
    logger.addHandler(handler)


# Logging levels:
# Level      Value   Description
# DEBUG      10      Detailed info, useful for debugging
# INFO       20      General runtime events
# WARNING    30      Something unexpected, but not an error
# ERROR      40      Serious issue, part of the program failed
# CRITICAL   50      Severe error, may crash the program
# TRACE SET TO 15
# SAVE SET TO 22
# NOTICE SET TO 35
# Default level is WARNING → shows WARNING, ERROR, CRITICAL

def setup_logger(
    name="app_logger",
    base_dir="logs",
    log_level=logging.INFO,
    to_console=True,
    to_file=True,
    set_global = False
):
    """Simple logger that creates a new dated folder each day."""
    today_dir = datetime.now().strftime("%Y-%m-%d")
    log_dir = os.path.join(base_dir, today_dir)
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger(name)
    if logger.hasHandlers():
        return logger
    logger.setLevel(log_level)
    logger.propagate = False

    # --- File handler
    if to_file:
        file_path = os.path.join(log_dir, f"{name}.log")
        file_handler = logging.FileHandler(file_path, encoding="utf-8")
        file_handler.setFormatter(_get_formatter())
        file_handler.setLevel(log_level)
        logger.addHandler(file_handler)

    # --- Console handler
    if to_console:
        _add_console_handler(logger, log_level)

    # --- Metadata for rotation
    logger._base_dir = base_dir
    logger._name = name
    logger._current_date = datetime.now().date()

    # --- Attach custom levels
    def trace(self, message, *args, **kwargs):
        if self.isEnabledFor(TRACE_LEVEL_NUM):
            self._log(TRACE_LEVEL_NUM, message, args, **kwargs)

    def save(self, message, *args, **kwargs):
        if self.isEnabledFor(SAVE_LEVEL_NUM):
            self._log(SAVE_LEVEL_NUM, message, args, **kwargs)

    def notice(self, message, *args, **kwargs):
        if self.isEnabledFor(NOTICE_LEVEL_NUM):
            self._log(NOTICE_LEVEL_NUM, message, args, **kwargs)

    logging.Logger.trace = trace
    logging.Logger.save = save
    logging.Logger.notice = notice
    
    if set_global:
        set_global_logger(logger)

    return logger


def rotate_daily_log(logger):
    """Call at app start or before long loops to move to a new daily folder."""
    today = datetime.now().date()
    if today != getattr(logger, "_current_date", None):
        logger.info("Rotating log folder for new day...")

        # Remove old file handler(s)
        for handler in list(logger.handlers):
            if isinstance(handler, logging.FileHandler):
                logger.removeHandler(handler)
                handler.close()

        # Create new folder & file
        today_dir = datetime.now().strftime("%Y-%m-%d")
        log_dir = os.path.join(logger._base_dir, today_dir)
        os.makedirs(log_dir, exist_ok=True)
        new_file = os.path.join(log_dir, f"{logger._name}.log")

        new_handler = logging.FileHandler(new_file, encoding="utf-8")
        new_handler.setFormatter(_get_formatter())
        new_handler.setLevel(logger.level)
        logger.addHandler(new_handler)

        logger._current_date = today
        logger.info(f"Logger rotated to new file: {new_file}")


# --- Global Logger Registry ---
_active_logger = None

def set_global_logger(logger):
    global _active_logger
    _active_logger = logger

def get_global_logger():
    return _active_logger or logging.getLogger("default_logger")


def log_exceptions(level="error", return_value=None):
    """
    Decorator that logs exceptions with traceback.
    Adds class name and file name (if available) for context.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_global_logger()
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Detect context — class, file name, etc.
                cls_name = args[0].__class__.__name__ if args else ""
                file_name = getattr(args[0], "FILE_NAME", None) if args else None

                # Build contextual prefix
                context = f"[{cls_name}.{func.__name__}]"
                if file_name:
                    context += f" ({file_name})"

                log_func = getattr(logger, level, logger.error)
                log_func(f"{context} {type(e).__name__}: {e}")
                logger.error(traceback.format_exc())
                return return_value
        return wrapper
    return decorator