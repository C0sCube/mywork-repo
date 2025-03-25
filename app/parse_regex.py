import re
import os
import json, random,string
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
        self.POPULATE_ALL_INDICE = data.get("add_json_headers",[])
        self.METRIC_HEADER = data.get("metrics_headers",{})
       

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
                
    def _map_metric_keys_to_dict(self, text:str):
        for json_key, patterns in self.METRIC_HEADER.items():
            for pattern in patterns:
                regex = re.compile(pattern) 
                if regex.match(text):
                    return json_key
                
    def _populate_all_indices_in_json(self,data:dict):
        for key, value in self.POPULATE_ALL_INDICE.items():
            if key not in data:
                data[key] = value
        return {k:data[k] for k in sorted(data)} #sorted
    
    def _populate_all_metrics_in_json(self, data: dict):
        if not isinstance(data, dict):
            raise TypeError(f"Expected dictionary, got {type(data)}")
            return
        # for key, value in data.items():
        #     if isinstance(value, str) and value.strip().lower() == "na":
        #         data[key] = None
        for key in self.METRIC_HEADER:
            if key not in data:
                data[key] = None
                
        return {k:data[k] for k in sorted(data)} #sorted

    
    def _dummy_block(self,fontz:str,colorz:str):
        return {
                "number": 0,
                "type": 0,
                "bbox": (0,0,0,0), #406.72119140625, 439.4930419921875, 565.697265625, 484.5830383300781
                "lines": [
                    {
                        "spans": [
                            {
                                "size": 30.0,
                                "flags": 20,
                                "font": fontz, #set this
                                "color": colorz, #set this
                                "ascender": 1.0429999828338623,
                                "descender": -0.2619999945163727,
                                "text": f"DUMMY{"".join(random.choices(string.ascii_letters,k=15))}", #garbage val
                                "origin": (round(random.uniform(0, 100), 11), round(random.uniform(0, 100), 11)),
                                "bbox": (0,0,0,0), #406.72119140625,439.4930419921875,565.697265625,462.9830322265625,
                            }
                        ],
                        "wmode": 0,
                        "dir": (1.0, 0.0),
                        "bbox": (0,0,0,0), #406.72119140625,439.4930419921875,565.697265625,462.9830322265625,
                    },
                    
                ],
            }
                


     
            
    