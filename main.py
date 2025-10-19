import os, time, traceback
# from app.konstant import *
from app.logger import setup_logger, rotate_daily_log, set_global_logger
from app.utils import Helper
from app.mailer import Mailer
from app.amc.registry import *
from app.konstant import (JSON_DIR,LOG_DIR,PROCESSED_DIR,FAILED_DIR, INPUT_PATH)
from app.konstant import(PROGRAM_NAME, CHECK_INTERVAL, PAUSE_AFTER_FILE_DETECTION)

# -------------------- LOGGER SETUP --------------------
logger = setup_logger("watcher", base_dir=LOG_DIR, log_level=12)  # 12 ~ between DEBUG(10) and INFO(20)
rotate_daily_log(logger)  # ensure correct folder for today
set_global_logger(logger)

logger.info(f"{PROGRAM_NAME} Running ...")

# -------------------- CORE PIPELINE --------------------
    # if amc_id == "8_0":
    #     try:
    #         filename = file_name.replace(".pdf", ".xlsx")
    #         logger.info("Trying to read tabular data (xlsx)...")
    #         df = utils.get_ext_in_folder(INPUT_PATH,filename,extension=".xlsx")
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
    #         jsn = utils.get_ext_in_folder(INPUT_PATH,filename,extension=".json")
    #         # if df:
    #         #     page_content = dict(zip(df.iloc[:, 0], df.iloc[:, 1]))
    #         #     logger.notice("Tabular data loaded.")
    #         #     logger.info(page_content)
    #         # else:
    #         #     raise ValueError("Tabular Data Not Found.")
        
    #     except Exception as e:
    #         logger.warning(f"Json loading failed: {e}")

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

        # step 1: detect + highlight
        title, path_pdf = obj.check_and_highlight(path)
        if not (title and path_pdf):
            raise ValueError("check_and_highlight failed")
        # step 2: extract data
        data = obj.get_data(path_pdf, title)
        # step 3: generate content from extracted data
        extracted_text = obj.get_generated_content(data)
        # step 4: refine text into structured data
        final_text = obj.refine_extracted_data(extracted_text)
        # step 5: merge and select final JSON data
        dfs = obj.merge_and_select_data(final_text)
        if not dfs:
            raise ValueError("No final merged data")
        # step 6: save output JSON
        save_path = os.path.join(JSON_DIR, file_name.replace(".pdf", ".json"))
        Helper.save_json(dfs, save_path)
        logger.save(f"Saved JSON File: {save_path}")
        return True

    except Exception as e:
        logger.error(f"[Pipeline Error] {file_name} | {type(e).__name__}: {e}")
        logger.debug(traceback.format_exc())
        return False


# -------------------- WATCHER LOOP --------------------
def main():
    known_files = set()
    mail = Mailer()

    while True:
        try:
            # check new PDFs in input folder
            current_files = {f for f in os.listdir(INPUT_PATH) if os.path.isfile(os.path.join(INPUT_PATH, f))}
            new_files = current_files - known_files

            if not new_files:
                logger.notice("No new files found. Sleeping...")
                time.sleep(CHECK_INTERVAL)
                rotate_daily_log(logger)  # ensure correct folder daily
                logger.trace(f"Watching for new PDFs in: {INPUT_PATH}")
                continue

            logger.info(f"Files Detected: {' | '.join(sorted(new_files))}")
            logger.notice("Mandatory pause for file save.")
            time.sleep(PAUSE_AFTER_FILE_DETECTION)

            completed, failed = {}, {}

            for file_name in new_files:
                try:
                    file_path = os.path.join(INPUT_PATH, file_name)
                    file_key = check_amc_file(file_name=file_name)

                    result = program_runner(file_path, file_key, file_name)
                    if result: completed[file_name] = file_path
                    else: failed[file_name] = file_path

                except Exception as e:
                    logger.error(f"Error in processing {file_name}: {type(e).__name__}: {e}")
                    logger.debug(traceback.format_exc())

                time.sleep(1)

            logger.save(f"[{', '.join(completed.keys())}] file(s) done. [{', '.join(failed.keys())}] file(s) failed.")
            logger.trace("Session completed. Ending current session.")

            # move processed files
            known_files.update(new_files)
            if completed: Helper.archive_files(PROCESSED_DIR, completed)
            if failed:Helper.archive_files(FAILED_DIR, failed)
            Helper.clear_folder(INPUT_PATH)
            time.sleep(10)
            known_files = set()

        except KeyboardInterrupt:
            logger.warning("Watcher stopped by user (KeyboardInterrupt). Exiting gracefully.")
            break
        except Exception as e:
            logger.critical(f"Unhandled watcher error in main loop: {type(e).__name__}: {e}")
            logger.debug(traceback.format_exc())
            time.sleep(5)

if __name__ == "__main__":
    main()
