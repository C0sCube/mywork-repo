import sys, os, json, traceback, logging, io
from datetime import datetime
from app.config_loader import load_config_once, get_config, restore_config
from app.utils import *
from app.util_class_registry import CLASS_REGISTRY
import warnings
from pandas.errors import SettingWithCopyWarning

# UTF-8 for console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Suppress warnings
warnings.simplefilter("ignore", category=SettingWithCopyWarning)
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

# === Config Load ===
output_folder = f"APR25_{datetime.now().strftime('%Y%m%d')}"
load_config_once(output_folder=output_folder)
CONFIG = get_config()


logger = Helper.setup_logger(log_dir=CONFIG["output_path"])
error_log_path = os.path.join(CONFIG["output_path"], CONFIG["output"]["error_log"])

# === Pipeline Start ===
logger.info("Running main.py")
mutual_fund = Helper.get_amc_paths(CONFIG["amc_path"])
amc_not_done = []

for amc_id, class_name in CLASS_REGISTRY.items():
    logger.info(f"Running for: {class_name}")
    try:
        fund_name, path = mutual_fund[amc_id]
        obj = class_name(fund_name, amc_id, path)
    except Exception as e:
        logger.exception(f"[Key Error] {amc_id}")
        amc_not_done.append(amc_id)
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
        Helper.save_json(dfs,save_path)
        logger.info(f"File Saved At: {save_path}")

    except Exception as e:
        logger.exception(f"[Pipeline Error] {fund_name} ({class_name})")
        amc_not_done.append(fund_name)
        continue

# === Save Errors ===
if amc_not_done:
    with open(error_log_path, 'a', encoding='utf-8') as f:
        f.writelines(f"{item}\n" for item in amc_not_done)
    logger.warning(f"{len(amc_not_done)} AMC(s) failed. Details saved to {error_log_path}")

restore_config()
logger.info("Completed main.py execution.")




















# from app.config_loader import load_config_once, get_config,restore_config
# from datetime import datetime
# output_folder = f"FEB25 {datetime.now().strftime("%Y%m%d")}"
# CONFIG = load_config_once(output_folder=output_folder)

# import json, os, traceback
# from app.utils import Helper #utils
# from app.util_class_registry import CLASS_REGISTRY

# CONFIG = get_config()
# mutual_fund = Helper.get_amc_paths(CONFIG["amc_path"])
# error_log_path = os.path.join(CONFIG["output_path"],CONFIG["output"]["error_log"])

# print("Running main.py")

# amc_not_done = []
# for amc_id, class_name in CLASS_REGISTRY.items():
#     print(f"\nRunning for: {str(class_name)}\n{'*' * 20}")
#     try:
#         fund_name, path = mutual_fund[amc_id]
#         obj = class_name(fund_name, amc_id, path) #class_name is actual Class
#     except Exception as e:
#         print(f"[Key Error] No Mutual Fund {class_name}: {e}")
#         # amc_not_done.append(fund_name)

#         with open(error_log_path, "a") as error_file:
#             error_file.write(f"\n[Key Error] {amc_id}:\n")
#             traceback.print_exc(file=error_file)
#         continue  # Skip to next AMC

#     try:# Pipeline starts
#         title, path_pdf = obj.check_and_highlight(path)
#         if not (path_pdf and title):
#             raise ValueError("check_and_highlight returned invalid results.")

#         data = obj.get_data(path_pdf, title)
#         if not data:
#             raise ValueError("get_data returned None.")

#         extracted_text = obj.get_generated_content(data)
#         if not extracted_text:
#             raise ValueError("get_generated_content returned None.")

#         final_text = obj.refine_extracted_data(extracted_text) #flatten=obj.MAIN_MAP['flatten']
#         if not final_text:
#             raise ValueError("refine_extracted_data returned None.")

#         dfs = obj.merge_and_select_data( #select=obj.MAIN_MAP['select'],
#             final_text,
#             map_keys=obj.MAIN_MAP['map'],
#             special_handling=obj.MAIN_MAP['special']
#         )
#         save_path = os.path.join(obj.JSONPATH, obj.FILE_NAME).replace(".pdf", ".json")
#         with open(save_path, 'w') as f:
#             json.dump(dfs, f, indent=2)
#         print(f"File Saved At: {save_path}")

#     except Exception as inner_e:
#         print(f"[Error] Pipeline failed for {class_name}: {inner_e}")
#         amc_not_done.append(fund_name)

#         with open(error_log_path, "w") as error_file:
#             error_file.write(f"\n[Pipeline Error] {fund_name} ({class_name}):\n")
#             traceback.print_exc(file=error_file)
#         continue  # Skip to next AMC


# # Save all failed AMCs
# with open(error_log_path, 'w') as error_file:
#     error_file.writelines(f"{item}\n" for item in amc_not_done)

# restore_config()
# print("\nCompleted main.py execution.")
