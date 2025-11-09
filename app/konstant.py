
import json,json5,os


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


PATHS = load_json("paths.json")

OUTPUT_PATH = PATHS["output_path"]
INPUT_PATH = PATHS["amc_path"]

CONFIG = load_json5(PATHS["configs"]["params"])
REGEX = load_json5(PATHS["configs"]["regex"])


def load_config():
    return load_json5(
        PATHS["configs"]["params"]
    )

def load_regex():
    return load_json5(
        PATHS["configs"]["regex"]
    )

SIDKIM_REGEX = load_json5(PATHS["configs"]["sid_regex"])
SIDKIM_CONFIG = load_json5(PATHS["configs"]["sid_params"])

def load_sidkimregex():
    return load_json5(
        PATHS["configs"]["sid_regex"]
    )

def load_sidkimparams():
    return load_json5(
        PATHS["configs"]["sid_params"]
    )

CHECK_INTERVAL = 10
PROGRAM_NAME = "FS_JSON_PARSE"
PAUSE_AFTER_FILE_DETECTION = 30

# Output directories
JSON_DIR = create_dir(OUTPUT_PATH,"json")
LOG_DIR = create_dir(OUTPUT_PATH,"logs")
REPORT_DIR = create_dir(OUTPUT_PATH,"reports")
FAILED_DIR = create_dir(OUTPUT_PATH,"failed")
PROCESSED_DIR = create_dir(OUTPUT_PATH,"processed")
DUMMY_PDF_DIR = create_dir("app","temp")


#MAILS
MAIL_CONFIG = PATHS["mail"]
MAIL_SENDER = PATHS["mail"]["sender"]
MAIL_RECEIVER = PATHS["mail"]["recipients"]
MAIL_SERVER = PATHS["mail"]["server"]
MAIL_PORT = PATHS["mail"]["port"]




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
