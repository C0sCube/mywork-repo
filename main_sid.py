import os, time, shutil, logging, json
from app.config_loader import Config
from app.utils import Helper
from app.mailer import Mailer
from app.program_logger import get_forever_logger, setup_session_logger
from app.sid_registry import SID_CLASS_REGISTRY

CONFIG = Config()
WATCH_PATH, OUTPUT_PATH = CONFIG.watch_path, CONFIG.output_path
CHECK_INTERVAL = 10

JSON_DIR = os.path.join(OUTPUT_PATH, CONFIG.output["json"])
DAILY_LOG_DIR = os.path.join(OUTPUT_PATH, CONFIG.output["daily_logs"])
SESSION_LOG_DIR = os.path.join(OUTPUT_PATH, CONFIG.output["session_logs"])
FAILED_DIR = os.path.join(OUTPUT_PATH, CONFIG.output["failed"])
PROCESSED_DIR = os.path.join(OUTPUT_PATH, CONFIG.output["processed"])

watch_logger = get_forever_logger("watcher", log_dir=DAILY_LOG_DIR,log_level=logging.WARNING)
watch_logger.notice("SID/KIM JSON PARSE main.py Running ...")

mail = Mailer()
known_folders = set(os.listdir(WATCH_PATH))
watch_logger.info(f"Watching for new PDFs in: {WATCH_PATH}")


def process_amc(amc_id,content,amc_path,logger):
    page_content = {}
    results = {"done": {}, "failed": {}}
    
    try:
        
        logger.info("Trying to read tabular data (xlsx)...")
        df = Helper().get_xlsx_in_folder(amc_path)
        if df is not None:
            page_content = {row[0]: list(row[1:]) for row in df.itertuples(index=False)}
            logger.notice("Tabular data loaded.")
            # logger.info(page_content)
            
    except Exception as e:
        
        logger.warning(f"Tabular data loading failed: {e}")
    
    for typez,fund_name,path in content:
        
        try:
            
            logger.notice(f"Processing {amc_id}:{fund_name}")
            obj = SID_CLASS_REGISTRY[amc_id](amc_id, path)
            dfs,temp_dict = {},{}
            typez = typez.lower()
                        
            fundName = fund_name.replace(".pdf", "").strip()
            if fundName in page_content:
                args = page_content[fundName]
                logger.info(f"Page Data for {fundName} = {args}. ")

            if typez == "sid":

                temp_dict.update(obj.parse_page_zero(args[0]))
                temp_dict.update(obj.parse_scheme_table_data(args[1]))
                temp_dict.update(obj.parse_fund_manager_info(str(args[2])))
                
            elif typez == "kim": temp_dict = obj.parse_KIM_data(pages=args[0], instrument_count=int(args[1]))
            else: raise ValueError(f"For {fund_name} typez is wrong: {typez}")
            
            dataset = obj.refine_data(temp_dict)
            dfs = obj.merge_and_select_data(dataset,sid_or_kim=typez)
            
            if not dfs: raise ValueError("No final merged data.")
            
            save_path = os.path.join(JSON_DIR, f"{fundName}.json")
            Helper.save_json(dfs, save_path)
            
            # with open("temp.json","w+") as file:
            #     json.dump(temp_dict,file)
            # with open("data.json","w+") as file:
            #     json.dump(dataset,file)
            
            logger.save(f"Saved JSON: {save_path}")
            results["done"][fund_name] = path
                    
        except Exception as e:
            
            logger.error(f"[Pipeline Error] {fund_name} | {type(e).__name__}: {e}")
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
            
            for amc_id, _class in SID_CLASS_REGISTRY.items():
                content = mutual_fund.get(amc_id)
                if not content:
                    continue
                
                session_logger.info(f"{amc_id} SID/KIM attached.")
                time.sleep(1)
                watch_logger.info(f"{amc_id} SID/KIM attached.")
                
                result = process_amc(amc_id, content, amc_path, logger=session_logger)
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
            time.sleep(1)
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
