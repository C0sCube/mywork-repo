import re
import os
import json
from dateutil import parser #type:ignore

PATH = os.path.join(os.getcwd(),"data\\config\\regex.json")

class FundRegex():
    
    def __init__(self, path = PATH):
        self.config_path = path
        
        try:
            if not os.path.exists(self.config_path):
                raise FileNotFoundError(f"Config file not found: {self.config_path}")
            with open(self.config_path,'r') as file:
                data = json.load(file)
        except Exception as e:
            print(f'Error: {e}')
        
        self.HEADER_PATTERNS = data.get("header_patterns", {})
        self.STOP_WORDS = data.get("stop_words", [])
        self.JSON_HEADER = data.get("json_headers",{})
       

    @staticmethod
    def extract_date(text: str):
        try:
            return parser.parse(text).strftime(r"%y%m%d")
        except Exception as e:
            print(f"\n{e}")
            return text

    def header_mapper(self, text: str)->str:
        text = re.sub(r"[^\w\s]+", "", text).strip()
        for replacement, patterns in self.HEADER_PATTERNS.items():
            try:
                if isinstance(patterns, list):
                    for pattern in patterns:
                        if re.match(f"^{pattern}.*", text, re.IGNORECASE):
                            return replacement
                else:
                    if re.match(patterns, text, re.IGNORECASE):
                        return replacement
            except Exception as e:
                print(f"\n{e}")
        return text
    
    def select_imp_headers(self, text:str)->str:
        text = re.sub(r"[^\w\s]+", "", text).strip()
        for pattern in self.SELECTKEYS:
            if re.match(f"^{pattern}.*",text, re.IGNORECASE):
                return True
        return False
    
    def __clean_key(self,key: str) -> str:
        
        key = re.sub(r"[^\w\s]", "", key)
        key = re.sub(r"\s+", "_", key)
        return key.strip().lower()

    def transform_keys(self, data:dict)->dict:
        """ lowercase_ all the keys"""
        if isinstance(data, dict):
            return {self.__clean_key(key): self.transform_keys(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self.transform_keys(item) if isinstance(item, dict) else item for item in data]
        else:
            return data
        
    
    def flatten_dict(self,data:dict, parent_key='', sep='.'):
        flattened = {}

        for key, value in data.items():
            new_key = f"{parent_key}{sep}{key}" if parent_key else key

            if isinstance(value, dict):  
                # Recursively flatten nested dictionaries
                flattened.update(self.flatten_dict(value, new_key, sep))
            elif isinstance(value, list):
                # Keep lists untouched
                flattened[new_key] = value
            else:
                flattened[new_key] = value

        return flattened
    
    def _map_json_keys_to_dict(self, text:str):
        for json_key, patterns in self.JSON_HEADER.items():
            for pattern in patterns:
                regex = re.compile(pattern) 
                if regex.match(text):
                    return json_key
                


     
            
    