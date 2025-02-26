# logger_config.py
import logging
import os
from logging.handlers import TimedRotatingFileHandler
from IPython.core.interactiveshell import InteractiveShell #type:ignore
 
os.makedirs("logs", exist_ok=True)


logger = logging.getLogger()
if not logger.hasHandlers():  # Prevent adding duplicate handlers
    logger.setLevel(logging.INFO)
    
    log_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    log_handler = TimedRotatingFileHandler(
        "logs/runtime.log", when="midnight", interval=1, backupCount=7, encoding="utf-8"
    )
    log_handler.setLevel(logging.INFO)
    log_handler.setFormatter(log_formatter)
    
    logger.addHandler(log_handler)

    # Console Handler (Only Show Warnings and Above)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))
    logger.addHandler(console_handler)

# Jupyter Notebook Exception Handler
def notebook_exception_handler(shell, exc_type, exc_value, traceback_obj, tb_offset=None):
    # Log the error
    logger.error("Uncaught Exception", exc_info=(exc_type, exc_value, traceback_obj))
    
    # Call the default exception handler to display the traceback in the notebook
    shell.showtraceback(exc_tuple=(exc_type, exc_value, traceback_obj), tb_offset=tb_offset)

# Set the Jupyter exception handler
InteractiveShell.instance().set_custom_exc((Exception,), notebook_exception_handler)
