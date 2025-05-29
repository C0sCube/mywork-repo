import re, os,json,sys, json5,ocrmypdf,io,pytesseract, inspect #type:ignore
from app.parse_pdf import Reader
from logging_config import logger
import fitz #type:ignore
from datetime import datetime
from dateutil.relativedelta import relativedelta #type: ignore

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.config_loader import *
conf = get_config()

PARAMS_PATH = os.path.join(conf["base_path"],conf["configs"]['params'])
class GrandFundData:
    
    def __init__(self,fund_name:str,amc_id:str):
        with open(PARAMS_PATH, "r") as file:
            config = json5.load(file)

        fund_config = config.get(amc_id, {}) #paramters.json5

        #amc indicators
        self.FUND_NAME = fund_name
        self.PARAMS = fund_config.get("PARAMS", {})
        self.REGEX = fund_config.get("REGEX", {})
        
        self.SELECTKEYS = fund_config.get("SELECTKEYS",{})
        self.MERGEKEYS = fund_config.get("MERGEKEYS",{})
        self.CLONEKEYS = fund_config.get("CLONEKEYS",[])
        self.COMBINEKEYS = fund_config.get("COMBINEKEYS",{})
        self.PROMOTEKEYS = fund_config.get("PROMOTE_KEYS",{})
        
        self.IMP_DATA = fund_config.get("IMP_DATA",{})
        self.PREV_KEY_DATA = fund_config.get("PRE_DATA_SELECT",[])
        self.SPECIAL_FUNCTIONS = fund_config.get("SPECIAL_FUNCTIONS",{})
        
        self.PATTERN = {
            "primary":fund_config.get("PATTERN_TO_FUNCTION", {}),
            "secondary":fund_config.get("SECONDARY_PATTERN_TO_FUNCTION",{}),
            "tertiary":fund_config.get("TERTIARY_PATTERN_TO_FUNCTION",{})
        }
        self.MAIN_MAP = fund_config.get("MAIN_MAP",{})
        
    #extract 
    def _extract_dummy_data(self,main_key:str,data):
        return {main_key:data}
    
    def _extract_scheme_data(self,main_key:str,data:list, pattern:str):
        """
            Extracts key-value pairs from text using regex spans between keyword pairs.
            Args:
                main_key (str): Top-level key for the returned dictionary.
                data (list | str): Input text data.
                pattern (str): Key to fetch start-end regex keywords from self.REGEX.
            Returns:
                dict: {main_key: {keyword: extracted_text}}
        """

        regex_ = self.REGEX[pattern] #list
        mention_start = regex_[:-1]
        mention_end = regex_[1:]

        # patterns = [r"(\b{start}\b)\s*(.+?)\s*(\b{end}\b|$)".format(start=start, end=end)
        #     for start, end in zip(mention_start, mention_end)]
        patterns = [r"(\b{start}\b)\s*((?:(?!\b{end}\b).)*)\s*(\b{end}\b|$)".format(start=start, end=end)
            for start, end in zip(mention_start, mention_end)]


        final_dict = {}
        scheme_data = " ".join(data) if isinstance(data,list) else data
        scheme_data = re.sub(self.REGEX['escape'],"", scheme_data).strip()
        unique_set = set()
        for pattern in patterns:
            if matches:= re.findall(pattern, scheme_data, re.MULTILINE):
                for match in matches:
                    key, value, dummy = match[0].strip().lower(),match[1].strip(),match[2]
                    if key not in unique_set:
                        final_dict[key] = value
                        unique_set.add(key)
        return {main_key:final_dict}
    
    def _extract_str_data(self, main_key: str, data: list):
        return {main_key: " ".join(data)}
    
    def _extract_whitespace_data(self, main_key:str,data, pattern:str):
        """
            Extracts values or key-value pairs from text using regex.
            Args:
                main_key (str): Top-level key for the returned dict.
                data (list | str): Input text to search.
                pattern (str): Regex key for matching patterns.
            Returns:
                dict: {main_key: value or {key: value}} based on match structure.
        """
        final_dict = {}
        generic_data = " ".join(data) if isinstance(data,list) else data
        generic_data = re.sub(self.REGEX['escape'], "", generic_data).replace(" ","").strip()
      
        matches = re.findall(self.REGEX[pattern], generic_data, re.IGNORECASE)
        for match in matches:
            if isinstance(match, str):
                return {main_key: match}
            elif len(match) == 2:
                key, value = match
                final_dict[key.strip()] = value.strip()
            elif len(match) == 3:
                key,v1,v2 = match
                final_dict[key.strip()] = v1.strip()
                    
        return {main_key:final_dict}
    
    def _extract_generic_data(self, main_key: str, data, pattern: str):
        """
            Extracts values or key-value pairs from text using regex.
            Args:
                main_key (str): Top-level key for the returned dict.
                data (list | str): Input text to search.
                pattern (str): Regex key for matching patterns.
            Returns:
                dict: {main_key: value or {key: value}} based on match structure.
        """
        final_dict = {}
        generic_data = " ".join(data) if isinstance(data,list) else data
        generic_data = re.sub(self.REGEX['escape'], "", generic_data).strip()
      
        matches = re.findall(self.REGEX[pattern], generic_data, re.IGNORECASE)
        for match in matches:
            if isinstance(match, str):
                return {main_key: match}
            elif len(match) == 2:
                key, value = match
                final_dict[key.strip()] = value.strip()
            elif len(match) == 3:
                key,v1,v2 = match
                final_dict[key.strip()] = v1.strip()
                    
        return {main_key:final_dict}
    
    def _extract_metric_data(self,main_key:str, data,pattern:str):
        """
            Extracts key-value pairs from text using regex patterns for keys and values.
            Args:
                main_key (str): The top-level key for the returned dictionary.
                data (list | str): Text or list of strings to search.
                pattern (str): The regex key containing 'key' and 'value' sub-patterns.
            Returns:
                dict: A dictionary with the format {main_key: {key: value}} extracted from the input text.
        """

        final_dict = {}
        metric_data = " ".join(data) if isinstance(data,list) else data
        metric_data = re.sub(self.REGEX["escape"],"",metric_data).strip()
        
        values = re.findall(self.REGEX[pattern]["value"],metric_data,re.IGNORECASE)
        keys = re.findall(self.REGEX[pattern]["key"],metric_data,re.IGNORECASE)
        for k,v in zip(keys,values):
            final_dict[k.strip()] = v.strip()
        return{main_key:final_dict}
    
    def _extract_iter_data(self, main_key: str, data, pattern: str):
        """
        Extracts key-value pairs by aligning regex 'key' and 'value' matches by order and position.
        """
        final_dict = {}
        metric_data = " ".join(data) if isinstance(data, list) else data
        metric_data = re.sub(self.REGEX["escape"], "", metric_data).strip()

        key_matches = [(m.group(), m.start()) for m in re.finditer(self.REGEX[pattern]["key"], metric_data, re.IGNORECASE)]
        value_matches = [(m.group(), m.start()) for m in re.finditer(self.REGEX[pattern]["value"], metric_data)]

        val_idx = 0
        for key, key_pos in key_matches:
            # find the next value that comes AFTER this key
            while val_idx < len(value_matches) and value_matches[val_idx][1] < key_pos:
                val_idx += 1
            if val_idx < len(value_matches):
                final_dict[key.strip()] = value_matches[val_idx][0].strip()
                val_idx += 1

        return {main_key: final_dict}

    def _extract_load_data(self,main_key:str,data:list, pattern:str):
        """
            Extracts entry and exit load values from the given text using a regex pattern.
            Args:
                main_key (str): Top-level key for the returned dictionary.
                data (list | str): Input text or list of strings to search.
                pattern (str): Regex key used to match entry and exit load values.
            Returns:
                dict: A dictionary in the format {main_key: {'entry_load': str, 'exit_load': str}}.
        """
    
        load_data = " ".join(data) if isinstance(data,list) else data
        # load_data = re.sub(self.REGEX['escape'], "", load_data).strip()
        final_dict = {'entry_load':"","exit_load":""}
        if matches:= re.findall(self.REGEX[pattern],load_data.strip(), re.IGNORECASE):
            for match in matches:
                entry_,exit_ = match 
            final_dict['entry_load'], final_dict['exit_load'] = entry_.strip(),exit_.strip()
        return {main_key:final_dict}
     
    def _extract_amt_data(self,main_key:str, data, pattern:str):
        """
            Extracts amount-related data from the given text using a regex pattern.
            Args:
                main_key (str): Top-level key for the returned dictionary.
                data (list | str): Input text or list of strings to process.
                pattern (str): Regex key used to extract 'amt' and 'thereafter' values.
            Returns:
                dict: A dictionary in the format {main_key: {'amt': str, 'thraftr': str}}.
        """
        amt_data = " ".join(data) if isinstance(data,list) else data
        amt_data = re.sub(self.REGEX['escape'],"",amt_data).strip()
        final_dict = {'amt':"",'thraftr':""}
        if matches:= re.findall(self.REGEX[pattern],amt_data,re.IGNORECASE):
            amt,thraftr = matches[0]
            final_dict['amt'], final_dict['thraftr'] = amt,thraftr
        return {main_key:final_dict}
    
    def _extract_manager_data(self, main_key: str, data, pattern: str):
        """
            Extracts fund manager details such as name, designation, experience, and since-date from the given text.
            Args:
                main_key (str): Top-level key for the returned dictionary.
                data (list | str): Input text or list of strings to process.
                pattern (str): Regex key containing the 'pattern' and corresponding 'fields' 
                            (e.g., name, desig, exp, since in variable order).
            Returns:
                dict: A dictionary in the format {main_key: [manager_info, ...]}, 
                    where each manager_info is built using _return_manager_data(**fields).
        """
        # print("running manager data")
        final_list = []
        manager_data = " ".join(data) if isinstance(data, list) else data
        manager_data = re.sub(self.REGEX['escape'], "", manager_data).strip()

        pattern_info = self.REGEX[pattern]
        regex_pattern = pattern_info['pattern']
        field_names = pattern_info['fields']

        if matches := re.findall(regex_pattern, manager_data, re.IGNORECASE):
            # print(matches)
            for match in matches:
                if isinstance(match, str):
                    match = (match,)
                record = {field_names[i]: match[i] if i < len(match) else "" for i in range(len(field_names))} #kwargs
                final_list.append(self._return_manager_data(**record))
        # print(final_list)
        return {main_key: final_list}
    
    def _extract_lump_data(self, main_key: str, data, pattern:list):
        """
            Extracts minimum and additional lump sum investment amounts from the given text using a regex pattern.
            Args:
                main_key (str): Top-level key for the returned dictionary.
                data (list | str): Input text or list of strings to process.
                pattern (str): Regex key used to extract minimum and additional amount pairs.
            Returns:
                dict: A dictionary in the format {main_key: {'min_amt': str, 'add_amt': str}}.
                    If no valid matches are found, both values will be empty strings.
        """

        load_data = " ".join(data) if isinstance(data, list) else data
        load_data = re.sub(self.REGEX['escape'], "", load_data).strip()
        final_dict = {"min_amt": {}, "add_amt": {}}

        matches = re.findall(self.REGEX[pattern], load_data, re.IGNORECASE)
        if not matches:
            return {main_key: final_dict}

        for match in matches:
            min_amt, add_amt = match
            if not min_amt.strip() and not add_amt.strip():
                continue
            final_dict['min_amt'],final_dict['add_amt'] = min_amt, add_amt
        return {main_key: final_dict}

    def _extract_bench_data(self,main_key:str,data,pattern:str):
        data = " ".join(data) if isinstance(data,list) else data
        benchmark_data = re.sub(self.REGEX['escape'],"",data).strip()
        matches = re.findall(self.REGEX[pattern],benchmark_data, re.IGNORECASE)
        return {main_key:matches[0] if matches else ""}
    
    def _extract_date_data(self, main_key:str,data:list, pattern:str):  # GROWW & Edelweiss
        date_data = "".join(main_key)
        matches = re.findall(self.REGEX[pattern],date_data, re.IGNORECASE)
        return {"inception_date": " ".join(matches)}
    
    
    # dynamic function match
    def _match_with_patterns(self, string: str, data: list, level:str):
        try: 
            for pattern, (func_name, regex_key) in self.PATTERN[level].items():
                if re.match(pattern, string, re.IGNORECASE):
                    func = getattr(self, func_name)  # dynamic function|attribute lookup
                    if regex_key:
                        return func(string, data, regex_key)
                    return func(string, data)
        except Exception as e:
            logger.error(e)
            return

        return self._extract_dummy_data(string, data)  # fallback

    def _special_match_regex_to_content(self, string: str, data):
        try:
            for pattern,func_name, in self.SPECIAL_FUNCTIONS.items():
                if re.match(pattern,string,re.IGNORECASE):
                    func = getattr(self, func_name) #dynamic function|attribute lookup
                    return func(string, data)    
        except Exception as e:
            logger.error(e)
            return
        return self._extract_dummy_data(string, data) #fallback
   
   
   # CRUD dict operations
    def _merge_fund_data(self, data: dict):
        if not isinstance(data, dict):
            return data  # cuz ALL data stored as dict

        for new_key, patterns in self.MERGEKEYS.items():
            keys_to_merge = [key for key in data if any(re.search(pattern, key, re.IGNORECASE) for pattern in patterns)] #match regex to key
            values = [data[key] for key in keys_to_merge if key in data] #heterogenous

            if all(isinstance(v, list) for v in values): #list + list
                merged_value = []
                for v in values:
                    merged_value.extend(v)
            elif all(isinstance(v, dict) for v in values): #dict + dict
                merged_value = {}
                for v in values:
                    merged_value.update(v)
            else: #string + dict
                merged_value = {}
                for key in keys_to_merge:
                    if key in data:
                        if isinstance(data[key], dict):
                            merged_value.update(data[key])
                        else:
                            merged_value[key] = data[key]
            
            for key in keys_to_merge:
                data.pop(key, None)
            if merged_value:
                data[new_key] = merged_value  
        return data

    def _clone_fund_data(self, data: dict):
        for clone_key, regex_pattern in self.CLONEKEYS.items():  
            pattern = re.compile(regex_pattern)
            for key in data:
                if pattern.match(key):
                    data[clone_key] = data[key]
                    break
        return data
    
    def _promote_key_from_dict(self,data:dict):
        for section_key, promote_map in self.PROMOTEKEYS.items():
            if section_key not in data:
                continue

            for new_key, pattern_str in promote_map.items():
                pattern = re.compile(pattern_str, re.IGNORECASE)
                for key, val in data[section_key].items():
                    if pattern.match(key):
                        data[new_key] = val
                        del data[section_key][key]
                        break
        return data
    
    def _combine_fund_data(self, data: dict):
        if not isinstance(data, dict):
            return data

        for new_key, keys_to_combine in self.MERGEKEYS.items():
            values = [data[key] for key in keys_to_combine if key in data]
            if not values:
                continue
            combined_value = []
            for val in values:
                if isinstance(val, list):combined_value.extend(val)
                else:combined_value.append(val)
                
            for key in keys_to_combine:
                data.pop(key, None)

            data[new_key] = combined_value  

        return data
    
    def _get_prev_text(self,key:str):
        for pattern in self.PREV_KEY_DATA:
            if re.match(pattern, key,re.IGNORECASE):
                return True
        return False


    # clean + other
    def _select_by_regex(self, data:dict):
        finalData = {}
        for key, value in data.items():
            if any(re.match(pattern, key, re.IGNORECASE) for pattern in self.SELECTKEYS):
                finalData[key] = value
        return finalData
    
    def _return_manager_data(self, since = "",name = "",desig= "",exp = ""):
        return {
            "managing_fund_since":since.title().strip(),
            "name": name.title().strip(),
            "qualification": desig.title().strip(),
            "total_exp": exp.title().strip()
        }
    
    def _update_imp_data(self,data:dict,main_scheme:str, pgn:list):
        return data.update({
            "amc_name":self.IMP_DATA['amc_name'],
            "main_scheme_name":main_scheme,
            "monthly_aaum_date": (datetime.today().replace(day=1) - relativedelta(days=1)).strftime("%Y%m%d"),
            "page_number":pgn,
            "mutual_fund_name":self.IMP_DATA['mutual_fund_name'],
            "file_name":""
        })
#1 <>
class ThreeSixtyOne(Reader,GrandFundData):   
    def __init__(self, fund_name:str,amc_id:str,path:str):
        GrandFundData.__init__(self,fund_name,amc_id) 
        Reader.__init__(self, self.PARAMS,amc_id,path) 

#2 
class BajajFinServ(Reader,GrandFundData):  
    def __init__(self, fund_name:str,amc_id:str,path:str):
        GrandFundData.__init__(self,fund_name,amc_id) 
        Reader.__init__(self, self.PARAMS,amc_id,path) 
#3 <>
class Bandhan(Reader,GrandFundData):  
   def __init__(self, fund_name:str,amc_id:str,path:str):
        GrandFundData.__init__(self,fund_name,amc_id) 
        Reader.__init__(self, self.PARAMS,amc_id,path) 
#4
class BankOfIndia(Reader,GrandFundData):   
   def __init__(self, fund_name:str,amc_id:str,path:str):
        GrandFundData.__init__(self,fund_name,amc_id) 
        Reader.__init__(self, self.PARAMS,amc_id,path) 
#5 <>
class BarodaBNP(Reader,GrandFundData):
   def __init__(self, fund_name:str,amc_id:str,path:str):
        GrandFundData.__init__(self,fund_name,amc_id) 
        Reader.__init__(self, self.PARAMS,amc_id,path) 
#6 
class Canara(Reader,GrandFundData):
    
    def __init__(self, fund_name:str,amc_id:str,path:str):
        GrandFundData.__init__(self,fund_name,amc_id) 
        Reader.__init__(self, self.PARAMS,amc_id,path) 
    
    def _update_manager_data(self,main_key:str,manager_data):
        nsample, msample, esample = [], [], []
        nlength = 0
        value = " ".join(manager_data.values()) if isinstance(manager_data,dict) else manager_data
        nsample = re.findall(self.REGEX['manager']['name'], value, re.IGNORECASE)
        esample = re.findall(self.REGEX['manager']['exp'], value, re.IGNORECASE)
        msample = re.findall(self.REGEX['manager']['since'], value, re.IGNORECASE)
        
        nlength = len(nsample)
        msample += [""] * abs(nlength - len(msample))
        esample += [""] * abs(nlength - len(esample))
        
        # print(value)
        # print(nsample,esample,msample)
        
        final_list = [self._return_manager_data(since=m,name=n,exp=e)for n, m, e in zip(nsample, msample, esample)]
        return {main_key:final_list}

    def _update_benchmark_data(self,main_key:str,bench_data):
        bench_data = " ".join(bench_data) if isinstance(bench_data,list) else bench_data
        if match:=re.match(self.REGEX["benchmark"],bench_data,re.IGNORECASE):
            return {main_key:match[0]}
        return {main_key:bench_data}
#7
class DSP(Reader,GrandFundData):
    def __init__(self, fund_name:str,amc_id:str,path:str):
        GrandFundData.__init__(self,fund_name,amc_id) 
        Reader.__init__(self, self.PARAMS,amc_id,path)  

#8 <> 
class Edelweiss(Reader,GrandFundData):
    def __init__(self, fund_name:str,amc_id:str,path:str):
        GrandFundData.__init__(self,fund_name,amc_id) 
        Reader.__init__(self, self.PARAMS,amc_id,path) 
#9 <>
class FranklinTempleton(Reader,GrandFundData):
   def __init__(self, fund_name:str,amc_id:str,path:str):
        GrandFundData.__init__(self,fund_name,amc_id) 
        Reader.__init__(self, self.PARAMS,amc_id,path)  

#10 
class HDFC(Reader,GrandFundData):
    def __init__(self, fund_name:str,amc_id:str,path:str):
        GrandFundData.__init__(self,fund_name,amc_id) 
        Reader.__init__(self, self.PARAMS,amc_id,path) 
    
    def _update_manager_data(self, main_key: str, data):
        DATE_PATTERN = r"([A-Za-z]+\s*\d+),"
        NAME_PATTERN = r"([A-Za-z]+\s[A-Za-z]+)"
        EXP_PATTERN = r"over (\d+)"
        YEAR_PATTERN = r"(\d{4})"

        manager_data = " ".join(data) if isinstance(data,list) else data
        manager_data = re.sub(self.REGEX["escape"],"",manager_data).strip()
        manager_data = re.sub(r"[^A-Za-z0-9\s\-\(\).,]+|Name|Since|Total|Exp|years", "", manager_data).strip()

        experience_years = re.findall(EXP_PATTERN, manager_data, re.IGNORECASE)
        dates = re.findall(DATE_PATTERN, manager_data, re.IGNORECASE)[:len(experience_years)]
        years = re.findall(YEAR_PATTERN, manager_data, re.IGNORECASE)[:len(experience_years)]
        names = re.findall(NAME_PATTERN, manager_data, re.IGNORECASE)[:len(experience_years)]
        
        managing_since = [f"{date}, {year}" for date, year in zip(dates, years)]
        experience_list = [f"{exp} years" for exp in experience_years]
        final_list = [
            self._return_manager_data(name=name,since=since,exp=exp)
            for since, exp, name in zip(managing_since, experience_list, names)
        ]
        
        return {main_key:final_list}    

    def _update_benchmark_data(self,main_key:str,data):
        return {"benchmark_index":" ".join(data.values())}
#11
class GROWW(Reader,GrandFundData):
    def __init__(self, fund_name:str,amc_id:str,path:str):
        GrandFundData.__init__(self,fund_name,amc_id) 
        Reader.__init__(self, self.PARAMS,amc_id,path)  
#12 <>
class Helios(Reader,GrandFundData):
    def __init__(self, fund_name:str,amc_id:str,path:str):
        GrandFundData.__init__(self,fund_name,amc_id) 
        Reader.__init__(self, self.PARAMS,amc_id,path) 

#13 
class HSBC(Reader,GrandFundData):
    def __init__(self, fund_name:str,amc_id:str,path:str):
        GrandFundData.__init__(self,fund_name,amc_id) 
        Reader.__init__(self, self.PARAMS,amc_id,path) 
        
    def _update_date_data(self,main_key:str,data):
        if matches:=re.findall(self.REGEX["date"],data, re.IGNORECASE):
            return {main_key:matches[0]}
    def _update_benchmark_data(self,main_key:str,data):
        data=re.sub(self.REGEX["benchmark"],"", data, re.IGNORECASE).strip()
        if matches:= re.findall(self.REGEX["benchmark2"],data,re.IGNORECASE):
            return {main_key:matches[0]}
        return {main_key:data}
#14
class ICICI(Reader,GrandFundData):
    def __init__(self, fund_name:str,amc_id:str,path:str):
        GrandFundData.__init__(self,fund_name,amc_id) 
        Reader.__init__(self, self.PARAMS,amc_id,path) 
        
    def _update_metric_data(self,main_key:str,data):
        if isinstance(data["std_dev"],str) and isinstance(data["port_turnover_ratio"],str):
            data["std_dev"], data["port_turnover_ratio"] = data["port_turnover_ratio"], data["std_dev"]
        return {main_key:data}
#15 <>
class Invesco(Reader,GrandFundData): 
    def __init__(self, fund_name:str,amc_id:str,path:str):
        GrandFundData.__init__(self,fund_name,amc_id) 
        Reader.__init__(self, self.PARAMS,amc_id,path) 
#16 <>
class ITI(Reader,GrandFundData):
    def __init__(self, fund_name:str,amc_id:str,path:str):
        GrandFundData.__init__(self,fund_name,amc_id) 
        Reader.__init__(self, self.PARAMS,amc_id,path) 
#17 <>
class Kotak(Reader,GrandFundData): 
    def __init__(self, fund_name:str,amc_id:str,path:str):
        GrandFundData.__init__(self,fund_name,amc_id) 
        Reader.__init__(self, self.PARAMS,amc_id,path) 
#18
class LIC(Reader,GrandFundData): 
    
    def __init__(self, fund_name:str,amc_id:str,path:str):
        GrandFundData.__init__(self,fund_name,amc_id) 
        Reader.__init__(self, self.PARAMS,amc_id,path) 
        
    def _update_manager_data(self, main_key: str, data):
        # print("hi")
        final_list = []
        manager_data = " ".join(data) if isinstance(data,list) else data
        manager_data =re.sub(self.REGEX["escape"], "", manager_data).strip()
        n = re.findall(self.REGEX['manager']['name'], manager_data, re.IGNORECASE)
        e = re.findall(self.REGEX['manager']['exp'], manager_data, re.IGNORECASE)
        # print(n,e)
        adjust = lambda target, lst: target[:len(lst)] + ([target[-1]] * abs(len(target) - len(lst)) if lst else [""])
        n = adjust(n,e)
        for name,exp in zip(n,e):
            final_list.append(self._return_manager_data(name=name,exp=exp))
        return {main_key: final_list}
    
    def _extract_manager_data(self, main_key: str, data,pattern:str):
        # print("hi")
        final_list = []
        manager_data = " ".join(data) if isinstance(data,list) else data
        manager_data =re.sub(self.REGEX["escape"], "", manager_data).strip()
        n = re.findall(self.REGEX['manager']['name'], manager_data, re.IGNORECASE)
        e = re.findall(self.REGEX['manager']['exp'], manager_data, re.IGNORECASE)
        # print(n,e)
        adjust = lambda target, lst: target[:len(lst)] + ([target[-1]] * abs(len(target) - len(lst)) if lst else [""])
        n = adjust(n,e)
        for name,exp in zip(n,e):
            final_list.append(self._return_manager_data(name=name,exp=exp))
        return {main_key: final_list}

#19 <>
class MahindraManu(Reader,GrandFundData):
    
    def __init__(self, fund_name:str,amc_id:str,path:str):
        GrandFundData.__init__(self,fund_name,amc_id) 
        Reader.__init__(self, self.PARAMS,amc_id,path)  
#20 <>
class MIRAE(Reader,GrandFundData):
    def __init__(self, fund_name:str,amc_id:str,path:str):
        GrandFundData.__init__(self,fund_name,amc_id) 
        Reader.__init__(self, self.PARAMS,amc_id,path) 

class MIRAEPassive(Reader,GrandFundData):
    def __init__(self, fund_name:str,amc_id:str,path:str):
        GrandFundData.__init__(self,fund_name,amc_id) 
        Reader.__init__(self, self.PARAMS,amc_id,path)  
#21 <>
class MotilalOswal(Reader,GrandFundData): 
    def __init__(self, fund_name:str,amc_id:str,path:str):
        GrandFundData.__init__(self,fund_name,amc_id) 
        Reader.__init__(self, self.PARAMS,amc_id,path) 

class MotilalOswalPassive(Reader,GrandFundData): 
    def __init__(self, fund_name:str,amc_id:str,path:str):
        GrandFundData.__init__(self,fund_name,amc_id) 
        Reader.__init__(self, self.PARAMS,amc_id,path)  
#22 <>
class NAVI(Reader,GrandFundData): 
    
    def __init__(self, fund_name:str,amc_id:str,path:str):
        GrandFundData.__init__(self,fund_name,amc_id) 
        Reader.__init__(self, self.PARAMS,amc_id,path) 
    
    def _extract_benchmark_data(self,main_key:str,data:str,pattern:str):
        bench_data = f"{main_key} {data}"
        bench_data = re.sub(self.REGEX["escape"],"",bench_data).strip()
        if matches:=re.findall(self.REGEX[pattern],bench_data, re.IGNORECASE):
            return {"benchmark_index":matches[0]}
        return{"benchmark_index":f"{main_key} {data}"}
    
class NAVIPassive(Reader,GrandFundData): 
    
    def __init__(self, fund_name:str,amc_id:str,path:str):
        GrandFundData.__init__(self,fund_name,amc_id) 
        Reader.__init__(self, self.PARAMS,amc_id,path) 
    
    def _extract_benchmark_data(self,main_key:str,data:str,pattern:str):
        bench_data = f"{main_key} {data}"
        bench_data = re.sub(self.REGEX["escape"],"",bench_data).strip()
        if matches:=re.findall(self.REGEX[pattern],bench_data, re.IGNORECASE):
            return {"benchmark_index":matches[0]}
        return{"benchmark_index":f"{main_key} {data}"}
#23 <>
class Nippon(Reader,GrandFundData):
    
    def __init__(self, fund_name:str,amc_id:str,path:str):
        GrandFundData.__init__(self,fund_name,amc_id) 
        Reader.__init__(self, self.PARAMS,amc_id,path)  
#24
class NJMF(Reader,GrandFundData):
   
    def __init__(self, fund_name:str,amc_id:str,path:str):
        GrandFundData.__init__(self,fund_name,amc_id) 
        Reader.__init__(self, self.PARAMS,amc_id,path) 
        
    def _update_manager_data(self,main_key:str,manager_data):
        nsample, msample, esample = [], [], []
        value = " ".join(manager_data) if isinstance(manager_data,list) else manager_data
        nsample = re.findall(self.REGEX['manager']['name'], value, re.IGNORECASE)
        esample = re.findall(self.REGEX['manager']['exp'], value, re.IGNORECASE)
        msample = re.findall(self.REGEX['manager']['since'], value, re.IGNORECASE)
        final_list = [self._return_manager_data(since=m,name=n,exp=e)for n, m, e in zip(nsample, msample, esample)]
        return {main_key:final_list}
    
    def _update_benchmark_data(self,main_key:str,data):
        return {"benchmark_index":" ".join(data.values())}
#25
class OldBridge(Reader,GrandFundData):
    def __init__(self, fund_name:str,amc_id:str,path:str):
        GrandFundData.__init__(self,fund_name,amc_id) 
        Reader.__init__(self, self.PARAMS,amc_id,path)  

#26
class PGIM(Reader, GrandFundData):
    
    def __init__(self, fund_name:str,amc_id:str,path:str):
        GrandFundData.__init__(self,fund_name,amc_id) 
        Reader.__init__(self, self.PARAMS,amc_id,path) 
        
#27
class PPFAS(Reader,GrandFundData):
    
    def __init__(self, fund_name:str,amc_id:str,path:str):
        GrandFundData.__init__(self,fund_name,amc_id) 
        Reader.__init__(self, self.PARAMS,amc_id,path)  
#28
class QuantMF(Reader,GrandFundData): 
    def __init__(self, fund_name:str,amc_id:str,path:str):
        GrandFundData.__init__(self,fund_name,amc_id) 
        Reader.__init__(self, self.PARAMS,amc_id,path) 
        
    def _generate_aum_data(self,main_key:str,data):
        text = ""
        # print(f"Function Running: {inspect.currentframe().f_code.co_name}")
        with fitz.open(self.PDF_PATH) as doc:
            if not data:
                return {main_key:data}
            
            for page_number in data:
                if page_number < 0 or page_number >= len(doc):
                    continue
                page = doc[page_number]
                text += page.get_text("text", clip=self.REGEX["aaum"]['coord']).strip()
                # print(text)
            if matches:=re.findall(self.REGEX["aaum"]['regex'],text,re.IGNORECASE):
                # print(matches)
                return {"monthly_aaum_value":matches[0]}        
        return  {main_key:data}
#29 
class Quantum(Reader,GrandFundData): 
    def __init__(self, fund_name:str,amc_id:str,path:str):
        GrandFundData.__init__(self,fund_name,amc_id) 
        Reader.__init__(self, self.PARAMS,amc_id,path)  
#30 <>
class Samco(Reader, GrandFundData):
    
    def __init__(self, fund_name:str,amc_id:str,path:str):
        GrandFundData.__init__(self,fund_name,amc_id) 
        Reader.__init__(self, self.PARAMS,amc_id,path)  
#31
class SBI(Reader, GrandFundData): #OCR
    
    def __init__(self, fund_name:str,amc_id:str,path:str):
        GrandFundData.__init__(self,fund_name,amc_id) 
        Reader.__init__(self, self.PARAMS,amc_id,path) 
    
    def _update_manager_data(self, main_key: str, data):
        final_list = []
        manager_data = " ".join(data) if isinstance(data,list) else data
        manager_data =re.sub(self.REGEX["escape"], "", manager_data).strip()
        n = re.findall(self.REGEX['manager']['name'], manager_data, re.IGNORECASE)
        e = re.findall(self.REGEX['manager']['exp'], manager_data, re.IGNORECASE)
        s = re.findall(self.REGEX['manager']['since'], manager_data, re.IGNORECASE)
        
        adjust = lambda target, lst: target[:len(lst)] + ([target[-1]] * abs(len(target) - len(lst)) if lst else [""])
        n,s = adjust(n,e),adjust(s,e)
        for name,since,exp in zip(n,s,e):
            final_list.append(self._return_manager_data(name=name,since=since,exp=exp))
        return {main_key: final_list}

#32
class SBIPassive(Reader, GrandFundData):
    
    def __init__(self, fund_name:str,amc_id:str,path:str):
        GrandFundData.__init__(self,fund_name,amc_id) 
        Reader.__init__(self, self.PARAMS,amc_id,path)  
        
    def _update_manager_data(self,main_key:str,data):
        final_list = []
        manager_data = " ".join(data) if isinstance(data, list) else data
        manager_data = re.sub(self.REGEX['escape'], "", manager_data).strip()
        pattern_info = self.REGEX["manager"]
        regex_pattern = pattern_info['pattern']
        field_names = pattern_info['fields']
        if matches := re.findall(regex_pattern, manager_data, re.IGNORECASE):
            for match in matches:
                if isinstance(match, str):
                    match = (match,)
                record = {field_names[i]: match[i] if i < len(match) else "" for i in range(len(field_names))} #kwargs
                final_list.append(self._return_manager_data(**record))

        return {main_key: final_list}
    

#33 <>
class Sundaram(Reader,GrandFundData):  
    def __init__(self, fund_name:str,amc_id:str,path:str):
        GrandFundData.__init__(self,fund_name,amc_id) 
        Reader.__init__(self, self.PARAMS,amc_id,path)  

#34 <>
class Tata(Reader,GrandFundData):  
    def __init__(self, fund_name:str,amc_id:str,path:str):
        GrandFundData.__init__(self,fund_name,amc_id) 
        Reader.__init__(self, self.PARAMS,amc_id,path)  
#35 <>
class Taurus(Reader,GrandFundData):
    
    def __init__(self, fund_name:str,amc_id:str,path:str):
        GrandFundData.__init__(self,fund_name,amc_id) 
        Reader.__init__(self, self.PARAMS,amc_id,path)  
#36
class Trust(Reader,GrandFundData):
    
   def __init__(self, fund_name:str,amc_id:str,path:str):
        GrandFundData.__init__(self,fund_name,amc_id) 
        Reader.__init__(self, self.PARAMS,amc_id,path)    
#37
class Union(Reader,GrandFundData):   
    def __init__(self, fund_name:str,amc_id:str,path:str):
        GrandFundData.__init__(self,fund_name,amc_id) 
        Reader.__init__(self, self.PARAMS,amc_id,path)   
#38
class UTI(Reader,GrandFundData):
    def __init__(self, fund_name:str,amc_id:str,path:str):
        GrandFundData.__init__(self,fund_name,amc_id) 
        Reader.__init__(self, self.PARAMS,amc_id,path)  
class UTIPassive(Reader,GrandFundData):
    def __init__(self, fund_name:str,amc_id:str,path:str):
        GrandFundData.__init__(self,fund_name,amc_id) 
        Reader.__init__(self, self.PARAMS,amc_id,path)  
#39 <>
class WhiteOak(Reader,GrandFundData):
    
    def __init__(self, fund_name:str,amc_id:str,path:str):
        GrandFundData.__init__(self,fund_name,amc_id) 
        Reader.__init__(self, self.PARAMS,amc_id,path)  
#40
class Zerodha(Reader,GrandFundData):
    
    def __init__(self, fund_name:str,amc_id:str,path:str):
        GrandFundData.__init__(self,fund_name,amc_id) 
        Reader.__init__(self, self.PARAMS,amc_id,path) 
#41 Aditya Birla
class AdityaBirla(Reader,GrandFundData):
    def __init__(self, fund_name:str,amc_id:str,path:str):
        GrandFundData.__init__(self,fund_name,amc_id) 
        Reader.__init__(self, self.PARAMS,amc_id,path)  
        
    def _update_manager_data(self,main_key:str,manager_data):
        nsample, msample, esample = [], [], []
        nlength = 0
        for key, value in manager_data.items():
            if re.search(r"\bfund_manager\b", key, re.IGNORECASE):
                nsample = re.findall(self.REGEX["manager"]["name"], value, re.IGNORECASE)
                nlength = len(nsample)

            elif re.search(r"^managing", key, re.IGNORECASE):
                msample = re.findall(self.REGEX["manager"]["since"], value, re.IGNORECASE)
                
            elif re.search(r"^experience", key, re.IGNORECASE):
                esample = re.findall(self.REGEX["manager"]["exp"], value, re.IGNORECASE)
        nlength = len(nsample)
        msample += [""] * (nlength - len(msample))
        esample += [""] * (nlength - len(esample))

        final_list = [
            self._return_manager_data(since=m,name=n,exp=e)
            for n, m, e in zip(nsample, msample, esample)
        ]

        return {main_key:final_list}
 
#42 Axis Mutual
class AXISMF(Reader,GrandFundData):
    
    def __init__(self, fund_name:str,amc_id:str,path:str):
        GrandFundData.__init__(self,fund_name,amc_id) 
        Reader.__init__(self, self.PARAMS,amc_id,path) 
        
    def _update_manager_data(self, main_key: str, data):
        final_list = []
        manager_data = " ".join(data.values()) if isinstance(data,dict) else data
        manager_data =re.sub(self.REGEX["escape"], "", manager_data).strip()
        n = re.findall(self.REGEX['manager']['name'], manager_data, re.IGNORECASE)
        e = re.findall(self.REGEX['manager']['exp'], manager_data, re.IGNORECASE)
        
        adjust = lambda target, lst: target[:len(lst)] + ([target[-1]] * abs(len(target) - len(lst)) if lst else [""])
        n = adjust(n,e)
        for name,exp in zip(n,e):
            final_list.append(self._return_manager_data(name=name,exp=exp))
        return {main_key: final_list}
    
class AXISMFPassive(Reader,GrandFundData):
    
    def __init__(self, fund_name:str,amc_id:str,path:str):
        GrandFundData.__init__(self,fund_name,amc_id) 
        Reader.__init__(self, self.PARAMS,amc_id,path) 
#43 JMMF
class JMMF(Reader,GrandFundData):
    
    def __init__(self, fund_name:str,amc_id:str,path:str):
        GrandFundData.__init__(self,fund_name,amc_id) 
        Reader.__init__(self, self.PARAMS,amc_id,path) 
        
# 44 Shriram
class Shriram(Reader,GrandFundData):
    
    def __init__(self, fund_name:str,amc_id:str,path:str):
        GrandFundData.__init__(self,fund_name,amc_id) 
        Reader.__init__(self, self.PARAMS,amc_id,path) 


# 45
class AngelOne(Reader,GrandFundData):   
    def __init__(self, fund_name:str,amc_id:str,path:str):
        GrandFundData.__init__(self,fund_name,amc_id) 
        Reader.__init__(self, self.PARAMS,amc_id,path)  
        
#46
class Unifi(Reader,GrandFundData):   
    def __init__(self, fund_name:str,amc_id:str,path:str):
        GrandFundData.__init__(self,fund_name,amc_id) 
        Reader.__init__(self, self.PARAMS,amc_id,path)
    
    def _update_date_data(self, main_key:str,data):  # GROWW & Edelweiss
        date_data = " ".join(data) if isinstance(data,list) else data
        matches = re.findall(self.REGEX["date"],date_data, re.IGNORECASE)
        return {"scheme_launch_date": " ".join(matches)}
    
    def _update_manager_data(self,main_key:str,data):
        final_list = []
        manager_data = " ".join(data) if isinstance(data, list) else data
        manager_data = re.sub(self.REGEX['escape'], "", manager_data).strip()
        pattern_info = self.REGEX["manager"]
        regex_pattern = pattern_info['pattern']
        field_names = pattern_info['fields']
        if matches := re.findall(regex_pattern, manager_data, re.IGNORECASE):
            for match in matches:
                if isinstance(match, str):
                    match = (match,)
                record = {field_names[i]: match[i] if i < len(match) else "" for i in range(len(field_names))} #kwargs
                final_list.append(self._return_manager_data(**record))

        return {main_key: final_list}
    