import os
import json5 #type:ignore

PARAMS_PATH =  os.path.join(os.getcwd(),"data\\config\\params.json5")

class FundHouseManager:
    
    def __init__(self, path = PARAMS_PATH):
        self.file_path = path
        self.data = self._load_data()
    
    def _load_data(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r') as f:
                return json5.load(f)
        return {}
    
    def _save_data(self):
        with open(self.file_path, 'w') as f:
            json5.dump(self.data, f, indent=4)
    
    def create_fund_house(self, name):
        
        if name in self.data:
            raise ValueError(f"{name} exists")
            return
        
        self.data[name] = {
            "PARAMS": {},
            "REGEX": {},
            "PATTERN_TO_FUNCTION": {},
            "SECONDARY_PATTERN_TO_FUNCTION": {},
            "SELECTKEYS": [],
            "MERGEKEYS": [],
            "COMMENTS":[],
        }
        self._save_data()
    
    def read_fund_house(self, name):
        return self.data.get(name, f"{name} not found")
         
    def update_fund_house(self, name, key, value):
        
        if name not in self.data:
            raise ValueError(f"{name} doesn't exist")

        if key not in self.data[name]:
            self.data[name][key] = value
            self._save_data()
            return  

        if isinstance(self.data[name][key], dict):
            if not isinstance(value, dict):
                raise ValueError(f"Expected dict to update {key}")
            self.data[name][key].update(value)

        elif isinstance(self.data[name][key], list):
            if isinstance(value, list):
                self.data[name][key].extend(value)
            else:
                self.data[name][key].append(value)

        elif isinstance(self.data[name][key], str):
            if not isinstance(value, str):
                raise ValueError(f"Non string value")
            self.data[name][key] = value

        else:
            raise ValueError(f"Unsupported operation for key '{key}' in fund house '{name}'.")

        self._save_data()

        
    def delete_fund_value(self, name, key, value):
        if name not in self.data:
            raise ValueError(f"{name} does not exist")
        if key not in self.data[name]:
            raise ValueError(f"Invalid key {key} for {name}.")
        
        if isinstance(self.data[name][key], dict):
            if value in self.data[name][key]:
                del self.data[name][key][value]  # Remove the specified value
            else:
                raise ValueError(f"{value} not in {key}.")
        else:
            raise ValueError(f"{key} not dict, cannot delete")

        self._save_data()

    
    def delete_fund_house(self, name):
        if name not in self.data:
            raise ValueError(f"{name} does not exist")
        
        del self.data[name]
        self._save_data()
    
    def list_fund_houses(self):
        return list(self.data.keys())
    
    def sort_amc_data(self):
        def recursive_sort(value):
            if isinstance(value, dict):
                return {k: recursive_sort(v) for k, v in sorted(value.items())}
            elif isinstance(value, list):
                return sorted(value, key=str)  # Ensuring consistent sorting
            return value

        self.data = recursive_sort(self.data)
        self._save_data()
    
    def transform_list_to_dict(self, name):
        if name not in self.data:
            raise ValueError(f"{name} does not exist")
        for key in ["fund", "data"]:
            if key in self.data[name].get("PARAMS", {}):
                original_list = self.data[name]["PARAMS"][key]
                transformed_dict = {f"{key}{i+1}": item for i, item in enumerate(original_list)}
                self.data[name]["PARAMS"][key] = transformed_dict

        self._save_data()

class DataStruct:
    
    def __init__(self):
        pass
    
    #first
    final_dic = {
        "metadata": [],
        "records": []
    }
    
    #second
    meta_data = {
        "document_name": "",
        "file_type": "",
        "process_date": ""
    }
    record = {
                "amc_name": "",
                "benchmark_index":[],
                "field_location": [],
                "fund_manager": [],
                "load": [],
                "main_scheme_name": "",
                "metrics": [],
                "min_addl_amt": "",
                "min_addl_multiple":"",
                "min_amt":"",
                "monthly_aaum_date":"",
                "monthly_aaum_value":"",
                "mutual_fund_name": "",
                "scheme_launch_date":""
                
            }
    
    #third  
    fund_manager = {
        "managing_fund_since":"",
        "name": "",
        "qualification": "",
        "total_exp": ""
    }
    load = {
        "type": "",
        "comment": ""
    }   
    metrics= {
        "name":"",
        "value":""
    }    
    field_location = {
      "amc_name": "",
      "benchmark_index": "",
      "count": 0,
      "fund_manager_managing_fund_since": "",
      "fund_manager_name": "",
      "fund_manager_total_exp": "",
      "load_entry": "",
      "load_exit": "",
      "main_scheme_name": "",
      "metrics_beta": "",
      "metrics_port_turnover_ratio": "",
      "metrics_r_squared_ratio": "",
      "metrics_sharpe": "",
      "metrics_std_dev": "",
      "metrics_treynor_ratio": "",
      "min_addl_amt": "",
      "min_addl_amt_multiple": "",
      "min_amt": "",
      "min_amt_multiple": "",
      "monthly_aaum_date": "",
      "monthly_aaum_value": "",
      "mutual_fund_name": "",
      "scheme_launch_date": ""
     }
    
    "PATTERN_TO_FUNCTION",{
        "^investment.*":[
            "_extract_str_data", None
        ],
        "^scheme":[
            "_extract_scheme_data",'scheme'
        ]
    }
    
    
    PARAMS = {
        "fund":{
            "flag":[4,16],
            "regex":"'^Canara.*",
            "size":[12,20],
            "color":[-12371562,-14475488],
        },
        "clip_bbox":[
            [0,115,220,812],
            [220,115,400,812],
        ],
        "data":{
            "size":[8,11],
            "update_size":30.0,
            "font":['Taz-SemiLight'],
            "color":[-12371562]
        },
        "content_size":[
            30.0,
            10.0
        ],
        "countmax_header_check": 15,
        "line_x":180.0,
        "method":"clip",
        "line_side":""
    }