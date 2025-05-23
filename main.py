import json, os
PATHS_CONFIG = os.path.join(os.getcwd(),'paths.json')
with open(PATHS_CONFIG,'r') as file:
    PATH = json.load(file)
    
from app.fund_data import *
from app.params_handler import *
from app.utils import Helper
from app.vendor_to_user import *

mutual_fund = Helper.get_fund_paths(PATH['dirs']['fund_path'])

with open(os.path.join(os.getcwd(),PATH["configs"]['regex']),'r') as file:
    class_mapper = json.load(file)['main_mapper']

print("Running file main.py")
not_done = []

for amc_name,class_name in class_mapper.items():
    
    vmapper = VendorMapper()
    print(f"\nRunning for AMC:{amc_name}\n**********************")
    try:
        # print(class_mapper[amc_name])
        path = mutual_fund[amc_name]
        object = eval(class_mapper[amc_name])(PATHS_CONFIG, amc_name,path)
        title,path_pdf = object.check_and_highlight(path)
        data = object.get_data(path_pdf, title)
        extracted_text = object.get_generated_content(data)
        final_text = object.refine_extracted_data(extracted_text, flatten=object.MAIN_MAP['flatten'])
        dfs = object.merge_and_select_data(final_text, 
                                           select=object.MAIN_MAP['select'], 
                                           map_keys=object.MAIN_MAP['map'], 
                                           special_handling=object.MAIN_MAP['special'])
        
        Helper.quick_json_dump(dfs, object.JSONPATH)

        if not os.path.exists(object.JSONPATH): # if exists
            raise FileNotFoundError(f"Expected output JSON not created: {object.JSONPATH}")

    except Exception as e:
        print(f"\n The Error:{e}")
        not_done.append(amc_name)
        continue

    
with open("amc_not_completed.txt",'w') as file:
    file.writelines(f"{item}\n" for item in not_done)