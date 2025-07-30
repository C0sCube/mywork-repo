import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler

# --- Stdout Redirection ---
ORIGINAL_STDOUT = sys.stdout
ORIGINAL_STDERR = sys.stderr

class StreamToLogger:
    def __init__(self, logger, level):
        self.logger = logger
        self.level = level

    def write(self, buf):
        for line in buf.rstrip().splitlines():
            self.logger.log(self.level, line.rstrip())

    def flush(self):
        pass

def redirect_stdout_to_logger(logger):
    sys.stdout = StreamToLogger(logger, logging.INFO)
    sys.stderr = StreamToLogger(logger, logging.ERROR)

def restore_stdout():
    sys.stdout = ORIGINAL_STDOUT
    sys.stderr = ORIGINAL_STDERR


# --- Optional ColorLog Support ---
try:
    import colorlog
    COLORLOG_AVAILABLE = True
except ImportError:
    COLORLOG_AVAILABLE = False

# --- Custom Log Levels ---
TRACE_LEVEL_NUM = 15
SAVE_LEVEL_NUM = 22
NOTICE_LEVEL_NUM = 35

logging.addLevelName(TRACE_LEVEL_NUM, "TRACE")
logging.addLevelName(SAVE_LEVEL_NUM, "SAVE")
logging.addLevelName(NOTICE_LEVEL_NUM, "NOTICE")

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

# --- Shared Formatters and Colors ---
DEFAULT_FORMAT = "%(asctime)s [%(levelname)s]: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_COLORS = {
    'TRACE': 'white',
    'SAVE': 'blue',
    'NOTICE': 'bold_cyan',
    'DEBUG': 'cyan',
    'INFO': 'green',
    'WARNING': 'yellow',
    'ERROR': 'red',
    'CRITICAL': 'bold_red',
}

def _get_formatter(use_color=False):
    if use_color and COLORLOG_AVAILABLE:
        return colorlog.ColoredFormatter(
            "%(log_color)s" + DEFAULT_FORMAT,
            datefmt=DATE_FORMAT,
            log_colors=LOG_COLORS
        )
    return logging.Formatter(DEFAULT_FORMAT, datefmt=DATE_FORMAT)

def _add_console_handler(logger, level, use_color=True):
    handler = colorlog.StreamHandler(sys.stdout) if use_color and COLORLOG_AVAILABLE else logging.StreamHandler(sys.stdout)
    handler.setFormatter(_get_formatter(use_color))
    handler.setLevel(level)
    logger.addHandler(handler)

# --- Generic Logger Setup ---
def setup_logger(
    name="app_logger",
    log_dir="logs",
    log_level=logging.DEBUG,
    to_console=True,
    to_file=True,
    use_color=True,
    redirect_stdout=False
):
    os.makedirs(log_dir, exist_ok=True)
    logger = logging.getLogger(name)
    if logger.hasHandlers():
        return logger
    logger.setLevel(log_level)
    logger.propagate = False

    if to_file:
        today = datetime.now().strftime('%Y-%m-%d')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        folder_path = os.path.join(log_dir,today)
        os.makedirs(folder_path, exist_ok=True)
        file_path = os.path.join(folder_path,f"{name}_{timestamp}.log")
        file_handler = logging.FileHandler(file_path, encoding='utf-8')
        file_handler.setFormatter(_get_formatter(use_color=False))
        file_handler.setLevel(TRACE_LEVEL_NUM)
        logger.addHandler(file_handler)

    if to_console:
        _add_console_handler(logger, log_level, use_color)
        
    if redirect_stdout:
        redirect_stdout_to_logger(logger)


    return logger

# --- Forever Logger ---
def get_forever_logger(
    name="watcher",
    log_dir="logs/daily",
    max_bytes=2 * 1024 * 1024,
    backup_count=5,
    log_level=logging.INFO,
    to_console=True,
    use_color=True,
    redirect_stdout=False
):
    today = datetime.now().strftime('%Y-%m-%d')
    folder_path = os.path.join(log_dir, today)
    os.makedirs(folder_path, exist_ok=True)

    logger = logging.getLogger(name)
    if logger.hasHandlers():
        return logger
    logger.setLevel(log_level)
    logger.propagate = False

    log_file = os.path.join(folder_path, f"{name}.log")
    file_handler = RotatingFileHandler(
        log_file, maxBytes=max_bytes, backupCount=backup_count, encoding='utf-8'
    )
    file_handler.setFormatter(_get_formatter(use_color=False))
    logger.addHandler(file_handler)

    if to_console:
        _add_console_handler(logger, log_level, use_color)
    
    if redirect_stdout:
        redirect_stdout_to_logger(logger)

    return logger

# --- Session Logger ---
def setup_session_logger(
    folder_name: str,
    base_log_dir: str = "logs/sessions",
    log_level: int = logging.DEBUG,
    to_console: bool = True,
    use_color: bool = True,
    redirect_stdout=False
):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    os.makedirs(base_log_dir, exist_ok=True)

    log_filename = f"fs_{folder_name}_{timestamp}.log"
    today = datetime.now().strftime('%Y-%m-%d')
    log_path = os.path.join(base_log_dir,today)
    os.makedirs(log_path, exist_ok=True)
    log_path = os.path.join(log_path,log_filename)
    logger = logging.getLogger(f"session_{folder_name}_{timestamp}")

    if logger.hasHandlers():
        return logger

    logger.setLevel(log_level)
    formatter = logging.Formatter(DEFAULT_FORMAT, datefmt=DATE_FORMAT)

    file_handler = logging.FileHandler(log_path, encoding='utf-8')
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    if to_console:
        if use_color and COLORLOG_AVAILABLE:
            color_formatter = colorlog.ColoredFormatter(
                "%(log_color)s" + DEFAULT_FORMAT,
                datefmt=DATE_FORMAT,
                log_colors= LOG_COLORS
            )
            console_handler = colorlog.StreamHandler(stream=sys.stdout)
            console_handler.setFormatter(color_formatter)
        else:
            console_handler = logging.StreamHandler(stream=sys.stdout)
            console_handler.setFormatter(formatter)

        console_handler.setLevel(log_level)
        logger.addHandler(console_handler)
    
    if redirect_stdout:
        redirect_stdout_to_logger(logger)

    return logger

# --- Global Logger Registry ---
_active_logger = None

def set_active_logger(logger):
    global _active_logger
    _active_logger = logger

def get_active_logger():
    return _active_logger or logging.getLogger("default_logger")
