import os
import time
import json
import traceback
from datetime import datetime
from zoneinfo import ZoneInfo

from app.konstant import (
    get_input_path, get_output_path, create_dir,
    load_db_config,
    get_config, get_regex,
    get_sidkim_config,
    CHECK_INTERVAL, PAUSE
)

from app.logger import setup_logger, rotate_daily_log
from app.utils import Helper
from app.amc.registry import (
    load_registry,
    load_sidkim_registry,
    check_amc_file
)

from app.sqlconnect import (
    fetch_latest_uploaded_job,
    transition_job_state,
    JobState
)

# --------------------------------------------------
# Helpers
# --------------------------------------------------

def detect_input_pdf():
    try:
        return sorted([
            f for f in os.listdir(INPUT_DIR)
            if os.path.isfile(os.path.join(INPUT_DIR, f))
            and (f.endswith("_FS.pdf") or f.endswith("_SID.pdf") or f.endswith("_KIM.pdf"))
        ])
    except FileNotFoundError:
        os.makedirs(INPUT_DIR, exist_ok=True)
        return []


def read_meta_content(root_dir, file_name):
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

def execute_fs_parser(path, amc_id, year):
    file_name = os.path.basename(path)
    logger.info(f"Parsing FS: {file_name}")

    try:
        registry = load_registry()
        if amc_id not in registry:
            raise ValueError("Unknown AMC ID")

        config = get_config(year, amc_id)
        regex = get_regex(year)

        obj = registry[amc_id](config, regex, path)

        title, path_pdf = obj.check_and_highlight(path)
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

def execute_sidkim_parser(path, amc_id, sid_or_kim):
    file_name = os.path.basename(path)
    logger.info(f"Parsing {sid_or_kim}: {file_name}")

    try:
        registry = load_sidkim_registry()
        if amc_id not in registry:
            raise ValueError("Unknown AMC ID")

        meta = read_meta_content(INPUT_DIR, file_name)
        config = get_sidkim_config(amc_id)

        obj = registry[amc_id](config, path)

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

    job = fetch_latest_uploaded_job(file_name, db_config)
    if not job:
        logger.warning(f"No UPLOADED job found for {file_name}")
        return

    job_id = job["id"]

    amc_code, tag, file_type = check_amc_file(file_path, file_name)

    if not file_type:
        return

    if file_type == "FS":
        result = execute_fs_parser(file_path, amc_code, tag)

    else:  # SIDKIM
        result = execute_sidkim_parser(file_path, amc_code, tag)

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
            PRS_FS_DIR if file_name.endswith("_FS.pdf")
            else PRS_SID_DIR if file_name.endswith("_SID.pdf")
            else PRS_KIM_DIR
        )

    else:
        transition_job_state(
            job_id,
            JobState.UPLOADED,
            JobState.PARSE_FAILED,
            error=result["error"],
            db_config=db_config
        )

        archive_dir = FAILED_DIR

    # ---------- Archive ----------
    Helper.archive_and_delete_files(
        archive_dir,
        {file_name: file_path}
    )

    # ---------- Cleanup meta ----------
    meta_path = file_path.replace(".pdf", ".meta.json")
    if os.path.exists(meta_path):
        os.remove(meta_path)

# --------------------------------------------------
# MAIN LOOP
# --------------------------------------------------

def main():
    logger.info("Watcher started")

    while True:
        try:
            files = detect_input_pdf()

            if not files:
                time.sleep(CHECK_INTERVAL)
                rotate_daily_log(logger)
                continue

            db_config = load_db_config()

            for f in files:
                process_file(f, db_config)
                time.sleep(1)

            logger.save(f"Processed: {', '.join(files)}")

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

    JSON_DIR = create_dir(OUTPUT_DIR, "json")
    LOG_DIR = create_dir(OUTPUT_DIR, "logs")
    PROCESSED_DIR = create_dir(OUTPUT_DIR, "processed")

    PRS_FS_DIR = create_dir(PROCESSED_DIR, "fs")
    PRS_SID_DIR = create_dir(PROCESSED_DIR, "sid")
    PRS_KIM_DIR = create_dir(PROCESSED_DIR, "kim")
    FAILED_DIR = create_dir(OUTPUT_DIR, "failed")

    logger = setup_logger("watcher", base_dir=LOG_DIR, log_level=12, set_global=True)

    logger.info("Running FactSheet / SID / KIM Watcher")
    main()


# import os
# import time
# import traceback
# import json
# from datetime import datetime
# from zoneinfo import ZoneInfo

# from app.konstant import (
#     get_input_path, get_output_path, create_dir,
#     load_db_config, get_config, get_regex,
#     get_sidkim_config, get_sidkim_regex,
#     CHECK_INTERVAL, PAUSE
# )
# from app.logger import setup_logger, rotate_daily_log
# from app.utils import Helper
# from app.amc.registry import load_registry, check_amc_file, load_sidkim_registry

# from app.sqlconnect import (
#     fetch_latest_uploaded_job,
#     transition_job_state,
#     JobState
# )



# # --- Helper Functions ---
# def detect_input_pdf():
#     """Return list of valid pdf filenames currently in INPUT_DIR."""
#     try:
#         files = [
#             f for f in os.listdir(INPUT_DIR)
#             if os.path.isfile(os.path.join(INPUT_DIR, f)) and (f.endswith("_SID.pdf") or f.endswith("_KIM.pdf") or f.endswith("_FS.pdf"))
#         ]
#         return sorted(files)
#     except FileNotFoundError:
#         os.makedirs(INPUT_DIR, exist_ok=True)
#         return []
#     except Exception as e:
#         logger.error(f"Error listing input dir: {e}")
#         return []

# def read_meta_content(root_dir, file_name):
#     """
#     Read sidecar meta JSON.
#     Meta is for parser hints ONLY, never job state.
#     """
#     meta_path = os.path.join(
#         root_dir,
#         file_name.replace(".pdf", ".meta.json")
#     )

#     if not os.path.exists(meta_path):
#         return {}

#     try:
#         with open(meta_path, "r", encoding="utf-8") as fh:
#             return json.load(fh)
#     except Exception as e:
#         logger.warning(f"Failed to read meta for {file_name}: {e}")
#         return {}


# # --- Main Watcher Loop ---


# #================== FACTSHEET ====================
# #=================================================

# def execute_sidkim_parser(path:str, amc_id:str, sidkim:str):
#     file_name = os.path.basename(path)
#     logger.info(f"Parsing: {file_name}")

#     try:
#         sidkim_registry = load_sidkim_registry()
#         if amc_id not in sidkim_registry:
#             raise ValueError("Unknown AMC ID")
        
#         config, regex = get_sidkim_config(amc_id), get_sidkim_regex()
#         if not config or not regex:
#             raise ValueError("Missing config or regex")
        
#         obj = sidkim_registry[amc_id](config, path)
#         temp_dict = {}
#         if sidkim.lower() == "sid":
            
#             temp_dict.update(obj.parse_page_zero("1"))
#             temp_dict.update(obj.parse_scheme_table_data("3-7"))
#             temp_dict.update(obj.parse_fund_manager_info("15-16"))
   
#         if sidkim.lower() == "kim":
#             temp_dict = obj.parse_KIM_data(pages="2", instrument_count=2)
        

#         data = obj.refine_data(temp_dict)
#         dfs = obj.merge_and_select_data(data=data,sid_or_kim=sidkim)
#         if not dfs:
#             raise ValueError("No parsed data")

#         save_path = os.path.join(
#             JSON_DIR,
#             file_name.replace(".pdf", ".json")
#         )
#         Helper.save_json(dfs, save_path)

#         return {"json_path": save_path}
#     except Exception as e:
#         logger.error(f"[SID/KIM PARSE ERROR] {file_name}: {e}")
#         logger.debug(traceback.format_exc())
#         return {"error": f"{type(e).__name__}: {e}"}  
#     pass

# def execute_parser(path, amc_id, year):
#     file_name = os.path.basename(path)
#     logger.info(f"Parsing: {file_name}")

#     try:
#         amc_registry = load_registry()
#         if amc_id not in amc_registry:
#             raise ValueError("Unknown AMC ID")

#         config, regex = get_config(year, amc_id), get_regex(year)
#         if not config or not regex:
#             raise ValueError("Missing config or regex")

#         obj = amc_registry[amc_id](config, regex, path)

#         title, path_pdf = obj.check_and_highlight(path)
#         if not title:
#             raise ValueError("check_and_highlight failed")

#         data = obj.get_data(path_pdf, title)
#         extracted = obj.get_generated_content(data)
#         refined = obj.refine_extracted_data(extracted)
#         dfs = obj.merge_and_select_data(refined)

#         if not dfs:
#             raise ValueError("No parsed data")

#         save_path = os.path.join(
#             JSON_DIR,
#             file_name.replace(".pdf", ".json")
#         )
#         Helper.save_json(dfs, save_path)

#         return {"json_path": save_path}

#     except Exception as e:
#         logger.error(f"[PARSE ERROR] {file_name}: {e}")
#         logger.debug(traceback.format_exc())
#         return {"error": f"{type(e).__name__}: {e}"}

# def process_file(file_name, db_config):
#     file_path = os.path.join(INPUT_DIR, file_name)

#     # 1. Find latest UPLOADED job
#     job = fetch_latest_uploaded_job(file_name, db_config)
#     if not job:
#         logger.warning(f"No UPLOADED job found for {file_name}")
#         return

#     job_id = job["id"]

#     # 2. Identify AMC + year
#     file_key, year, type_ = check_amc_file(file_path, file_name)

#     # 3. Parse
#     if type_ == "FS":
#         result = execute_parser(file_path, file_key, year)
    
#     if type_ == "SIDKIM":
#         execute_sidkim_parser(file_path, file_key, year)
#         pass

#     # 4. Transition state
#     if "json_path" in result:
#         transition_job_state(
#             job_id=job_id,
#             from_state=JobState.UPLOADED,
#             to_state=JobState.PARSED,
#             json_path=result["json_path"],
#             db_config=db_config
#         )

#         archive_dir = (
#             PRS_FS_DIR if file_name.endswith("_FS.pdf")
#             else PRS_SID_DIR if file_name.endswith("_SID.pdf")
#             else PRS_KIM_DIR if file_name.endswith("_KIM.pdf")
#             else PROCESSED_DIR
#         )

#         logger.info(f"[PARSED] {file_name}")

#     else:
#         transition_job_state(
#             job_id=job_id,
#             from_state=JobState.UPLOADED,
#             to_state=JobState.PARSE_FAILED,
#             error=result["error"],
#             db_config=db_config
#         )

#         archive_dir = FAILED_DIR
#         logger.error(f"[FAILED] {file_name}")

#     # 5. Archive PDF
#     Helper.archive_and_delete_files(
#         archive_dir,
#         {file_name: file_path}
#     )

#     # 6. Cleanup meta file
#     meta_path = os.path.join(
#         INPUT_DIR,
#         file_name.replace(".pdf", ".meta.json")
#     )
#     if os.path.exists(meta_path):
#         os.remove(meta_path)



# def main():
#     logger.info("Watcher started.")

#     while True:
#         try:
#             new_files = detect_input_pdf()

#             if not new_files:
#                 time.sleep(CHECK_INTERVAL)
#                 rotate_daily_log(logger)
#                 continue

#             logger.info(f"Files detected: {', '.join(new_files)}")
#             time.sleep(PAUSE)

#             db_config = load_db_config()

#             for file_name in new_files:
                
#                 if file_name.endswith("_FS.pdf"):
#                     process_file(file_name, db_config)
#                     time.sleep(1)
                
#                 elif file_name.endswith("_SID.pdf"):
#                     time.sleep(1)
#                     pass
                
#                 else: #kim
#                     time.sleep(1)
#                     pass

#             logger.save(f"Processed: {', '.join(new_files)}")

#         except KeyboardInterrupt:
#             logger.warning("Watcher stopped.")
#             break

#         except Exception as e:
#             logger.critical(f"Unhandled error: {e}")
#             logger.debug(traceback.format_exc())
#             time.sleep(5)


# # --- Entry Point ---
# if __name__ == "__main__":
    
#     #timezone
#     TIME_ZONE = ZoneInfo("Asia/Kolkata")

#     # dir
#     OUTPUT_DIR = get_output_path()
#     INPUT_DIR = get_input_path()
#     JSON_DIR = create_dir(OUTPUT_DIR, "json")
#     LOG_DIR = create_dir(OUTPUT_DIR, "logs")
#     PROCESSED_DIR = create_dir(OUTPUT_DIR, "processed")
#     PRS_FS_DIR = create_dir(PROCESSED_DIR,"fs")
#     PRS_SID_DIR = create_dir(PROCESSED_DIR,"sid")
#     PRS_KIM_DIR = create_dir(PROCESSED_DIR,"kim")
#     FAILED_DIR = create_dir(OUTPUT_DIR, "failed")
    
#     #log
#     logger = setup_logger("watcher", base_dir=LOG_DIR, log_level=12, set_global=True)
#     helper = Helper()
    
#     #sp call
#     SP_STATUS = False
        
#     logger.info("Running FactSheet Parser (watcher)")
#     main()



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
