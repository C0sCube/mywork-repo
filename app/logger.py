import logging, os, sys
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

def _get_formatter(use_color=False):
    if use_color and COLORLOG_AVAILABLE:
        return colorlog.ColoredFormatter(
            "%(log_color)s" + DEFAULT_FORMAT,
            datefmt=DATE_FORMAT,
            log_colors=LOG_COLORS
        )
    return logging.Formatter(DEFAULT_FORMAT, datefmt=DATE_FORMAT)

def _add_console_handler(logger, use_color=True): #level set to TRACE =15
    handler = colorlog.StreamHandler(sys.stdout) if use_color and COLORLOG_AVAILABLE else logging.StreamHandler(sys.stdout)
    handler.setFormatter(_get_formatter(use_color))
    handler.setLevel(15)
    logger.addHandler(handler)


# --- Forever Logger ---
def create_logger(name="watcher",log_dir="logs/daily",max_bytes=2 * 1024 * 1024,backup_count=5,log_level=logging.INFO,to_console=True,use_color=True,redirect_stdout=False):


    logger = logging.getLogger(name)
    if logger.hasHandlers():
        return logger
    logger.setLevel(log_level)
    logger.propagate = False

    log_file = os.path.join(log_dir, f"{name}.log")
    file_handler = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count, encoding='utf-8')
    file_handler.setFormatter(_get_formatter(use_color=False))
    logger.addHandler(file_handler)

    if to_console:
        _add_console_handler(logger, use_color)
    
    if redirect_stdout:
        redirect_stdout_to_logger(logger)

    return logger


# --- Global Logger Registry ---
_active_logger = None

def set_global_logger(logger):
    global _active_logger
    _active_logger = logger

def get_global_logger():
    return _active_logger or logging.getLogger("default_logger")
