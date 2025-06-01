import sys, os,json,traceback
from datetime import datetime
from app.config_loader import load_config_once, get_config, restore_config

# Load configuration
output_folder = f"APR25_{datetime.now().strftime('%Y%m%d')}"
CONFIG = load_config_once(output_folder=output_folder)
CONFIG = get_config()

from app.utils import Helper
from app.util_class_registry import CLASS_REGISTRY

class Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for s in self.streams:
            s.write(data)
            s.flush()

    def flush(self):
        for s in self.streams:
            s.flush()

# Setup dual logging: console + file
log_filename = f"run_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
log_file = open(log_filename, "w")
sys.stdout = sys.stderr = Tee(sys.__stdout__, log_file)

mutual_fund = Helper.get_amc_paths(CONFIG["amc_path"])
error_log_path = os.path.join(CONFIG["output_path"], CONFIG["output"]["error_log"])

print("Running main.py")

amc_not_done = []

for amc_id, class_name in CLASS_REGISTRY.items():
    print(f"\nRunning for: {class_name}\n{'*' * 20}")
    try:
        fund_name, path = mutual_fund[amc_id]
        obj = class_name(fund_name, amc_id, path)
    except Exception as e:
        print(f"[Key Error] No Mutual Fund {class_name}: {e}")
        with open(error_log_path, "a") as error_file:
            error_file.write(f"\n[Key Error] {amc_id}:\n")
            traceback.print_exc(file=error_file)
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

        dfs = obj.merge_and_select_data(
            final_text,
            map_keys=obj.MAIN_MAP['map'],
            special_handling=obj.MAIN_MAP['special']
        )

        save_path = os.path.join(obj.JSONPATH, obj.FILE_NAME).replace(".pdf", ".json")
        with open(save_path, 'w') as f:
            json.dump(dfs, f, indent=2)
        print(f"File Saved At: {save_path}")

    except Exception as inner_e:
        print(f"[Error] Pipeline failed for {class_name}: {inner_e}")
        amc_not_done.append(fund_name)
        with open(error_log_path, "a") as error_file:
            error_file.write(f"\n[Pipeline Error] {fund_name} ({class_name}):\n")
            traceback.print_exc(file=error_file)
        continue

# Save failed AMCs
with open(error_log_path, 'a') as error_file:
    error_file.writelines(f"{item}\n" for item in amc_not_done)

restore_config()
log_file.close()
print("\nCompleted main.py execution.")




















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
