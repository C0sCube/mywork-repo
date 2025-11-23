import os, time,traceback
from datetime import datetime

# --- Import your actual modules ---
from app.konstant import (
    get_input_path, get_output_path, create_dir,
    load_db_config, get_config, get_regex,
    CHECK_INTERVAL, PAUSE
)
from app.logger import setup_logger, rotate_daily_log, set_global_logger
from app.utils import Helper
from app.amc.registry import CLASS_REGISTRY, check_amc_file
from app.sqlconnect import update_table

# --- Setup paths and logger ---
OUTPUT_DIR = get_output_path()
INPUT_DIR = get_input_path()
JSON_DIR = create_dir(OUTPUT_DIR, "json")
LOG_DIR = create_dir(OUTPUT_DIR, "log")
PROCESSED_DIR = create_dir(OUTPUT_DIR, "processed")
FAILED_DIR = create_dir(OUTPUT_DIR, "failed")
DB_CONFIG = load_db_config()

logger = setup_logger("watcher", base_dir=LOG_DIR, log_level=12)
rotate_daily_log(logger)
set_global_logger(logger)

# --- Helper Functions ---
def discover_new_files(known_files):
    current_files = {
        f for f in os.listdir(INPUT_DIR)
        if os.path.isfile(os.path.join(INPUT_DIR, f)) and f.endswith("_FS.pdf")
    }
    return current_files - known_files

def initialize_status_reports(new_files):
    reports = {}
    for file_name in new_files:
        update = {
            "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": None,
            "file_name": file_name,
            "json_path": None,
            "status": "Pending",
            "error": None
        }
        reports[file_name] = update
        update_table(update,db_config=DB_CONFIG)
    return reports

def program_runner(path, amc_id, year, report):
    file_name = os.path.basename(path)
    logger.notice(f"Process {amc_id}: {file_name}")
    try:
        if amc_id not in CLASS_REGISTRY:
            raise ValueError("Unknown AMC ID or File.")
        
        config  =  get_config(year,amc_id)
        regex = get_regex(year)
        if not config or not regex:
            raise ValueError(f"Unknown {amc_id} not present in Config. or regex")
        
        obj = CLASS_REGISTRY[amc_id](config,regex,path)

        title, path_pdf = obj.check_and_highlight(path)
        if not (title and path_pdf):
            raise ValueError("check_and_highlight failed.")

        data = obj.get_data(path_pdf, title)
        extracted_text = obj.get_generated_content(data)
        final_text = obj.refine_extracted_data(extracted_text)
        dfs = obj.merge_and_select_data(final_text)
        if not dfs:
            raise ValueError("No final merged data")

        save_path = os.path.join(JSON_DIR, file_name.replace(".pdf", ".json"))
        Helper.save_json(dfs, save_path)
        logger.save(f"Saved JSON File: {save_path}")
        
        
        report.update({
            "end_time":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "json_path":save_path,
            "status":"completed"
        })

    except Exception as e:
        logger.error(f"[Pipeline Error] {file_name} | {type(e).__name__}: {e}")
        logger.debug(traceback.format_exc())
        
        report.update({
            "end_time":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "json_path":None,
            "status":"failed",
            "error":f"{type(e).__name__}: {e}"
        })
                
    return report

def process_file(file_name, report):
    try:
        file_path = os.path.join(INPUT_DIR, file_name)
        
        file_key, year = check_amc_file(file_name=file_name)
        report = program_runner(file_path, file_key, year, report)
        
        archive_dir = PROCESSED_DIR if report["status"] == "completed" else FAILED_DIR
        Helper.archive_files(archive_dir, {file_name: file_path})

    except Exception as e:
        logger.error(f"Error in processing {file_name}: {type(e).__name__}: {e}")
        logger.debug(traceback.format_exc())
        report.update({
            "end_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "json_path": None,
            "status": "Error",
            "error": f"{type(e).__name__}: {e}"
        })

    update_table(report, db_config=DB_CONFIG)
    return report["json_path"]

# --- Main Watcher Loop ---
def main():
    known_files = set()

    while True:
        try:
            new_files = discover_new_files(known_files)

            if not new_files:
                logger.notice("No new files. Sleeping...")
                time.sleep(CHECK_INTERVAL)
                rotate_daily_log(logger)
                continue

            logger.info(f"Files Detected: {' | '.join(sorted(new_files))}")
            logger.notice("Mandatory pause for file save.")
            time.sleep(PAUSE)

            status_reports = initialize_status_reports(new_files)
            completed, failed = {}, {}

            for file_name in new_files:
                report = status_reports[file_name]
                result = process_file(file_name, report)
                if result:
                    completed[file_name] = result
                else:
                    failed[file_name] = report.get("error")
                time.sleep(1)

            logger.save(f"[{', '.join(completed.keys())}] file(s) done. [{', '.join(failed.keys())}] file(s) failed.")
            known_files.update(new_files)
            Helper.delete_files([os.path.join(INPUT_DIR, f) for f in known_files])

        except KeyboardInterrupt:
            logger.warning("Watcher stopped by user. Exiting gracefully.")
            break
        except Exception as e:
            logger.critical(f"Unhandled error: {type(e).__name__}: {e}")
            logger.debug(traceback.format_exc())
            time.sleep(5)

# --- Entry Point ---
if __name__ == "__main__":
    logger.info("Running program FactSheet Parser")
    main()





# -------------------- CORE PIPELINE --------------------
# if amc_id == "8_0":
#     try:
#         filename = file_name.replace(".pdf", ".xlsx")
#         logger.info("Trying to read tabular data (xlsx)...")
#         df = utils.get_ext_in_folder(INPUT_DIR,filename,extension=".xlsx")
#         if df:
#             page_content = dict(zip(df.iloc[:, 0], df.iloc[:, 1]))
#             logger.notice("Tabular data loaded.")
#             logger.info(page_content)
#         else:
#             raise ValueError("Tabular Data Not Found.")
    
#     except Exception as e:
#         logger.warning(f"Tabular data loading failed: {e}")

# if amc_id == "1_0":
#     pass
#     try:
#         filename = file_name.replace(".pdf", ".json")
#         logger.info("Trying to read annot data (json)...")
#         jsn = utils.get_ext_in_folder(INPUT_DIR,filename,extension=".json")
#         # if df:
#         #     page_content = dict(zip(df.iloc[:, 0], df.iloc[:, 1]))
#         #     logger.notice("Tabular data loaded.")
#         #     logger.info(page_content)
#         # else:
#         #     raise ValueError("Tabular Data Not Found.")
    
#     except Exception as e:
#         logger.warning(f"Json loading failed: {e}")