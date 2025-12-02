import os
import time
import traceback
import json
from datetime import datetime
from zoneinfo import ZoneInfo

from app.konstant import (
    get_input_path, get_output_path, create_dir,
    load_db_config, get_config, get_regex,
    CHECK_INTERVAL, PAUSE
)
from app.logger import setup_logger, rotate_daily_log
from app.utils import Helper
from app.amc.registry import load_registry, check_amc_file
from app.sqlconnect import update_report_table, json_to_cog_db

#timezone
TIME_ZONE = ZoneInfo("Asia/Kolkata")

# dir
OUTPUT_DIR = get_output_path()
INPUT_DIR = get_input_path()
JSON_DIR = create_dir(OUTPUT_DIR, "json")
LOG_DIR = create_dir(OUTPUT_DIR, "logs")
PROCESSED_DIR = create_dir(OUTPUT_DIR, "processed")
FAILED_DIR = create_dir(OUTPUT_DIR, "failed")

#log
logger = setup_logger("watcher", base_dir=LOG_DIR, log_level=12, set_global=True)
helper = Helper()


#sp call
SP_COG_MF = False
SP_STATUS = True

# --- Helper Functions ---
def detect_input_pdf():
    """Return list of valid pdf filenames currently in INPUT_DIR."""
    try:
        files = [
            f for f in os.listdir(INPUT_DIR)
            if os.path.isfile(os.path.join(INPUT_DIR, f)) and f.endswith("_FS.pdf")
        ]
        return sorted(files)
    except FileNotFoundError:
        os.makedirs(INPUT_DIR, exist_ok=True)
        return []
    except Exception as e:
        logger.error(f"Error listing input dir: {e}")
        return []

def read_meta_content(root_dir,file_name):
    """Read sidecar meta JSON (if present) and return dict."""
    file_name = file_name.replace(".pdf", ".meta.json")
    meta_path = os.path.join(root_dir, file_name)
    # print(meta_path)
    if not os.path.exists(meta_path):
        logger.warning("meta file doesnt exist.")
        return {}
    
    try:
        with open(meta_path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as e:
        logger.warning(f"Failed to read meta for {file_name}: {e}")
    return {}

def initialize_status_report(db_config:dict,file_list):
    reports = {}
    for file_name in file_list:
        meta = read_meta_content(INPUT_DIR,file_name)
        uploaded_by = meta.get("uploaded_by","unknown")
        # print(uploaded_by)
        report = {
            "start_time": datetime.now(TIME_ZONE).strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": None,
            "file_name": file_name,
            "json_path": None,
            "status": "Pending",
            "error": None,
            "uploaded_by": uploaded_by
        }
        reports[file_name] = report
       
        update_report_table(report, db_config=db_config)
    return reports

def update_status_report(report, status, json_path=None, error=None):
    report.update({
        "end_time": datetime.now(TIME_ZONE).strftime("%Y-%m-%d %H:%M:%S"),
        "json_path": json_path,
        "status": status,
        "error": error
    })
    return report


# --- Main Watcher Loop ---
def execute_parser(path, amc_id, year, report):
    file_name = os.path.basename(path)
    logger.info(f"Process {amc_id}: {file_name}")

    try:
        
        amc_registry = load_registry()
        if amc_id not in amc_registry:
            raise ValueError("Unknown AMC ID or File.")

        logger.info(f"Fetchin CONFIG: {amc_id} - {year}")
        config,regex = get_config(year, amc_id),get_regex(year)
        
        if not config or not regex:
            raise ValueError(f"CONFIG,REGEX missing: {amc_id}")
        
        obj = amc_registry[amc_id](config, regex, path)
        title, path_pdf = obj.check_and_highlight(path)
        if not (title and path_pdf):
            raise ValueError("check_and_highlight failed.")

        data = obj.get_data(path_pdf, title)
        extracted_text = obj.get_generated_content(data)
        final_text = obj.refine_extracted_data(extracted_text)
        dfs = obj.merge_and_select_data(final_text)
        if not dfs:
            raise ValueError("No final Data.")
        
        #save
        save_path = os.path.join(JSON_DIR, file_name.replace(".pdf", ".json"))
        Helper.save_json(dfs, save_path)
        logger.info(f"Saved JSON File: {save_path}")

        return update_status_report(report, "completed", json_path=save_path)

    except Exception as e:
        logger.error(f"[Pipeline Error] {file_name} | {type(e).__name__}: {e}")
        logger.debug(traceback.format_exc())
        return update_status_report(report, "failed", error=f"{type(e).__name__}: {e}")
        
def process_file(file_name, db_config, report):
    file_path = os.path.join(INPUT_DIR, file_name)
    file_key, year = check_amc_file(file_path,file_name)

    report = execute_parser(file_path, file_key, year, report)
    
    if SP_STATUS:
        update_report_table(report, db_config)

    # archive + delete
    archive_dir = PROCESSED_DIR if report["status"] == "completed" else FAILED_DIR
    Helper.archive_and_delete_files(archive_dir, {file_name: file_path})

    meta_file_name = file_name.replace(".pdf", ".meta.json")
    meta_src = os.path.join(INPUT_DIR, meta_file_name)
    if os.path.exists(meta_src):
        try:
            os.remove(meta_src)
        except Exception:
            logger.warning("Meta file not removed")

    # upload to cog_mf if enabled
    if report["status"] == "completed" and report["json_path"] and SP_COG_MF:
        try:
            json_to_cog_db(report["json_path"], db_config)
        except Exception as e:
            logger.error(f"db update failed for {file_name}: {type(e).__name__}: {e}")
            logger.debug(traceback.format_exc())

    # update status report if enabled
    if SP_STATUS:
        update_report_table(report, db_config)

    return report["status"]

def main():
    logger.info("Watcher started.")
    while True:
        try:
            new_files = detect_input_pdf()

            if not new_files:
                # logger.notice("No new files. Sleeping...")
                time.sleep(CHECK_INTERVAL)
                rotate_daily_log(logger)
                continue
            
            logger.info(f"Files Detected: {'|'.join(sorted(new_files))}")
            logger.notice("Mandatory pause for file save.")
            time.sleep(PAUSE)        

            db_config = load_db_config()
            status_reports = initialize_status_report(db_config,new_files)

            for file_name in new_files:
                report = status_reports[file_name]
                process_file(file_name,db_config, report)
                time.sleep(1)

            logger.save(f"[{', '.join(new_files)}] processed/attempted.")

        except KeyboardInterrupt:
            logger.warning("Watcher stopped by user. Exiting gracefully.")
            break
        except Exception as e:
            logger.critical(f"Unhandled error: {type(e).__name__}: {e}")
            logger.debug(traceback.format_exc())
            time.sleep(5)

# --- Entry Point ---
if __name__ == "__main__":
    logger.info("Running FactSheet Parser (watcher)")
    main()
