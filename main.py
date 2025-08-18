import os, time, shutil, logging
from app.config_loader import Config
from app.utils import Helper
from app.mailer import Mailer
from app.program_logger import get_forever_logger
from app.class_registry import CLASS_REGISTRY, check_amc_file

CONFIG = Config()
WATCH_PATH, OUTPUT_PATH = CONFIG.watch_path, CONFIG.output_path
CHECK_INTERVAL = 10
PROGRAM_NAME = "FS_JSON_PARSE"

# Output directories
JSON_DIR = os.path.join(OUTPUT_PATH, CONFIG.output["json"])
LOG_DIR = os.path.join(OUTPUT_PATH, CONFIG.output["daily_log"])
FAILED_DIR = os.path.join(OUTPUT_PATH, CONFIG.output["failed"])
PROCESSED_DIR = os.path.join(OUTPUT_PATH, CONFIG.output["processed"])

logger = get_forever_logger("watcher", log_dir=LOG_DIR,log_level=logging.DEBUG)
logger.notice(f"{PROGRAM_NAME} Running ...")

mail = Mailer(logger=logger)
known_folders = set(os.listdir(WATCH_PATH))
logger.notice(f"Watching for new PDFs in: {WATCH_PATH}")

def process_amc(path,amc_id, file_name):
    page_content = {}

    if amc_id == "8_0":
        try:
            filename = file_name.replace(".pdf", ".xlsx")
            logger.info("Trying to read tabular data (xlsx)...")
            df = Helper.get_ext_in_folder(WATCH_PATH,filename,extension=".xlsx")
            if df:
                page_content = dict(zip(df.iloc[:, 0], df.iloc[:, 1]))
                logger.notice("Tabular data loaded.")
                logger.info(page_content)
            else:
                raise ValueError("Tabular Data Not Found.")
            
        except Exception as e:
            logger.warning(f"Tabular data loading failed: {e}")
    
    if amc_id == "1_0":
        pass
        try:
            filename = file_name.replace(".pdf", ".json")
            logger.info("Trying to read annot data (json)...")
            jsn = Helper.get_ext_in_folder(WATCH_PATH,filename,extension=".json")
            # if df:
            #     page_content = dict(zip(df.iloc[:, 0], df.iloc[:, 1]))
            #     logger.notice("Tabular data loaded.")
            #     logger.info(page_content)
            # else:
            #     raise ValueError("Tabular Data Not Found.")
            
        except Exception as e:
            logger.warning(f"Json loading failed: {e}")

    try:
        if amc_id not in CLASS_REGISTRY:
            logger.warning(f"Unknown AMC ID: {amc_id}")
            return False

        logger.info(f"Processing {amc_id}:{file_name}")
        obj = CLASS_REGISTRY[amc_id](file_name, amc_id, path, logger)

        if file_name in page_content:
            obj.PARAMS["table"] = page_content[file_name]
            logger.info(f"Page Data for {file_name} = {obj.PARAMS['table']}. ")

        title, path_pdf = obj.check_and_highlight(path)
        if not (title and path_pdf):
            raise ValueError("check_and_highlight failed")

        dfs =   obj.merge_and_select_data(
                    obj.refine_extracted_data(
                        obj.get_generated_content(
                            obj.get_data(path_pdf, title)
                        )
                    )
                )

        if not dfs:
            raise ValueError("No final merged data")

        save_path = os.path.join(JSON_DIR, file_name.replace(".pdf", ".json"))
        Helper.save_json(dfs, save_path)
        logger.save(f"Saved Json File: {save_path}")
        return True

    except Exception as e:
        logger.error(f"[Pipeline Error] {file_name} | {type(e).__name__}: {e}")
        return False

try:
    known_files = set()
    while True:
        current_files = {f for f in os.listdir(WATCH_PATH) if os.path.isfile(os.path.join(WATCH_PATH, f))}
        new_files = current_files - known_files
        
        if not new_files:
            logger.notice("No new files found. Sleeping...")
            time.sleep(CHECK_INTERVAL)
            logger.notice(f"Watching for new PDFs in: {WATCH_PATH}")
            continue
        
        logger.info(f"Files Detected: {' | '.join(sorted(new_files))}")

        mail.started(PROGRAM_NAME,data=new_files)
        logger.info("Mail Sent to Recipient(s).")
        
        total_done, total_failed = list(), list()
        time.sleep(30) #wait
        
        for file_name in new_files:
            file_path = os.path.join(WATCH_PATH, file_name)
            file_key = check_amc_file(file_name=file_name)
            
            result = process_amc(file_path,file_key, file_name)
            
            if result:
                Helper.copy_pdfs_to_folder(PROCESSED_DIR, file_path)
                total_done.append(file_name)
            else:
                Helper.copy_pdfs_to_folder(FAILED_DIR, file_path)
                total_failed.append(file_name)
            
            time.sleep(5)
            
        logger.save(f"{total_done} file(s) done. {total_failed} file(s) failed.")
        logger.trace("Session Completed. Ending Current Session.")

        mail.end(PROGRAM_NAME, [total_done, total_failed])
        logger.info("Parsed Data Report sent to recipients.")

        known_files.update(new_files)
        Helper.delete_all_files(WATCH_PATH)

except KeyboardInterrupt:
    logger.warning("Watcher stopped by user.")
    mail.send_custom(
        subject=f"{PROGRAM_NAME} - Watcher Stopped",
        body_html=f"<p>The {PROGRAM_NAME} watcher has been stopped by the user.</p>",
    )

except Exception as e:
    logger.error(f"[Watcher Error] {type(e).__name__}: {e}")
    mail.send_custom(
        subject=f"{PROGRAM_NAME} - Watcher Unexpected Error",
        body_html=f"<p>Unexpected error occurred: {type(e).__name__} - {e}</p>"
    )
    time.sleep(CHECK_INTERVAL)




# while True:
#     try:
#         current_folders = set(os.listdir(WATCH_PATH))
#         new_folders = current_folders - known_folders

#         for folder in new_folders:
#             amc_path = os.path.join(WATCH_PATH, folder)
#             if not os.path.isdir(amc_path):
#                 continue

#             folder_key = "_".join(folder.split()).lower()
#             # logger = setup_logger(folder_key, base_log_dir=SESSION_LOG_DIR, redirect_stdout=True)
#             logger.notice(f"New folder: {folder_key}")
#             time.sleep(30)  # Wait for copy to complete
            
#             mail.started("FS_JSON_PARSE_KAUSTUBH")
#             logger.info("Mail Send to Recipients.")
            
            # mutual_fund = Helper().get_pdf_with_id(amc_path)
#             total_done, total_failed = {}, {}

#             for amc_id, class_ in CLASS_REGISTRY.items():
#                 content = mutual_fund.get(amc_id)
#                 if not content:
#                     continue
            
#                 logger.info(f"{amc_id} FS attached.")
#                 logger.info(f"{amc_id} FS attached.")
                
#                 result = process_amc(amc_id, content, amc_path, logger)
#                 total_done.update(result["done"])
#                 total_failed.update(result["failed"])

#             # Handle output
#             if total_done:
#                 Helper.save_text(total_done, os.path.join(PROCESSED_DIR, "processed_amc.txt"))
#                 Helper.copy_pdfs_to_folder(PROCESSED_DIR, total_done)
#                 logger.save(f"{len(total_done)} AMC(s) processed.")

#             if total_failed:
#                 Helper.save_text(total_failed, os.path.join(FAILED_DIR, "failed_amc.txt"))
#                 Helper.copy_pdfs_to_folder(FAILED_DIR, total_failed)
#                 logger.warning(f"{len(total_failed)} AMC(s) failed. They are {total_failed}")

#             shutil.rmtree(amc_path, ignore_errors=True)
#             logger.notice(f"Deleted input folder: {amc_path}")
#             logger.trace("Session Completed. Ending Current Session.")
            
#             #mail
#             mail.end("FS_JSON_PARSE_KAUSTUBH",[total_done,total_failed])
#             logger.info("Parsed Data Report Send to Recipients")

#         known_folders.update(new_folders)
#         logger.notice("No new folders found. Sleeping...")
#         time.sleep(CHECK_INTERVAL)

#     except KeyboardInterrupt:
#         logger.warning("Watcher stopped by user.")
#         break
#     except Exception as e:
#         logger.error(f"[Watcher Error] {type(e).__name__}: {e}")
#         time.sleep(CHECK_INTERVAL)
