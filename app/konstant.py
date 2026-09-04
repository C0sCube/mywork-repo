
import json,json5,os, sys
from pathlib import Path

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(root_dir)

root_dir = Path(root_dir)
path_dir = str(root_dir / r"paths.json")
program_dir = str(root_dir)

from .utils import Helper
utils = Helper()

#global registry
def get_registry():
    base_path = os.path.join(program_dir,"config","0000","registry.json")
    if not os.path.exists(base_path):
        return {}
    return utils.load_json(base_path)

def save_registry(key:str, data):
    base_path = os.path.join(program_dir,"config","0000","registry.json")
    if not os.path.exists(base_path):
        return None
    
    registry = utils.load_json(base_path)
    if key not in registry:
        print(f"{key} not found in registry. Cannot Save.")
        return
    
    registry.update({
        key:data
    })
    
    utils.save_json(registry, base_path)
    
# factsheet conf
def get_config(year = "2025", id = ""):

    config_path = os.path.join(program_dir,"config",year, f"{id}_AMC.json5")    
    if not os.path.exists(config_path):
        return None
    return utils.load_json5(config_path)

def get_regex(year = "2025"):
    config_path = os.path.join(program_dir,"config", year, f"regex_{year}.json")
    if not os.path.exists(config_path):
        return None
    return utils.load_json(config_path)

#sid/kim conf
def get_sidkim_config(folder = "sidkim"):

    config_path = os.path.join(program_dir, "config", folder, f"sid_params.json5")
    if not os.path.exists(config_path):
        return None
    config =  utils.load_json5(config_path)
    return config

def load_sidkimregex():
    sid_path = os.path.join(program_dir,"config", "sidkim","sid_regex.json")
    return utils.load_json(sid_path)


def load_db_config():
    f = utils.load_json(path_dir)
    return f["db_config"]

def load_mail_data():
    f = utils.load_json(path_dir)
    return f["mail_data"]



INPUT_DIR = utils.create_dir(program_dir, "input")
OUTPUT_DIR = utils.create_dir(program_dir, "output")
PROCESSED_DIR = utils.create_dir(OUTPUT_DIR, "processed")
FAILED_DIR = utils.create_dir(OUTPUT_DIR, "failed")
JSON_DIR = utils.create_dir(OUTPUT_DIR, "json")
REPORT_DIR = utils.create_dir(OUTPUT_DIR, "reports")
LOG_DIR = utils.create_dir(OUTPUT_DIR, "logs")


def get_processed_dir(sub):
    return utils.create_dir(PROCESSED_DIR,sub)


#pdf generation constants
# TITLE_FONT_SIZE = 24
# TITLE_POSITION = 72
# TITLE_COLOR = (0, 0, 1)
# DEFAULT_FONT_NAME = "helv"
# DEFAULT_FONT_SIZE = 10
# DEFAULT_FONT_COLOR = (0, 0, 0)  # black
# LEFT_MARGIN = 32        # Left margin for alignment
# MIN_LINE_SPACING = 2     # Extra space between lines
# Y_SNAP_THRESHOLD = 3     # If two words are within 3 units, snap to same Y

#log data

FINAL_LOG_NAME = "fs_parse_log"
FINAL_WEB_LOG_NAME = "fs_web_log"