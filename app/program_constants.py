import os,json
from app.utils import Helper

config_path = "config\\parameters.json5"
regex_path = "config\\regex.json"

PATHS = Helper.load_json("paths.json")

OUTPUT_PATH = PATHS["output_path"]
INPUT_PATH = PATHS["amc_path"]

OUTPUT_FOLDERS = PATHS["output"]

CONFIG = Helper.load_json5(PATHS["configs"]["params"])
REGEX = Helper.load_json5(PATHS["configs"]["regex"])

CHECK_INTERVAL = 10
PROGRAM_NAME = "FS_JSON_PARSE"

# Output directories
JSON_DIR = Helper.create_dir(OUTPUT_PATH,"json")
LOG_DIR = Helper.create_dir(OUTPUT_PATH,"logs")
REPORT_DIR = Helper.create_dir(OUTPUT_PATH,"reports")
FAILED_DIR = Helper.create_dir(OUTPUT_PATH,"failed")
PROCESSED_DIR = Helper.create_dir(OUTPUT_PATH,"processed")
DUMMY_PDF_DIR = Helper.create_dir(OUTPUT_PATH,"dry")


#MAILS
MAIL_SENDER = PATHS["mail"]["sender"]
MAIL_RECEIVER = PATHS["mail"]["recipients"]
MAIL_SERVER = PATHS["mail"]["server"]
MAIL_PORT = PATHS["mail"]["port"]