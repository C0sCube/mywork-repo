import re
import os, sys
import json, inspect, json5
from dateutil import parser #type:ignore

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.config_loader import *

conf = get_config()
REGEX_PATH = os.path.join(conf["base_path"],conf["configs"]["sid_regex"])

class SidKimRegex():
    
    def __init__(self, path = REGEX_PATH):
        self.config_path = path
        
        try:
            if not os.path.exists(self.config_path):
                raise FileNotFoundError(f"Config file not found: {self.config_path}")
            with open(self.config_path,'r') as file:
                data = json.load(file)
        except Exception as e:
            print(f'Error: {e}')
        
        #=================GENERAL=================
        self.HEADER_PATTERNS = data.get("header_patterns", {})
        self.STOP_WORDS = data.get("stop_words", [])
        self.MANAGER_STOP_WORDS = re.compile(r'\b(' + '|'.join(map(re.escape, data.get("manager_stop_words","").split(","))) + r')\b', flags=re.IGNORECASE)
        self.ESCAPE = data.get("escape_regex","")
        
        #===================SID===================
        self.SID_HEADER = data.get("sid_json_headers",{})
        self.POPULATE_ALL_SID_INDICE = data.get("add_sid_headers",[])
        
        #===================KIM===================
        self.KIM_HEADER = data.get("kim_json_headers",{})
        self.POPULATE_ALL_KIM_INDICE = data.get("add_kim_headers",[])

    @staticmethod
    def extract_date(text: str):
        try:
            return parser.parse(text).strftime(r"%y%m%d")
        except Exception as e:
            print(f"\n{e}")
            return text

    def header_mapper(self, text: str)->str:
        # print(f"Function Running: {inspect.currentframe().f_code.co_name}")
        text = re.sub(r"[^\w\s]+|\u00b7", "", text).strip()
        # print(text)
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
                print(f"Function Running: {inspect.currentframe().f_code.co_name}\n{e}")
        return text

    def _normalize_key(self,key: str) -> str:
        key = re.sub(r"[^\w\s\.]", "", key)
        key = re.sub(r"\s+", "_", key)
        return key.strip().lower()
    
    def _normalize_whitespace(self,key:str)->str:
        return re.sub(r"\s+", " ", key).strip()

    def _transform_keys(self, data:dict)->dict: #lowercase
        if isinstance(data, dict):
            return {self._normalize_key(key): self._transform_keys(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._transform_keys(item) if isinstance(item, dict) else item for item in data]
        else:
            return data
            
    def _flatten_dict(self,data:dict, parent_key='', sep='.'):
        flattened = {}

        for key, value in data.items():
            new_key = f"{parent_key}{sep}{key}" if parent_key else key

            if isinstance(value, dict):  #recurse
                flattened.update(self._flatten_dict(value, new_key, sep))
            elif isinstance(value, list):
                # Keep lists untouched
                flattened[new_key] = value
            else:
                flattened[new_key] = value

        return flattened
    
    def _map_json_keys_to_dict(self, text:str,typez:str):
        # print(f"To Match: {text}")
        JSON_HEADER = self.SID_HEADER if typez == "sid" else self.KIM_HEADER
        for json_key, patterns in JSON_HEADER.items():
            for pattern in patterns:
                regex = re.compile(pattern)
                if regex.match(text):
                    # print(f"Matched: {json_key}")
                    return json_key
        return text
                
    def _populate_all_indices_in_json(self,data:dict, typez:str):
        POPULATE_ALL_INDICE = self.POPULATE_ALL_SID_INDICE if typez == "sid" else self.POPULATE_ALL_KIM_INDICE
        if not isinstance(data, dict):
            raise TypeError(f"Expected dict, got {type(data)}")
            return
        for key, value in POPULATE_ALL_INDICE.items():
            if key not in data:
                data[key] = value
        return {k:data[k] for k in sorted(data)} #sorted
                
    def _check_replace_type(self,data:dict,fund:str):
        expected_types = {
            "amc_name": str,
            "benchmark_index": str,
            "fund_manager": list,
            "load": dict,
            "main_scheme_name": str,
            "mutual_fund_name": str,
            "suitable_for_investors": str,
            "scheme_objective": str,
            "scheme_code": str,
            "type_of_scheme": str,
            "open_date": str,
            "close_date": str,
            "face_value": str,
            "riskometer_scheme": str,
            "riskometer_benchmark": str,
            "min_addl_amt": str,
            "min_addl_amt_multiple": str,
            "min_amt": str,
            "min_amt_multiple": str,
            "page_number": list,
        }

        changes = {}

        for key, expected_type in expected_types.items():
            if key in data and not isinstance(data[key], expected_type):
                original_type = type(data[key]).__name__
                default_value = expected_type()
                data[key] = default_value
                changes[key] = f"For AMC {fund} -> Replaced {original_type} with {expected_type.__name__}"

        return data
    
    # def _sanitize_fund(self,fund:str,fund_name:str):
        
    #     fund = re.sub(self.ESCAPE, '', fund)
    #     fund = re.sub("\\s+", ' ', fund)
    #     for key,regex in self.MAIN_SCHEME_NAME[fund_name].items():
    #         if re.search(regex, fund, re.IGNORECASE):
    #             print(f"{fund} --> {key}")
    #             fund = key
    #             break
    #     return fund

    def _convert_date_format(self,data, output_format="%Y%m%d"):
        try:
            date_str = data.get("scheme_launch_date","")
            dt = parser.parse(date_str)
            data["scheme_launch_date"] = dt.strftime(output_format)
            return data
        except (ValueError, TypeError): #empty string, str other than date
            return data

    def _convert_year_format(self,data):
        metrics = data.get("metrics",{})
        time_str = metrics["macaulay"]
        year_value = time_str
        if any(x in time_str.lower() for x in ["days", "day","da"]):
            numeric_value = float(re.findall(r"\d+\.?\d*", time_str, re.IGNORECASE)[0])
            year_value = str(numeric_value / 365)
        elif any(x in time_str.lower() for x in ["months", "month","mon","mont"]):
            numeric_value = float(re.findall(r"\d+\.?\d*", time_str, re.IGNORECASE)[0])
            year_value = str(numeric_value / 12.0)
        elif any(x in time_str.lower() for x in ["years", "year","yea","ye"]):
            numeric_value = float(re.findall(r"\d+\.?\d*", time_str, re.IGNORECASE)[0])
            year_value = str(numeric_value)
        return year_value
    
    def _remove_duplicates(self,text):
        if not text:
            return text
        seen = []
        text = text.split(" ")
        for word in text:
            if word not in seen:
                seen.append(word)
        return " ".join(seen)

    
    def _format_fund_manager(self, data):
        fund_managers = data.get("fund_manager", [])
        if not fund_managers:
            return data

        clean_fund_managers = []
        for manager in fund_managers:
            name = manager.get("name", "")
            if not name:
                continue

            # Clean and normalize name
            cleaned_name = self.MANAGER_STOP_WORDS.sub('', name)
            cleaned_name = re.sub("[^A-Za-z\\s]","", cleaned_name,re.IGNORECASE)
            cleaned_name = self._remove_duplicates(cleaned_name)
            cleaned_name = re.sub(r'\s+', ' ', cleaned_name).strip()

            if cleaned_name and len(cleaned_name)>=3:
                manager["name"] = cleaned_name
                clean_fund_managers.append(manager)

        data["fund_manager"] = clean_fund_managers
        return data

    def _format_amt_data(self,data):
        clean_terms = {}
        for term in ["min_amt","min_addl_amt","min_amt_multiple","min_addl_amt_multiple"]:
            content = data.get(term,"")
            content = re.sub(r"[,\s.]+|any","",content,re.IGNORECASE)
            if content:
                clean_terms[term] = content
        data.update(clean_terms)
        
        return data


                

            
     
            
    