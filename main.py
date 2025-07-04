import os, sys, io, time, shutil
from datetime import datetime
from app.config_loader import load_config_once, get_config
from app.utils import *
from app.program_logger import setup_logger, cleanup_logger
from app.class_registry import CLASS_REGISTRY
from app.mailer import Mailer

# Set UTF-8 encoding for stdout/stderr
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

print("FS_JSON_PARSE main.py Running ...", flush=True)

# Load config
load_config_once(output_folder=None)
CONFIG = get_config()
WATCH_PATH, OUTPUT_PATH = CONFIG["amc_path"], CONFIG["output_path"]

# mail config
# mail = Mailer()

# Output folders
CHECK_INTERVAL = 10
JSON_DIR = os.path.join(OUTPUT_PATH, CONFIG["output"]["json"])
LOG_DIR = os.path.join(OUTPUT_PATH, CONFIG["output"]["logs"])
FAILED_DIR = os.path.join(OUTPUT_PATH, CONFIG["output"]["failed"])
PROCESSED_DIR = os.path.join(OUTPUT_PATH, CONFIG["output"]["processed"])

# Known folders
known_folders = set(os.listdir(WATCH_PATH))
print(f"[WATCHER] Watching for new PDFs in: {WATCH_PATH}", flush=True)

# Watcher loop
while True:
    try:
        current_folders = set(os.listdir(WATCH_PATH))
        new_folders = current_folders - known_folders

        for new_folder in new_folders:
            amc_path = os.path.join(WATCH_PATH, new_folder)
            if not os.path.isdir(amc_path):
                continue

            # Setup a unique logger per folder
            log_filename = new_folder
            logger = setup_logger(log_dir=LOG_DIR, logger_name="fs_logger",folder_name=log_filename)

            print(f"[WATCHER] New folder detected: {new_folder}")
            logger.info(f"\nProgram Execution Started for: {new_folder}")
            # mail.started("FS main.py")
            mutual_fund = Helper.get_pdf_with_id(amc_path)
            amc_done, amc_not_done = {}, {}

            for amc_id, class_ in CLASS_REGISTRY.items():
                try:
                    fund_name, path = mutual_fund[amc_id]
                except KeyError:
                    logger.warning(f"{amc_id} FS not attached. Skipping.")
                    time.sleep(.2)
                    continue

                try:
                    logger.info(f"Processing {amc_id}:{class_.__name__}")
                    obj = class_(fund_name, amc_id, path)
                    title, path_pdf = obj.check_and_highlight(path)

                    if not (path_pdf and title):
                        raise Exception("check_and_highlight returned invalid results")

                    data = obj.get_data(path_pdf, title)
                    extracted_text = obj.get_generated_content(data)
                    final_text = obj.refine_extracted_data(extracted_text)
                    dfs = obj.merge_and_select_data(final_text)

                    if not dfs:
                        raise Exception("Final merged data is empty")

                    save_path = os.path.join(JSON_DIR, obj.FILE_NAME.replace(".pdf", ".json"))
                    Helper.save_json(dfs, save_path)
                    logger.info(f"Saved JSON: {save_path}")
                    amc_done[fund_name] = path

                except Exception:
                    logger.exception(f"[Pipeline Error] {fund_name}({class_.__name__})")
                    amc_not_done[fund_name] = path
                    continue

            # Handle output folders
            if amc_done:
                Helper.save_text(amc_done, os.path.join(PROCESSED_DIR, "processed_amc.txt"))
                Helper.copy_pdfs_to_folder(PROCESSED_DIR, amc_done)
                print(PROCESSED_DIR)
                logger.warning(f"{len(amc_done)} AMC(s) processed.")

            if amc_not_done:
                Helper.save_text(amc_not_done, os.path.join(FAILED_DIR, "failed_amc.txt"))
                Helper.copy_pdfs_to_folder(FAILED_DIR, amc_not_done)
                print(FAILED_DIR)
                logger.warning(f"{len(amc_not_done)} AMC(s) failed.")

            if os.path.exists(amc_path):
                shutil.rmtree(amc_path, ignore_errors=True)
                logger.warning(f"Deleted input folder: {amc_path}")

            logger.warning("Program Completed.")
            # mail.end("FS main.py program completed")
            cleanup_logger(logger)

        known_folders.update(new_folders)
        print("[WATCHER] No new folders found. Sleeping...", flush=True)
        time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        print("[WATCHER] Stopped by user.")
        break
    except Exception as e:
        print(f"[WATCHER ERROR] {e}")
        time.sleep(CHECK_INTERVAL)
