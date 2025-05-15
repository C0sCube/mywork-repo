import json, os
from app.config_loader import load_config
from app.fund_data import *
from app.params_handler import *
from app.utils import Helper
from app.vendor_to_user import *

CONFIG = load_config()

mutual_fund = Helper.get_amc_paths(CONFIG["amc_path"])
cls_map_path = os.path.join(CONFIG["base_path"],CONFIG["configs"]["regex"])


print("Running main.py")
with open(cls_map_path,'r') as file: #class for each amc
    class_mapper = json.load(file)['class_mapper']

not_done = []
for amc_id,class_name in class_mapper.items():
    
    vmapper = VendorMapper()
    print(f"\nRunning for:{class_name}\n******************")
    try:
        # print(class_mapper[amc_name])
        fund_name,path = mutual_fund[amc_id]
        object = eval(class_mapper[amc_id])(fund_name,amc_id,path)
        try:
            title, path_pdf = object.check_and_highlight(path)
        except Exception as e:
            print(f"[Error] check_and_highlight failed: {e}")

        try:
            if path_pdf and title:
                data = object.get_data(path_pdf, title)
            else:
                print("[Warning] Skipping get_data due to previous failure.")
        except Exception as e:
            print(f"[Error] get_data failed: {e}")

        try:
            if data:
                extracted_text = object.get_generated_content(data)
            else:
                print("[Warning] Skipping get_generated_content due to missing data.")
        except Exception as e:
            print(f"[Error] get_generated_content failed: {e}")

        try:
            if extracted_text:
                final_text = object.refine_extracted_data(extracted_text, flatten=object.MAIN_MAP['flatten'])
            else:
                print("[Warning] Skipping refine_extracted_data due to missing extracted_text.")
        except Exception as e:
            print(f"[Error] refine_extracted_data failed: {e}")

        try:
            if final_text:
                dfs = object.merge_and_select_data(
                    final_text,
                    select=object.MAIN_MAP['select'],
                    map_keys=object.MAIN_MAP['map'],
                    special_handling=object.MAIN_MAP['special']
                )
            else:
                print("[Warning] Skipping merge_and_select_data due to missing final_text.")
        except Exception as e:
            print(f"[Error] merge_and_select_data failed: {e}")
            
    except Exception as e:
        print(f"\n[Error] Main.py:{e}")
        not_done.append(fund_name)
        continue

    
with open("data\\output\\amc_not_completed.txt",'w') as file:
    file.writelines(f"{item}\n" for item in not_done)