import logging, os, sys
from datetime import datetime
import colorlog

# --- Custom Log Levels ---
TRACE_LEVEL_NUM = 5
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
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    try:
        color_formatter = colorlog.ColoredFormatter(
            "%(log_color)s%(asctime)s [%(levelname)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold_red",
                "TRACE": "white",
                "SAVE": "blue",
                "NOTICE": "bold_cyan"
            }
        )
        console_handler = colorlog.StreamHandler(sys.stdout)
        console_handler.setFormatter(color_formatter)
    except:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(file_formatter)

    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)

    LOGGER = logger
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

def get_logger():
    return LOGGER