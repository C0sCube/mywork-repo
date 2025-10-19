import os, time,logging, traceback

from app.konstant import *
from app.logger import create_logger, set_global_logger
logger = create_logger("watcher", log_dir=LOG_DIR,log_level=10) #logging.DEBUG is 10
set_global_logger(logger)

from core.utils import Helper
from core.mailer import Mailer
from app.regis_amc import *


logger.info(f"{PROGRAM_NAME} Running ...")
mail = Mailer()

def program_runner(path,amc_id, file_name):
    page_content = {}
    utils = Helper()
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

    try:
        if amc_id not in CLASS_REGISTRY:
            logger.warning(f"Unknown AMC ID: {amc_id}")
            return False

        logger.info(f"Processing {amc_id}:{file_name}")
        obj = CLASS_REGISTRY[amc_id](amc_id, path)

        if file_name in page_content:
            obj.PARAMS["table"] = page_content[file_name]
            logger.info(f"Page Data for {file_name} = {obj.PARAMS['table']}. ")

        title, path_pdf = obj.check_and_highlight(path)
        if not (title and path_pdf):
            raise ValueError("check_and_highlight failed")
        

        data = obj.get_data(path_pdf,title)
        extracted_text = obj.get_generated_content(data)
        final_text = obj.refine_extracted_data(extracted_text)
        dfs = obj.merge_and_select_data(final_text)
        
        with open("data.json", 'w') as f:
            json.dump(final_text, f, indent=2)
            
        with open("extract.json", 'w') as f:
            json.dump(extracted_text, f, indent=2)

        if not dfs: raise ValueError("No final merged data")

        save_path = os.path.join(JSON_DIR, file_name.replace(".pdf", ".json"))
        Helper.save_json(dfs, save_path)
        logger.save(f"Saved Json File: {save_path}")
        return True

    except Exception as e:
        logger.error(f"[Pipeline Error] {file_name} | {type(e).__name__}: {e}")
        logger.debug(traceback.format_exc())
        return False

# try:
known_files = set()
try:
    while True:
        current_files = {f for f in os.listdir(INPUT_PATH) if os.path.isfile(os.path.join(INPUT_PATH, f))}
        new_files = current_files - known_files
        
        if not new_files:
            logger.notice("No new files found. Sleeping...")
            time.sleep(CHECK_INTERVAL)
            logger.notice(f"Watching for new PDFs in: {INPUT_PATH}")
            continue
        logger.info(f"Files Detected: {' | '.join(sorted(new_files))}")
        logger.notice("Mandatory program pause for file save.")
        # mail.started(PROGRAM_NAME,data=new_files)
        # logger.info("Mail Sent to Recipient(s).")
        time.sleep(PAUSE_AFTER_FILE_DETECTION) #30s mostly
        completed, failed = dict(), dict()
        
        for file_name in new_files:
            try:
                file_path = os.path.join(INPUT_PATH, file_name)
                file_key = check_amc_file(file_name=file_name)

                result = program_runner(file_path,file_key, file_name)
                
                if result:completed.update({file_name:file_path})
                else:failed.update({file_name:file_path})
            
            except Exception as e:
                logger.error(f"Error in processing {file_name}. {type(e).__name__}: {e}")
                logger.debug(traceback.format_exc())
            
            time.sleep(2)
            
        logger.save(f"{",".join(completed.keys())} file(s) done. {",".join(failed.keys())} file(s) failed.")
        logger.trace("Session Completed. Ending Current Session.")

        # mail.end(PROGRAM_NAME, [completed, failed])
        # logger.info("Parsed Data Report sent to recipients.")

        known_files.update(new_files)
        if completed:Helper.copy_pdfs_to_folder(PROCESSED_DIR, completed)
        if failed:Helper.copy_pdfs_to_folder(FAILED_DIR, failed)
        Helper.delete_all_files(INPUT_PATH)

except KeyboardInterrupt:
    logger.warning("Watcher stopped by user.")
    logger.debug(traceback.format_exc())
    # mail.send_custom(
    #     subject=f"{PROGRAM_NAME} - Watcher Stopped",
    #     body_html=f"<p>The {PROGRAM_NAME} watcher has been stopped by the user.</p>",
    # )

except Exception as e:
    logger.critical(f"Watcher error in main.py {type(e).__name__}: {e}")
    logger.debug(traceback.format_exc())
    # mail.send_custom(
    #     subject=f"{PROGRAM_NAME} - Watcher Unexpected Error",
    #     body_html=f"<p>Unexpected error occurred: {type(e).__name__} - {e}</p>"
    # )



    
    
