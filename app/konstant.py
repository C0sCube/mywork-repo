
import json,json5,os

path_path = r"C:\Users\kaustubh.keny\Projects\OFFICE PROJECTS\mywork-repo\paths.json"

def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
    
def load_json5(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json5.load(f)

def create_dir(base_path, *folders):
    dir_path = os.path.join(base_path, *folders)
    os.makedirs(dir_path, exist_ok=True)
    return dir_path


def load_paths(): return load_json(path_path)
def get_output_path(): return load_paths()["output_path"]
def get_input_path(): return load_paths()["amc_path"]


def load_config(): return load_json5(load_paths()["configs"]["params"])

def load_regex(): return load_json5(load_paths()["configs"]["regex"])

def load_sidkimregex():
    return load_json5(
        load_paths()["configs"]["sid_regex"]
    )

def load_sidkimparams():
    return load_json5(
        load_paths()["configs"]["sid_params"]
    )

CHECK_INTERVAL = 10
PROGRAM_NAME = "FS_JSON_PARSE"
PAUSE = 5


# DB_CONFIG = {
#     "host": "172.22.225.155",
#     "user": "cog_ws_user",
#     "password": "cogstatic",
#     "database": "cog_ws_staging",
#     "port": 3306
# }

def load_db_config():
    f = load_paths()
    return f["db_config"]

#MAILS
def load_mail_data():
    f = load_paths()
    return f["mail_data"]



#pdf generation constants
TITLE_FONT_SIZE = 24
TITLE_POSITION = 72
TITLE_COLOR = (0, 0, 1)
DEFAULT_FONT_NAME = "helv"
DEFAULT_FONT_SIZE = 10
DEFAULT_FONT_COLOR = (0, 0, 0)  # black
LEFT_MARGIN = 32        # Left margin for alignment
MIN_LINE_SPACING = 2     # Extra space between lines
Y_SNAP_THRESHOLD = 3     # If two words are within 3 units, snap to same Y
