import os
from core.config_manager import ConfigManager

config_mgr = ConfigManager()

PATHS = config_mgr.load("paths.json")
INPUT_PATH = PATHS["amc_path"]
OUTPUT_PATH = PATHS["output_path"]

JSON_DIR = os.path.join(OUTPUT_PATH, "json")
LOG_DIR = os.path.join(OUTPUT_PATH, "logs")
REPORT_DIR = os.path.join(OUTPUT_PATH, "reports")
FAILED_DIR = os.path.join(OUTPUT_PATH, "failed")
PROCESSED_DIR = os.path.join(OUTPUT_PATH, "processed")

# PDF generation constants
TITLE_FONT_SIZE = 24
TITLE_POSITION = 72
TITLE_COLOR = (0, 0, 1)
DEFAULT_FONT_NAME = "helv"
DEFAULT_FONT_SIZE = 10
DEFAULT_FONT_COLOR = (0, 0, 0)
LEFT_MARGIN = 32
MIN_LINE_SPACING = 2
Y_SNAP_THRESHOLD = 3
