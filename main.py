import sys, os, io
from datetime import datetime
from dateutil.relativedelta import relativedelta
from app.config_loader import load_config_once, get_config, restore_config
from app.utils import *
from app.program_logger import setup_logger
from app.util_class_registry import CLASS_REGISTRY


sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# === Config Load ===
filename = (datetime.now() - relativedelta(months=1)).strftime("%b%y").upper()
currtime = datetime.now().strftime('%Y%m%d')
output_foldername = f"FS_{filename}_{currtime}"
load_config_once(output_folder=output_foldername)
CONFIG = get_config()

root_folder = os.path.join(CONFIG["output_path"], output_foldername)

logger = setup_logger(log_dir=root_folder)

# === Pipeline Start ===
logger.info("Program Execution Started.")
mutual_fund = Helper.get_amc_paths(CONFIG["amc_path"])
amc_not_done = {}

for amc_id, class_name in CLASS_REGISTRY.items():
    logger.info(f"AMC : {amc_id}:{class_name}")
    try:
        fund_name, path = mutual_fund[amc_id]
        obj = class_name(fund_name, amc_id, path)
    except Exception as e:
        logger.exception(f"[Key Error] {amc_id}")
        amc_not_done[fund_name] = path
        continue

    try:
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
        
        save_path = os.path.join(obj.JSONPATH, obj.FILE_NAME).replace(".pdf", ".json")
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        Helper.save_json(dfs,save_path)
        logger.info(f"File '{obj.FILE_NAME.replace(".pdf", ".json")}' Saved.")

    except Exception as e:
        logger.exception(f"[Pipeline Error] {fund_name}({class_name})")
        amc_not_done[fund_name] = path
        continue

# === Save Errors ===
if amc_not_done:
    failed_amc_folder = os.path.join(CONFIG["output_path"], CONFIG["output"]['failed'])
    Helper.save_text(amc_not_done,os.path.join(failed_amc_folder, "uncompleted_amc.txt"))
    Helper.copy_pdfs_to_folder(failed_amc_folder,amc_not_done)
    logger.warning(f"{len(amc_not_done)} AMC(s) failed. Details saved to {root_folder}")

# === Restore Defaults ===
restore_config()
Helper.delete_file_by_suffix(base_folder=CONFIG["amc_path"])
logger.info("Program Completed.")

