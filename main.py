import os, time,traceback
from datetime import datetime

# --- Import your actual modules ---
from app.konstant import (
    get_input_path, get_output_path, create_dir,
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

logger = setup_logger("watcher", base_dir=LOG_DIR, log_level=12)
rotate_daily_log(logger)
set_global_logger(logger)

# --- Helper Functions ---
def discover_new_files(known_files):
    current_files = {
        f for f in os.listdir(INPUT_DIR)
        if os.path.isfile(os.path.join(INPUT_DIR, f))
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
        update_table(update)
    return reports

def program_runner(path, amc_id, file_name):
    try:
        if amc_id not in CLASS_REGISTRY:
            logger.warning(f"Unknown AMC ID: {amc_id}")
            return None

        logger.notice(f"Processing {amc_id}: {file_name}")
        obj = CLASS_REGISTRY[amc_id](amc_id, path)

        title, path_pdf = obj.check_and_highlight(path)
        if not (title and path_pdf):
            raise ValueError("check_and_highlight failed")

        data = obj.get_data(path_pdf, title)
        extracted_text = obj.get_generated_content(data)
        final_text = obj.refine_extracted_data(extracted_text)
        dfs = obj.merge_and_select_data(final_text)
        if not dfs:
            raise ValueError("No final merged data")

        save_path = os.path.join(JSON_DIR, file_name.replace(".pdf", ".json"))
        Helper.save_json(dfs, save_path)
        logger.save(f"Saved JSON File: {save_path}")
        return save_path

    except Exception as e:
        logger.error(f"[Pipeline Error] {file_name} | {type(e).__name__}: {e}")
        logger.debug(traceback.format_exc())
        return None

def process_file(file_name, report):
    try:
        file_path = os.path.join(INPUT_DIR, file_name)
        file_key = check_amc_file(file_name=file_name)
        result = program_runner(file_path, file_key, file_name)

        report["end_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        report["json_path"] = result
        report["status"] = "Completed" if result else "Failed"

        archive_dir = PROCESSED_DIR if result else FAILED_DIR
        Helper.archive_files(archive_dir, {file_name: file_path})

    except Exception as e:
        logger.error(f"Error in processing {file_name}: {type(e).__name__}: {e}")
        logger.debug(traceback.format_exc())
        report.update({
            "end_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "json_path": None,
            "status": "Error",
            "error": str(e)
        })

    update_table(report)
    return report["json_path"]

# --- Main Watcher Loop ---
def main():
    known_files = set()

    while True:
        try:
            new_files = discover_new_files(known_files)

            if not new_files:
                logger.notice("No new files found. Sleeping...")
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


# import os, time, traceback
# # from app.konstant import *
# from app.logger import setup_logger, rotate_daily_log, set_global_logger
# from app.utils import Helper
# from app.amc.registry import *
# from app.konstant import (get_input_path, get_output_path,create_dir)
# from app.konstant import(PROGRAM_NAME, CHECK_INTERVAL, PAUSE)
# from app.sqlconnect import update_table

# OUTPUT_DIR = get_output_path()
# INPUT_DIR = get_input_path()
# JSON_DIR = create_dir(OUTPUT_DIR,"json")

# # -------------------- LOGGER SETUP --------------------
# log_dir = create_dir(OUTPUT_DIR,"log")
# logger = setup_logger("watcher", base_dir=log_dir, log_level=12)
# rotate_daily_log(logger)
# set_global_logger(logger)

# logger.info(f"{PROGRAM_NAME} Running ...")

# def program_runner(path, amc_id, file_name):
#     """Runs the entire AMC data extraction pipeline for a single PDF."""
#     page_content = {}
#     try:
#         if amc_id not in CLASS_REGISTRY:
#             logger.warning(f"Unknown AMC ID: {amc_id}")
#             return False

#         logger.notice(f"Processing {amc_id}: {file_name}")
#         obj = CLASS_REGISTRY[amc_id](amc_id, path)

#         if file_name in page_content:
#             obj.PARAMS["table"] = page_content[file_name]
#             logger.trace(f"Page Data for {file_name} = {obj.PARAMS['table']}")

#         title, path_pdf = obj.check_and_highlight(path)
#         if not (title and path_pdf):
#             raise ValueError("check_and_highlight failed")
        
#         data = obj.get_data(path_pdf, title)
#         extracted_text = obj.get_generated_content(data)
#         final_text = obj.refine_extracted_data(extracted_text)
#         dfs = obj.merge_and_select_data(final_text)
#         if not dfs: raise ValueError("No final merged data")
        
#         save_path = os.path.join(JSON_DIR, file_name.replace(".pdf", ".json"))
#         Helper.save_json(dfs, save_path)
#         logger.save(f"Saved JSON File: {save_path}")
#         return save_path

#     except Exception as e:
#         logger.error(f"[Pipeline Error] {file_name} | {type(e).__name__}: {e}")
#         logger.debug(traceback.format_exc())
#         return None

# # -------------------- WATCHER LOOP --------------------
# def main():
#     known_files = set()
    
#     processed_dir = create_dir(OUTPUT_DIR,"processed")
#     failed_dir = create_dir(OUTPUT_DIR,"failed")
#     while True:
#         try:
#             # check new PDFs in input folder
#             current_files = {f for f in os.listdir(INPUT_DIR) if os.path.isfile(os.path.join(INPUT_DIR, f))}
#             new_files = current_files - known_files

#             if not new_files:
#                 logger.notice("No new files found. Sleeping...")
#                 time.sleep(CHECK_INTERVAL)
#                 rotate_daily_log(logger)  # ensure correct folder daily
#                 logger.trace(f"Watching for new PDFs in: {INPUT_DIR}")
#                 continue

#             logger.info(f"Files Detected: {' | '.join(sorted(new_files))}")
#             logger.notice("Mandatory pause for file save.")
#             time.sleep(PAUSE)

#             completed, failed = {}, {}
            
#             status_reports ={}
#             for file_name in new_files:
#                 update = {
#                     "start_time":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
#                     "end_time":None,
#                     "file_name":file_name,
#                     "json_path":None,
#                     "status":"Pending",
#                     "error":None
#                 } 
                
#                 status_reports[file_name] = update
#                 update_table(update)
               

#             for file_name in new_files:
#                 report = status_reports[file_name]
#                 try:
#                     file_path = os.path.join(INPUT_DIR, file_name)
#                     file_key = check_amc_file(file_name=file_name)

#                     result = program_runner(file_path, file_key, file_name)
#                     if result:
#                         completed[file_name] = file_path
#                         Helper.archive_files(processed_dir, {file_name: file_path})
#                         report.update({"end_time":datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "json_path":result, "status":"Completed" })
#                     else:
#                         failed[file_name] = file_path
#                         Helper.archive_files(failed_dir, {file_name: file_path})
#                         report.update({"end_time":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  "json_path":None,  "status":"Failed" })
                    
#                     update_table(report)

#                 except Exception as e:
#                     logger.error(f"Error in processing {file_name}: {type(e).__name__}: {e}")
#                     logger.debug(traceback.format_exc())
#                     report.update({"end_time":datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "json_path":None,"status":"Error", "error": str(e) })
                    
#                     update_table(report)

 
#                 time.sleep(1)

#             logger.save(f"[{', '.join(completed.keys())}] file(s) done. [{', '.join(failed.keys())}] file(s) failed.")
#             logger.trace("Session completed. Ending current session.")

#             # move processed files + delete
#             known_files.update(new_files)
#             Helper.delete_files([os.path.join(INPUT_DIR,f) for f in known_files])

#         except KeyboardInterrupt:
#             logger.warning("Watcher stopped by user (KeyboardInterrupt). Exiting gracefully.")
#             break
#         except Exception as e:
#             logger.critical(f"Unhandled watcher error in main loop: {type(e).__name__}: {e}")
#             logger.debug(traceback.format_exc())
#             time.sleep(5)

# if __name__ == "__main__":
    
#     logger.info("Running program FactSheet Parser")
#     main()

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