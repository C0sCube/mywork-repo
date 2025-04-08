import json, os
PATHS_CONFIG = os.path.join(os.getcwd(),'paths.json')
with open(PATHS_CONFIG,'r') as file:
    PATH = json.load(file)
    
from app.fund_data import *
from app.params_handler import *
from app.utils import Helper

mutual_fund = Helper.get_fund_paths(PATH['dirs']['fund_path'])

with open(os.path.join(os.getcwd(),PATH["configs"]['regex']),'r') as file:
    class_mapper = json.load(file)['main_mapper']

print("Main File Running!!")
not_done = []

for amc_name,class_name in class_mapper.items():
    print(f"\nRunning for AMC:{amc_name}")
    print(f"\n----------------------------------------------------\n")
    try:
        object = eval(class_mapper[amc_name])(PATHS_CONFIG,amc_name)
        path = mutual_fund[amc_name]
        title = object.get_relevant_pages(path)
        data = object.get_data(path,title)
        extracted_text = object.get_generated_content(data)
        final_text = object.refine_extracted_data(extracted_text, flatten=object.MAIN_MAP['flatten'])
        dfs = object.merge_and_select_data(final_text, select=object.MAIN_MAP['select'], map= object.MAIN_MAP['map'])
        Helper.quick_json_dump(dfs, object.JSONPATH)
    except Exception as e:
        print(f"\n{e}")
        not_done.append(amc_name)
        continue
    print("\nFinish")
    
with open("amc_not_completed.txt",'w') as file:
    file.writelines(f"{item}\n" for item in not_done)