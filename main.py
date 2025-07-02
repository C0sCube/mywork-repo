import os,sys,io,json,time,shutil
from datetime import datetime
from app.config_loader import load_config_once, get_config
from app.utils import *
from app.program_logger import setup_logger
from app.util_class_registry import CLASS_REGISTRY


print("FS_JSON_PARSE main.py Running ...", flush=True)

# === Watcher Setup ===
with open("paths.json", "r") as file:
    CONFIG = json.load(file)

WATCH_PATH = CONFIG["amc_path"]
CHECK_INTERVAL = 10  # seconds

known_folders = set(os.listdir(WATCH_PATH))
print(f"[WATCHER] Watching for new folders in: {WATCH_PATH}", flush=True)

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

while True:
    try:
        current_folders = set(os.listdir(WATCH_PATH))
        new_folders = current_folders - known_folders

        for new_folder in new_folders:
            folder_path = os.path.join(WATCH_PATH, new_folder)
            if not os.path.isdir(folder_path):
                continue

            print(f"[WATCHER] New folder detected: {new_folder}")
            output_foldername = f"FS_{new_folder.upper()}_{datetime.now().strftime('%Y%m%d')}"

            load_config_once(output_folder=output_foldername)
            CONFIG = get_config()
            print(CONFIG["output_path"])
            OUTPUT_ROOT = os.path.join(CONFIG["output_path"], output_foldername)
            logger = setup_logger(log_dir=OUTPUT_ROOT)

            logger.info(f"\nProgram Execution Started for: {new_folder}")
            amc_path = os.path.join(CONFIG["amc_path"], new_folder)
            mutual_fund = Helper.get_amc_paths(amc_path)
            amc_done = {}

            for amc_id, class_name in CLASS_REGISTRY.items():
                try:
                    fund_name, path = mutual_fund[amc_id]
                except KeyError as e:
                    logger.error(f"{amc_id} Corresponding FS not attatched. Skiped")
                    continue
                try:
                    logger.warning(f"AMC : {amc_id}:{class_name}")
                    obj = class_name(fund_name, amc_id, path)
                    title, path_pdf = obj.check_and_highlight(path)
                    if not (path_pdf and title):
                        raise ValueError("check_and_highlight returned invalid results.")

                    data = obj.get_data(path_pdf, title)
                    if not data:
                        raise ValueError("get_data returned None.")

                    extracted_text = obj.get_generated_content(data)
                    if not extracted_text:
                        raise ValueError("get_generated_content returned None.")

                    final_text = obj.refine_extracted_data(extracted_text)
                    if not final_text:
                        raise ValueError("refine_extracted_data returned None.")

                    dfs = obj.merge_and_select_data(final_text)

                    save_path = os.path.join(OUTPUT_ROOT, "json", obj.FILE_NAME).replace(".pdf", ".json")
                    os.makedirs(os.path.dirname(save_path), exist_ok=True)
                    Helper.save_json(dfs, save_path)
                    logger.warning(f"File '{obj.FILE_NAME.replace('.pdf', '.json')}' Saved.")
                    amc_done[fund_name] = path

                except Exception:
                    logger.exception(f"[Pipeline Error] {fund_name}({class_name})")
                    continue

            Helper.delete_file_by_suffix(base_folder=amc_path)
            
            amc_not_done = {v[0]: v[1] for k, v in mutual_fund.items() if v[0] not in amc_done}  # fund_name : path

            # Save failed
            if amc_not_done:
                failed_path = os.path.join(OUTPUT_ROOT, "failed")
                os.makedirs(failed_path, exist_ok=True)
                Helper.save_text(amc_not_done, os.path.join(OUTPUT_ROOT, "failed_amc.txt"))
                Helper.copy_pdfs_to_folder(failed_path, amc_not_done)
                logger.warning(f"{len(amc_not_done)} AMC(s) failed.")

            # Save processed
            if amc_done:
                processed_path = os.path.join(OUTPUT_ROOT, "processed")
                os.makedirs(processed_path, exist_ok=True)
                Helper.save_text(amc_done, os.path.join(OUTPUT_ROOT, "processed_amc.txt"))
                Helper.copy_pdfs_to_folder(processed_path, amc_done)
                logger.warning(f"{len(amc_done)} AMC(s) done.")

            shutil.rmtree(amc_path,ignore_errors=True)
            logger.warning(f"Deleted empty input folder: {amc_path}")
            
            #zip + send mail
            zip_filename = f"{output_foldername}.zip"
            zip_path = Helper.zip_output_folder(OUTPUT_ROOT, zip_filename,exclude_folders =("processed", "failed"))
            Helper.send_email_report(processed=len(amc_done), failed=len(amc_not_done), attachment=Path(zip_path))

            logger.warning("Program Completed.")

        known_folders = current_folders
        print("[WATCHER] No new folders found. Sleeping...", flush=True)
        time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        print("[WATCHER] Stopped by user.")
        break
    except Exception as e:
        print(f"[WATCHER ERROR] {e}")
        time.sleep(CHECK_INTERVAL)
