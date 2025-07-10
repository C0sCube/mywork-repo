import logging, os, sys
from datetime import datetime
import colorlog

# --- Custom Log Levels ---
#DEBUG lowest 10
TRACE_LEVEL_NUM = 15
SAVE_LEVEL_NUM = 22
NOTICE_LEVEL_NUM = 25
LOGGER = None

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

# --- Logger Setup ---
def setup_logger(log_dir, logger_name="fs_logger", folder_name=None):
    os.makedirs(log_dir, exist_ok=True)

    global LOGGER

    if folder_name:
        file_name = f"{folder_name}_log_{datetime.now().strftime('%Y%m%d_%H%M')}.log"
    else:
        file_name = f"{logger_name}_log_{datetime.now().strftime('%Y%m%d_%H%M')}.log"

    log_path = os.path.join(log_dir, file_name)
    logger = logging.getLogger(logger_name)

    if logger.hasHandlers():
        return logger

    logger.setLevel(logging.DEBUG)

    file_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s]: %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler = logging.FileHandler(log_path, encoding='utf-8')
    file_handler.setLevel(TRACE_LEVEL_NUM)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    try:
        color_formatter = colorlog.ColoredFormatter(
            "%(log_color)s%(asctime)s [%(levelname)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            log_colors={
                "TRACE": "white",          
                "SAVE": "blue",
                "NOTICE": "bold_cyan",
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold_red",
            }
        )
        console_handler = colorlog.StreamHandler(sys.stdout)
        console_handler.setFormatter(color_formatter)
    except:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(file_formatter)

    console_handler.addFilter(NoTracebackFilter())
    console_handler.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)

    LOGGER = logger
    return logger

def setup_simple_stdout_logger():
    logger = logging.getLogger("default_stdout_logger")
    if logger.hasHandlers():
        return logger

    logger.setLevel(logging.DEBUG)
    stream_handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s [%(levelname)s]: %(message)s',
                                  datefmt='%Y-%m-%d %H:%M:%S')
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    return logger



def cleanup_logger(logger):
    handlers = logger.handlers[:]
    for handler in handlers:
        try:
            handler.flush()
            if hasattr(handler, 'stream') and hasattr(handler.stream, 'flush'):
                handler.stream.flush()
            handler.close()
        except Exception as e:
            print(f"[LOGGER CLEANUP ERROR] {e}")
        logger.removeHandler(handler)

    logging.shutdown()

def get_logger(default_to_stdout=True):
    global LOGGER
    if LOGGER is not None:
        return LOGGER
    if default_to_stdout:
        return setup_simple_stdout_logger()
    raise RuntimeError("Logger not initialized. Call setup_logger() or enable fallback.")



class NoTracebackFilter(logging.Filter):
    def filter(self, record):
        record.exc_info = None
        return True



class StreamToLogger:
    def __init__(self, logger, level=logging.ERROR):
        self.logger = logger
        self.level = level
        self.buffer = ''

    def write(self, message):
        message = message.strip()
        if message:
            self.logger.log(self.level, message)

    def flush(self):
        pass  # Needed for file-like compatibility