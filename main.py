import os
import time
import json
import traceback
from datetime import datetime
from zoneinfo import ZoneInfo

from app.konstant import (
    get_input_path, get_output_path, create_dir,
    load_db_config,get_config, get_regex,
    get_processed_dir, get_failed_dir,
    get_json_dir, get_log_dir, FINAL_LOG_NAME
)

from app.logger import setup_logger, rotate_daily_log
from app.utils import Helper
from app.amc.registry import load_registry,check_amc_file
from app.sidkim.registry import load_sidkim_registry
from app.sqlconnect import (
    fetch_latest_uploaded_job,
    transition_job_state,
    get_job_states
)

# --------------------------------------------------
# Helpers
# --------------------------------------------------
def read_meta(root_dir, file_name):
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
    
# --------------------------------------------------
# FS PARSER
# --------------------------------------------------
def execute_fs(path, amc_id, year):
    file_name = os.path.basename(path)
    logger.info(f"Parsing FS: {file_name}")

    try:
        registry = load_registry()
        if amc_id not in registry:
            raise ValueError("Unknown AMC ID")

        config = get_config(year, amc_id)
        regex = get_regex(year)

        obj = registry[amc_id](config, regex, path)

        title, path_pdf = obj.check_and_highlight(path, save_report=True) #False ??
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
        logger.error(f"[FS ERROR] {file_name}: {e}")
        logger.debug(traceback.format_exc())
        return {"error": str(e)}
    
# --------------------------------------------------
# SID / KIM PARSER
# --------------------------------------------------
def execute_sidkim(path, amc_id, sid_or_kim):
    file_name = os.path.basename(path)
    logger.info(f"Parsing {sid_or_kim}: {file_name}")

    try:
        registry = load_sidkim_registry()
        if amc_id not in registry:
            raise ValueError("Unknown AMC ID")

        meta = read_meta(INPUT_DIR, file_name)   
        obj = registry[amc_id](amc_id, path)

        temp = {}
        if sid_or_kim == "SID":
            temp.update(obj.parse_page_zero(meta.get("front_page", "")))
            temp.update(obj.parse_scheme_table_data(meta.get("data_page", "")))
            temp.update(obj.parse_fund_manager_info(meta.get("manager_page", "")))

        else:  # KIM
            temp = obj.parse_KIM_data(
                pages=meta.get("instr_page", ""),
                instrument_count=meta.get("instr_count", "")
            )

        data = obj.refine_data(temp)
        dfs = obj.merge_and_select_data(data=data, sid_or_kim=sid_or_kim)

        if not dfs:
            raise ValueError("No parsed data")

        save_path = os.path.join(
            JSON_DIR,
            file_name.replace(".pdf", ".json")
        )

        Helper.save_json(dfs, save_path)
        return {"json_path": save_path}

    except Exception as e:
        logger.error(f"[SID/KIM ERROR] {file_name}: {e}")
        logger.debug(traceback.format_exc())
        return {"error": str(e)}

# --------------------------------------------------
# PROCESS FILE
# --------------------------------------------------

def process_file(file_name, db_config):
    file_path = os.path.join(INPUT_DIR, file_name)
    meta_path = file_path.replace(".pdf", ".meta.json")
    archive_dir = FAILED_DIR  # default
    JobState = get_job_states()

    job = fetch_latest_uploaded_job(file_name, db_config)
    if not job:
        logger.warning(f"Illegal Upload. No UPLOADED job found: {file_name}")

        Helper.archive_and_delete_files(archive_dir,{file_name: file_path})
        os.path.exists(meta_path) and os.remove(meta_path)
        return

    job_id = job["id"]
    logger.notice(f"START job={job_id} file={file_name}")

    amc_code, tag, file_type = check_amc_file(file_path, file_name)

    if not file_type:
        logger.warning("File neither FS nor SID/KIM. Aborting.")
        
        transition_job_state(
            job_id,
            JobState.UPLOADED,
            JobState.INVALID_TYPE,
            error="Unsupported file type",
            db_config=db_config
        )

        Helper.archive_and_delete_files( archive_dir,{file_name: file_path})
        os.path.exists(meta_path) and os.remove(meta_path)
        return

    # ---------- Parse ----------
    if file_type == "FS":
        result = execute_fs(file_path, amc_code, tag)
    else:  # SID / KIM
        result = execute_sidkim(file_path, amc_code, tag)

    # ---------- State transition ----------
    if "json_path" in result:
        transition_job_state(
            job_id,
            JobState.UPLOADED,
            JobState.PARSED,
            json_path=result["json_path"],
            db_config=db_config
        )

        archive_dir = (
            FST_DIR if file_name.endswith("_FS.pdf")
            else SID_DIR if file_name.endswith("_SID.pdf")
            else KIM_DIR
        )
    else:
        transition_job_state(
            job_id,
            JobState.UPLOADED,
            JobState.PARSE_FAILED,
            error=result.get("error", "Unknown parse error"),
            db_config=db_config
        )

    # ---------- Archive + Cleanup ----------
    Helper.archive_and_delete_files( archive_dir, {file_name: file_path})
    os.path.exists(meta_path) and os.remove(meta_path)
    logger.notice(f"END job={job_id}")

# --------------------------------------------------
# MAIN LOOP
# --------------------------------------------------

def main():
   
    while True:
        try:
            files = [ f for f in os.listdir(INPUT_DIR) if f.lower().endswith(".pdf") ]

            if not files:
                time.sleep(CHECK_INTERVAL)
                continue

            db_config = load_db_config()
            rotate_daily_log(logger)
            
            processed = []
            for f in files:
                process_file(f, db_config)
                processed.append(f)
                time.sleep(1)

            logger.save(f"Processed File(s): {processed}")

        except KeyboardInterrupt:
            logger.warning("Watcher stopped")
            break

        except Exception as e:
            logger.critical(f"Unhandled error: {e}")
            logger.debug(traceback.format_exc())
            time.sleep(5)

# --------------------------------------------------
# ENTRY
# --------------------------------------------------

if __name__ == "__main__":
    TIME_ZONE = ZoneInfo("Asia/Kolkata")

    OUTPUT_DIR = get_output_path()
    INPUT_DIR = get_input_path()
    CHECK_INTERVAL = 20

    JSON_DIR = get_json_dir()
    LOG_DIR = get_log_dir()
    
    FST_DIR = get_processed_dir("fs")
    SID_DIR = get_processed_dir("sid")
    KIM_DIR = get_processed_dir("kim")
    FAILED_DIR = get_failed_dir()
    

    logger = setup_logger(FINAL_LOG_NAME, base_dir=LOG_DIR, log_level=12, set_global=True)

    logger.info("Running FactSheet / SID / KIM Watcher")
    main()
