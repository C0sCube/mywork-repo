import re
import json5 #type:ignore
import os

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
            "MERGEKEYS": []
        }
        self._save_data()
    
    def read_fund_house(self, name):
        return self.data.get(name, f"{name} not found")
    
    def update_fund_house(self, name, key, value):
        if name not in self.data:
            raise ValueError(f"{name} does not exist.")
        if key not in self.data[name]:
            raise ValueError(f"Invalid key {key} for {name}.")
        
        if isinstance(self.data[name][key], dict):
             self.data[name][key].update(value)
        else:
            raise ValueError(f"{key} cannot add")
    
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