import os, time, traceback
# from app.konstant import *
from app.logger import setup_logger, rotate_daily_log, set_global_logger
from app.utils import Helper
from app.amc.registry import *
from app.konstant import (get_input_path, get_output_path,create_dir)
from app.konstant import(PROGRAM_NAME, CHECK_INTERVAL, PAUSE)
from app.sqlconnect import update_table

OUTPUT_DIR = get_output_path()
INPUT_DIR = get_input_path()
JSON_DIR = create_dir(OUTPUT_DIR,"json")

# -------------------- LOGGER SETUP --------------------
log_dir = create_dir(OUTPUT_DIR,"log")
logger = setup_logger("watcher", base_dir=log_dir, log_level=12)
rotate_daily_log(logger)
set_global_logger(logger)

logger.info(f"{PROGRAM_NAME} Running ...")

def program_runner(path, amc_id, file_name):
    """Runs the entire AMC data extraction pipeline for a single PDF."""
    page_content = {}
    try:
        if amc_id not in CLASS_REGISTRY:
            logger.warning(f"Unknown AMC ID: {amc_id}")
            return False

        logger.notice(f"Processing {amc_id}: {file_name}")
        obj = CLASS_REGISTRY[amc_id](amc_id, path)

        if file_name in page_content:
            obj.PARAMS["table"] = page_content[file_name]
            logger.trace(f"Page Data for {file_name} = {obj.PARAMS['table']}")

        title, path_pdf = obj.check_and_highlight(path)
        if not (title and path_pdf):
            raise ValueError("check_and_highlight failed")
        
        data = obj.get_data(path_pdf, title)
        extracted_text = obj.get_generated_content(data)
        final_text = obj.refine_extracted_data(extracted_text)
        dfs = obj.merge_and_select_data(final_text)
        if not dfs: raise ValueError("No final merged data")
        
        save_path = os.path.join(JSON_DIR, file_name.replace(".pdf", ".json"))
        Helper.save_json(dfs, save_path)
        logger.save(f"Saved JSON File: {save_path}")
        return save_path

    except Exception as e:
        logger.error(f"[Pipeline Error] {file_name} | {type(e).__name__}: {e}")
        logger.debug(traceback.format_exc())
        return None

# -------------------- WATCHER LOOP --------------------
def main():
    known_files = set()
    
    processed_dir = create_dir(OUTPUT_DIR,"processed")
    failed_dir = create_dir(OUTPUT_DIR,"failed")
    while True:
        try:
            # check new PDFs in input folder
            current_files = {f for f in os.listdir(INPUT_DIR) if os.path.isfile(os.path.join(INPUT_DIR, f))}
            new_files = current_files - known_files

            if not new_files:
                logger.notice("No new files found. Sleeping...")
                time.sleep(CHECK_INTERVAL)
                rotate_daily_log(logger)  # ensure correct folder daily
                logger.trace(f"Watching for new PDFs in: {INPUT_DIR}")
                continue

            logger.info(f"Files Detected: {' | '.join(sorted(new_files))}")
            logger.notice("Mandatory pause for file save.")
            time.sleep(PAUSE)

            completed, failed = {}, {}

            for file_name in new_files:
                try:
                    
                    status_report = {
                        "start_time":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "end_time":"",
                        "file_name":file_name,
                        "json_path":None,
                        "status":None,
                        "error":None
                    }
                    
                    file_path = os.path.join(INPUT_DIR, file_name)
                    file_key = check_amc_file(file_name=file_name)

                    result = program_runner(file_path, file_key, file_name)
                    if result:
                        completed[file_name] = file_path
                        Helper.archive_files(processed_dir, {file_name: file_path})
                        status_report.update({
                            "end_time":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "json_path":result,
                            "status":"Completed"
                            })
                    else:
                        failed[file_name] = file_path
                        Helper.archive_files(failed_dir, {file_name: file_path})
                        status_report.update({
                            "end_time":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "json_path":None,
                            "status":"Failed"
                            })
                    
                    update_table(status_report)

                except Exception as e:
                    logger.error(f"Error in processing {file_name}: {type(e).__name__}: {e}")
                    logger.debug(traceback.format_exc())
                    status_report.update({
                            "end_time":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "json_path":None,
                            "status":"Error"
                            })
                    
                    update_table(status_report)

 
                time.sleep(1)

            logger.save(f"[{', '.join(completed.keys())}] file(s) done. [{', '.join(failed.keys())}] file(s) failed.")
            logger.trace("Session completed. Ending current session.")

            # move processed files
            known_files.update(new_files)
            known_file_paths = [os.path.join(INPUT_DIR,f) for f in known_files]
            Helper.delete_files(known_file_paths)

        except KeyboardInterrupt:
            logger.warning("Watcher stopped by user (KeyboardInterrupt). Exiting gracefully.")
            break
        except Exception as e:
            logger.critical(f"Unhandled watcher error in main loop: {type(e).__name__}: {e}")
            logger.debug(traceback.format_exc())
            time.sleep(5)

if __name__ == "__main__":
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