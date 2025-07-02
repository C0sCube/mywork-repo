import re
import os, sys
import json, random,string, inspect, json5,datetime
from dateutil import parser #type:ignore

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.config_loader import *

class FundRegex():
    
    def __init__(self):
        conf = get_config()
        REGEX_PATH = os.path.join(conf["base_path"],conf["configs"]["regex"])
        self.config_path = REGEX_PATH
        try:
            if not os.path.exists(self.config_path):
                raise FileNotFoundError(f"Config file not found: {self.config_path}")
            with open(self.config_path,'r') as file:
                data = json.load(file)
        except Exception as e:
            print(f'Error: {e}')
        
        #============FACTSHEET===================
        self.HEADER_PATTERNS = data.get("header_patterns", {})
        self.STOP_WORDS = data.get("stop_words", [])
        self.MANAGER_STOP_WORDS = re.compile(r'\b(' + '|'.join(map(re.escape, data.get("manager_stop_words","").split(","))) + r')\b', flags=re.IGNORECASE)
        self.JSON_HEADER = data.get("json_headers",{})
        self.POPULATE_ALL_INDICE = data.get("add_json_headers",[])
        self.METRIC_HEADER = data.get("metrics_headers",{})
        self.FINANCIAL_TERMS = data.get("financial_indices",[])
        self.ESCAPE = data.get("escape_regex","")
        self.MAIN_SCHEME_NAME = data.get("main_scheme_name",{})

    def _header_mapper(self, text: str)->str:
        # print(f"Function Running: {inspect.currentframe().f_code.co_name}")
        text = self._remove_non_word_space_chars(text)
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
    
    def _map_main_and_tabular_data(self, original_df: dict, table_df: dict, mutual_fund: str) -> dict:
        print(f"Function Running: {inspect.currentframe().f_code.co_name}")
        f1_list = []
        for f1 in original_df:
            for f2, c2 in table_df.items():
                f1r = self._normalize_alphanumeric(f1)
                f2r = self._normalize_alphanumeric(f2)
                for _, pattern in self.MAIN_SCHEME_NAME[mutual_fund].items():
                    if re.findall(pattern, f1r, re.IGNORECASE) and re.findall(pattern, f2r, re.IGNORECASE):
                        print(f"Match: original_df ->{f1} table_df -> {f2}")
                        f1_list.append(f1)
                        original_df[f1].update(c2)
                        break
        print(f"UnMatched original_df: {[i for i in original_df if i not in f1_list]}")
        return original_df
    
    def _map_json_keys_to_dict(self, text:str):
        for json_key, patterns in self.JSON_HEADER.items():
            for pattern in patterns:
                regex = re.compile(pattern) 
                if regex.match(text):
                    return json_key
                
    def _map_metric_keys_to_dict(self, text:str):
        text = self._normalize_key_to_alnum_underscore(text)
        for json_key, patterns in self.METRIC_HEADER.items():
            for pattern in patterns:
                regex = re.compile(pattern) 
                if regex.match(text):
                    return json_key
                
    def _populate_all_indices_in_json(self,data:dict):
        if not isinstance(data, dict):
            raise TypeError(f"Expected dict, got {type(data)}")
            return
        for key, value in self.POPULATE_ALL_INDICE.items():
            if key not in data:
                data[key] = value
        return {k:data[k] for k in sorted(data)} #sorted
    
    def _populate_all_metrics_in_json(self, data: dict):
        if not isinstance(data, dict):
            raise TypeError(f"Expected dict, got {type(data)}")
            return
        for key in self.METRIC_HEADER:
            if key not in data:
                data[key] = None
                
        return {k:data[k] for k in sorted(data)} #sorted
    
    def _clean_leading_noise(self,text: str) -> str:
        if not isinstance(text,str):
            return text
        return re.sub(r'^[\s\n\r\t\\:;\-–—•|]+', '', text).strip()
    
    def _normalize_key(self,text: str) -> str:
        if not isinstance(text,str):
            return text
        text = re.sub(r"[^\w\s\.]", "", text)
        text = re.sub(r"\s+", "_", text)
        return text.strip().lower()
    
    def _normalize_key_to_alnum_underscore(self, text: str) -> str:
        if not isinstance(text, str):
            return text
        text = text.strip().lower()
        text = re.sub(r"[^\w]", "_", text)
        text = re.sub(r"__+", "_", text)
        return text.strip("_")

    #match type
    def is_numeric(self,text):
        return bool(re.fullmatch(r'[+-]?(\d+(\.\d*)?|\.\d+)', text))

    def is_alphanumeric(self,text):
        return bool(re.fullmatch(r'[A-Za-z0-9]+', text))

    def is_alpha(self,text):
        return bool(re.fullmatch(r'[A-Za-z]+', text))
        
    def _remove_non_word_space_chars(self,text:str)->str:
        if not isinstance(text,str):
            return text
        text = re.sub("[^\\w\\s]", "", text).strip()
        return text
    
    def _normalize_whitespace(self,text:str)->str:
        if not isinstance(text,str):
            return text
        return re.sub(r"\s+", " ", text).strip()
    
    def _normalize_date(self,text:str)->str:
        if not isinstance(text,str):
            return text
        text = re.sub(r"[^A-Za-z0-9\s\.\/\,\-\\]+"," ",text).strip()
        return self._normalize_whitespace(text)
    
    def _normalize_alphanumeric(self, text: str) -> str:
        if not isinstance(text,str):
            return text
        text = re.sub(r"[^a-zA-Z0-9]+", " ", str(text))
        return re.sub(r"\s+", " ", text).strip().lower()
    
    def _normalize_alpha(self, text: str) -> str:
        if not isinstance(text,str):
            return text
        text = re.sub(r"[^a-zA-Z]+", " ", str(text))
        return re.sub(r"\s+", " ", text).strip().lower()

    def _normalize_numeric(self, text: str) -> str:
        if not isinstance(text,str):
            return text
        text = re.sub(r"[^0-9\.]+", " ", str(text))
        return re.sub(r"\s+", " ", text).strip().lower()

    def _sanitize_fund(self,fund:str,fund_name:str):
        fund = re.sub(self.ESCAPE, '', fund)
        fund = self._normalize_whitespace(fund)
        for key,regex in self.MAIN_SCHEME_NAME[fund_name].items():
            if re.findall(regex,fund,re.IGNORECASE):
                # print(f"{fund} --> {key}")
                fund = key
                break
        return fund
    
    def _to_rgb_tuple(self,color_int):
        c = color_int & 0xFFFFFF
        r = (c >> 16) & 0xFF
        g = (c >> 8) & 0xFF
        b = c & 0xFF
        return (r/255.0, g/255.0, b/255.0)
    
    def _remove_rupee_symbol(self,data:dict):
        # rupee_keys = ["monthly_aaum_value","min_addl_amt","min_addl_amt_multiple","min_amt","min_amt_multiple"]
        # for k,v in data.items():
        #     if k in rupee_keys and isinstance(v,str) and re.match("^\\d",v):
        #         data[k] =f"\u20B9 {v}"         
        # return data   
        clean_keys = ["monthly_aaum_value"]
        for k,v in data.items():
            if k in clean_keys and isinstance(v,str):
                data[k] = re.sub(r"[^\d.,a-zA-Z ]+", "", v)
        return data

    def _convert_date_format(self,data, output_format="%Y%m%d"):
        try:
            date_str = data.get("scheme_launch_date","")
            date_str = self._normalize_date(date_str)
            dt = parser.parse(date_str)
            data["scheme_launch_date"] = dt.strftime(output_format)
            return data
        except (ValueError, TypeError): #empty string, str other than date
            return data
    
    def _remove_duplicates(self,text):
        if not text:
            return text
        seen = []
        text = text.split(" ")
        for word in text:
            word = word.lower().strip()
            if word not in seen:
                seen.append(word)
        return " ".join(seen)

    # def _format_fund_manager(self, data):
    #     fund_managers = data.get("fund_manager", [])
    #     if not fund_managers:
    #         return data

    #     clean_fund_managers = []
    #     for manager in fund_managers:
    #         name = manager.get("name", "")
    #         if not name:
    #             continue

    #         # Clean and normalize name
    #         cleaned_name = self.MANAGER_STOP_WORDS.sub(' ', name)
    #         cleaned_name = self._normalize_alpha(cleaned_name)
    #         cleaned_name = self._remove_duplicates(cleaned_name)
    #         if cleaned_name and len(cleaned_name)>=3:
    #             manager["name"] = cleaned_name.title()
    #             clean_fund_managers.append(manager)

    #     data["fund_manager"] = clean_fund_managers
    #     return data
    
    def _format_fund_manager(self, data):
        fund_managers = data.get("fund_manager", [])
        if not fund_managers:
            return data

        clean_fund_managers = []
        for manager in fund_managers:
            if isinstance(manager, str):
                manager = {"name": manager}
            elif not isinstance(manager, dict):
                continue

            name = manager.get("name", "")
            if not name:
                continue

            cleaned_name = self.MANAGER_STOP_WORDS.sub(' ', name)
            cleaned_name = self._normalize_alpha(cleaned_name)
            cleaned_name = self._remove_duplicates(cleaned_name)
            if cleaned_name and len(cleaned_name) >= 3:
                manager["name"] = cleaned_name.title()
                clean_fund_managers.append(manager)

        data["fund_manager"] = clean_fund_managers
        return data


    def _format_amt_data(self, fund, data):
        if re.search(r"\betf\b", str(fund), re.IGNORECASE):
            for key in ["min_amt", "min_addl_amt", "min_amt_multiple", "min_addl_amt_multiple"]:
                data.pop(key, None)
            return data

        for key in ["min_amt", "min_addl_amt", "min_amt_multiple", "min_addl_amt_multiple"]:
            val = data.get(key, "")
            if isinstance(val, str):
                cleaned = re.sub(r"[,\s.]+", "", val, flags=re.IGNORECASE)
                if cleaned:
                    data[key] = cleaned

        return data


    def _format_metric_data(self, fund,data):
        metric_data = data.get("metrics", {})
        if not isinstance(metric_data, dict) or not metric_data:
            return data

        for metric, value in metric_data.items():
            if not value:
                continue
            value = value.strip()
            if metric == "port_turnover_ratio":
                
                #fund specific
                if "sundaram" in fund.lower():
                    continue
                if re.search(r"times?$", value, re.IGNORECASE):
                    value = re.sub(r"times?$", "", value, flags=re.IGNORECASE).strip()
                    if self.is_numeric(value):
                        num = float(value)
                        value = str(int(num * 100))
                elif value.endswith("%"):
                    value = value.rstrip("%").strip()
                elif self.is_numeric(value):
                    num = float(value)
                    value = str(int(num * 100))
            
            if metric == "std_dev" or metric == "ytm" or metric == "tracking_error":
                if value.endswith("%"):
                    value = value.rstrip("%").strip()
            if metric in ["avg_maturity", "macaulay", "mod_duration"]:
                divide = 1
                val_lower = value.lower()
                if "day" in val_lower:
                    divide = 365
                elif "month" in val_lower:
                    divide = 12
                elif "year" in val_lower:
                    divide = 1

                value = re.sub(r"[^0-9.]+", "", value).strip()

                if self.is_numeric(value):
                    num = float(value)
                    value = str(round(num / divide, 4))

            metric_data[metric] = value
            
        #NA string
        metric_data = {
            k: v for k, v in metric_data.items()
            if not re.fullmatch(r"NA", str(v).strip(), re.IGNORECASE)
        }
        data["metrics"] = metric_data
        return data


    #MAPPER FINSTINCT
    def _format_to_finstinct(self,data,filename):
        scheme_count = len(data)
        final_container = {
            "metadata":{
                "document_name":filename,
                "file_type":"fs",
                "process_date": f"{datetime.datetime.now().strftime('%Y%m%d')}"
            },
            "records":[]
        }
        for key,content in data.items():
            final_container["records"].append({"value":FundRegex.__generate_map_value(scheme_count,content)})
        
        return final_container
    
    @staticmethod
    def __generate_map_value(scheme_count:int,data:dict):
        #dynamically get str , dict and list to map to correct format
        record_value, field_location_keys = {}, []

        page_list = data.get("page_number", [])
        page_number = str(page_list[0] + 1) if page_list else "0"

        for key, data_value in data.items():
            if isinstance(data_value, str):
                if key == "benchmark_index":
                    data_value = FundRegex()._clean_leading_noise(data_value)
                
                record_value[key] = FundRegex()._normalize_whitespace(data_value)
                field_location_keys.append(key)
                

            if key == "metrics" and isinstance(data_value, dict):
                metrics = [{"name": k, "value": str(v)} for k, v in data_value.items() if v]
                record_value[key] = metrics
                field_location_keys.extend([f"metrics_{m['name']}" for m in metrics])

            if key == "load" and isinstance(data_value, list):
                load = []
                for item in data_value:
                    value = item.get("comment", "")
                    value = FundRegex()._clean_leading_noise(value)
                    value = FundRegex()._normalize_whitespace(value)
                    load.append(
                        {
                            "type": item.get("type", ""),
                            "comment": value
                        })
                record_value[key] = load
                field_location_keys.extend([f"load_{l['type'].replace('_load','')}" for l in load])

            if key == "fund_manager" and isinstance(data_value, list) and data_value:
                record_value[key] = data_value
                field_location_keys.extend([f"fund_manager_{k}" for k in data_value[0].keys()])

        # assign page to each key as they are on same page usually
        field_location = {k: page_number for k in field_location_keys}
        field_location["count"] = scheme_count
        record_value["field_location"] = [dict(sorted(field_location.items()))]
        return dict(sorted(record_value.items()))
    
    def _dummy_block(self,fontz:str,colorz:str, count:int):
        num_to_str = {1:"one",2:"two",3:"three",4:"four",5:"five",6:"six",7:"seven",8:"eight",9:"nine"}
        random_val = "".join(random.choices(string.ascii_letters,k=15))
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
                                "text": f"DUMMY{random_val}{num_to_str[count]}", #garbage val
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


                

            
     
            
    