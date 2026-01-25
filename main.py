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

from app.sqlconnect import (
    fetch_latest_uploaded_job,
    transition_job_state,
    JobState
)



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

def read_meta_content(root_dir, file_name):
    """
    Read sidecar meta JSON.
    Meta is for parser hints ONLY, never job state.
    """
    meta_path = os.path.join(
        root_dir,
        file_name.replace(".pdf", ".meta.json")
    )

    if not os.path.exists(meta_path):
        return {}

    try:
        with open(meta_path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as e:
        logger.warning(f"Failed to read meta for {file_name}: {e}")
        return {}


# --- Main Watcher Loop ---

def execute_parser(path, amc_id, year):
    file_name = os.path.basename(path)
    logger.info(f"Parsing: {file_name}")

    try:
        amc_registry = load_registry()
        if amc_id not in amc_registry:
            raise ValueError("Unknown AMC ID")

        config, regex = get_config(year, amc_id), get_regex(year)
        if not config or not regex:
            raise ValueError("Missing config or regex")

        obj = amc_registry[amc_id](config, regex, path)

        title, path_pdf = obj.check_and_highlight(path)
        if not title:
            raise ValueError("check_and_highlight failed")

        data = obj.get_data(path_pdf, title)
        extracted = obj.get_generated_content(data)
        refined = obj.refine_extracted_data(extracted)
        dfs = obj.merge_and_select_data(refined)

        if not dfs:
            raise ValueError("No parsed data")

        save_path = os.path.join(
            JSON_DIR,
            file_name.replace(".pdf", ".json")
        )
        Helper.save_json(dfs, save_path)

        return {"json_path": save_path}

    except Exception as e:
        logger.error(f"[PARSE ERROR] {file_name}: {e}")
        logger.debug(traceback.format_exc())
        return {"error": f"{type(e).__name__}: {e}"}

def process_file(file_name, db_config):
    file_path = os.path.join(INPUT_DIR, file_name)

    # 1. Find latest UPLOADED job
    job = fetch_latest_uploaded_job(file_name, db_config)
    if not job:
        logger.warning(f"No UPLOADED job found for {file_name}")
        return

    job_id = job["id"]

    # 2. Identify AMC + year
    file_key, year = check_amc_file(file_path, file_name)

    # 3. Parse
    result = execute_parser(file_path, file_key, year)

    # 4. Transition state
    if "json_path" in result:
        transition_job_state(
            job_id=job_id,
            from_state=JobState.UPLOADED,
            to_state=JobState.PARSED,
            json_path=result["json_path"],
            db_config=db_config
        )

        archive_dir = (
            PRS_FS_DIR if file_name.endswith("_FS.pdf")
            else PRS_SID_DIR if file_name.endswith("_SID.pdf")
            else PRS_KIM_DIR if file_name.endswith("_KIM.pdf")
            else PROCESSED_DIR
        )

        logger.info(f"[PARSED] {file_name}")

    else:
        transition_job_state(
            job_id=job_id,
            from_state=JobState.UPLOADED,
            to_state=JobState.PARSE_FAILED,
            error=result["error"],
            db_config=db_config
        )

        archive_dir = FAILED_DIR
        logger.error(f"[FAILED] {file_name}")

    # 5. Archive PDF
    Helper.archive_and_delete_files(
        archive_dir,
        {file_name: file_path}
    )

    # 6. Cleanup meta file
    meta_path = os.path.join(
        INPUT_DIR,
        file_name.replace(".pdf", ".meta.json")
    )
    if os.path.exists(meta_path):
        os.remove(meta_path)

def main():
    logger.info("Watcher started.")

    while True:
        try:
            new_files = detect_input_pdf()

            if not new_files:
                time.sleep(CHECK_INTERVAL)
                rotate_daily_log(logger)
                continue

            logger.info(f"Files detected: {', '.join(new_files)}")
            time.sleep(PAUSE)

            db_config = load_db_config()

            for file_name in new_files:
                process_file(file_name, db_config)
                time.sleep(1)

            logger.save(f"Processed: {', '.join(new_files)}")

        except KeyboardInterrupt:
            logger.warning("Watcher stopped.")
            break

        except Exception as e:
            logger.critical(f"Unhandled error: {e}")
            logger.debug(traceback.format_exc())
            time.sleep(5)


# --- Entry Point ---
if __name__ == "__main__":
    
    #timezone
    TIME_ZONE = ZoneInfo("Asia/Kolkata")

    # dir
    OUTPUT_DIR = get_output_path()
    INPUT_DIR = get_input_path()
    JSON_DIR = create_dir(OUTPUT_DIR, "json")
    LOG_DIR = create_dir(OUTPUT_DIR, "logs")
    PROCESSED_DIR = create_dir(OUTPUT_DIR, "processed")
    PRS_FS_DIR = create_dir(PROCESSED_DIR,"fs")
    PRS_SID_DIR = create_dir(PROCESSED_DIR,"sid")
    PRS_KIM_DIR = create_dir(PROCESSED_DIR,"kim")
    FAILED_DIR = create_dir(OUTPUT_DIR, "failed")
    
    #log
    logger = setup_logger("watcher", base_dir=LOG_DIR, log_level=12, set_global=True)
    helper = Helper()
    
    #sp call
    SP_STATUS = False
        
    logger.info("Running FactSheet Parser (watcher)")
    main()



# UPLOAD PDF
#   ↓
# PARSE → JSON + CSV
#   ↓
# ANALYST DOWNLOADS CSV
#   ↓
# ANALYST EDITS CSV (locally or in UI)
#   ↓
# UPLOAD CSV → APPLY TO JSON
#   ↓
# OLD JSON → BACKUP
# NEW JSON → ACTIVE
#   ↓
# SLIDER CONFIRMATION
#   ↓
# PUSH JSON TO ADMIN PANEL
