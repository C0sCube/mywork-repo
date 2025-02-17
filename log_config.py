import logging
import os
from datetime import datetime


os.makedirs('logs', exist_ok=True)

log_filename = datetime.now().strftime("log_%Y_%m_%d.log")
log_path = os.path.join(os.getcwd(),'logs')

logging.basicConfig(
    level=logging.INFO,  # Change to DEBUG or ERROR as needed
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(log_path,log_filename)) 
    ]
)