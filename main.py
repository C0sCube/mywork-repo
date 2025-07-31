import os, time, shutil, logging
from app.config_loader import Config
from app.utils import Helper
from app.mailer import Mailer
from app.program_logger import get_forever_logger, setup_session_logger
from app.class_registry import CLASS_REGISTRY

CONFIG = Config()
WATCH_PATH, OUTPUT_PATH = CONFIG.watch_path, CONFIG.output_path
CHECK_INTERVAL = 10

# Output directories
JSON_DIR = os.path.join(OUTPUT_PATH, CONFIG.output["json"])
DAILY_LOG_DIR = os.path.join(OUTPUT_PATH, CONFIG.output["daily_logs"])
SESSION_LOG_DIR = os.path.join(OUTPUT_PATH, CONFIG.output["session_logs"])
FAILED_DIR = os.path.join(OUTPUT_PATH, CONFIG.output["failed"])
PROCESSED_DIR = os.path.join(OUTPUT_PATH, CONFIG.output["processed"])

watch_logger = get_forever_logger("watcher", log_dir=DAILY_LOG_DIR,log_level=logging.WARNING)
watch_logger.notice("FS_JSON_PARSE main.py Running ...")

mail = Mailer()
known_folders = set(os.listdir(WATCH_PATH))
watch_logger.notice(f"Watching for new PDFs in: {WATCH_PATH}")

def process_amc(amc_id, content, amc_path, session_logger):
    page_content = {}
    results = {"done": {}, "failed": {}}

    if amc_id == "8_0":
        try:
            session_logger.info("Trying to read tabular data (xlsx)...")
            df = Helper().get_xlsx_in_folder(amc_path)
            if df is not None:
                page_content = dict(zip(df.iloc[:, 0], df.iloc[:, 1]))
                session_logger.notice("Tabular data loaded.")
                session_logger.info(page_content)
        except Exception as e:
            session_logger.warning(f"Tabular data loading failed: {e}")

    for fund_name, path in content:
        try:
            session_logger.info(f"Processing {amc_id}:{fund_name}")
            obj = CLASS_REGISTRY[amc_id](fund_name, amc_id, path, session_logger)

            fundName = fund_name.replace(".pdf", "").strip()
            if fundName in page_content:
                obj.PARAMS["table"] = page_content[fundName]
                session_logger.info(f"Page Data for {fundName} = {obj.PARAMS['table']}. ")

            title, path_pdf = obj.check_and_highlight(path)
            if not (title and path_pdf):
                raise ValueError("check_and_highlight failed")

            data = obj.get_data(path_pdf, title)
            extracted = obj.get_generated_content(data)
            final = obj.refine_extracted_data(extracted)
            dfs = obj.merge_and_select_data(final)

            if not dfs:
                raise ValueError("No final merged data")

            save_path = os.path.join(JSON_DIR, obj.FILE_NAME.replace(".pdf", ".json"))
            Helper.save_json(dfs, save_path)
            session_logger.save(f"Saved JSON: {save_path}")
            results["done"][fund_name] = path

        except Exception as e:
            session_logger.error(f"[Pipeline Error] {fund_name} | {type(e).__name__}: {e}")
            results["failed"][fund_name] = path

    return results

while True:
    try:
        current_folders = set(os.listdir(WATCH_PATH))
        new_folders = current_folders - known_folders

        for folder in new_folders:
            amc_path = os.path.join(WATCH_PATH, folder)
            if not os.path.isdir(amc_path):
                continue

            folder_key = "_".join(folder.split()).lower()
            session_logger = setup_session_logger(folder_key, base_log_dir=SESSION_LOG_DIR, redirect_stdout=True)
            session_logger.notice(f"New folder: {folder_key}")
            time.sleep(20)  # Wait for copy to complete

            mutual_fund = Helper().get_pdf_with_id(amc_path)
            total_done, total_failed = {}, {}

            for amc_id, class_ in CLASS_REGISTRY.items():
                content = mutual_fund.get(amc_id)
                if not content:
                    continue
            
                session_logger.info(f"{amc_id} FS attached.")
                watch_logger.info(f"{amc_id} FS attached.")
                
                result = process_amc(amc_id, content, amc_path, session_logger)
                total_done.update(result["done"])
                total_failed.update(result["failed"])

            # Handle output
            if total_done:
                Helper.save_text(total_done, os.path.join(PROCESSED_DIR, "processed_amc.txt"))
                Helper.copy_pdfs_to_folder(PROCESSED_DIR, total_done)
                session_logger.save(f"{len(total_done)} AMC(s) processed.")

            if total_failed:
                Helper.save_text(total_failed, os.path.join(FAILED_DIR, "failed_amc.txt"))
                Helper.copy_pdfs_to_folder(FAILED_DIR, total_failed)
                session_logger.warning(f"{len(total_failed)} AMC(s) failed. They are {total_failed}")

            shutil.rmtree(amc_path, ignore_errors=True)
            session_logger.notice(f"Deleted input folder: {amc_path}")
            session_logger.trace("Session Completed. Ending Current Session.")
            watch_logger.notice(f"Folder {folder_key} Processing Complete.")

        known_folders.update(new_folders)
        watch_logger.notice("No new folders found. Sleeping...")
        time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        watch_logger.warning("Watcher stopped by user.")
        break
    except Exception as e:
        watch_logger.error(f"[Watcher Error] {type(e).__name__}: {e}")
        time.sleep(CHECK_INTERVAL)
