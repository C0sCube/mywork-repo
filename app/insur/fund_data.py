import re, os,sys, camelot#type:ignore
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import fitz #type:ignore
from datetime import datetime
from dateutil.relativedelta import relativedelta #type: ignore


from app.insur.parse_pdf import ReadrIns
from app.parse_table import *
from app.logger import get_global_logger, log_exceptions
from app.utils import Helper


class GrandInsrData:
    def __init__(self, config: str):

        fund_config = config
        self.PARAMS = fund_config.get("PARAMS", {})
        self.REGEX = fund_config.get("REGEX", {})
        self.FUND_NAME = fund_config.get("AMC_NAME", "")
        self.SELECTKEYS = fund_config.get("SELECTKEYS", {})
        self.MERGEKEYS = fund_config.get("MERGEKEYS", {})
        self.CLONEKEYS = fund_config.get("CLONEKEYS", [])
        self.PROMOTEKEYS = fund_config.get("PROMOTE_KEYS", {})
        self.IMP_DATA = fund_config.get("IMP_DATA", {})
        self.PREV_KEY_DATA = fund_config.get("PRE_DATA_SELECT", [])
        # self.DUPLICATE_FUNDS = fund_config.get("DUPLICATE_MUTUAL_FUNDS", {})
        self.SPECIAL_FUNCTIONS = fund_config.get("SPECIAL_FUNCTIONS", {})
        self.PATTERN = {
            "primary": fund_config.get("PATTERN_TO_FUNCTION", {}),
            "secondary": fund_config.get("SECONDARY_PATTERN_TO_FUNCTION", {}),
            "tertiary": fund_config.get("TERTIARY_PATTERN_TO_FUNCTION", {}),
        }
        self.MAIN_MAP = fund_config.get("MAIN_MAP", {})
        
        #mutual fund data
        # self.MUTUAL_FUND_DATA = fund_config.get("Z_MUTUAL_FUND_DATA",{})
        
        self.LOGGER = get_global_logger()
        self.UTILS = Helper()
        
    #extract 
    def _extract_dummy_data(self,main_key:str,data):
        return {main_key:data}
    
    def _extract_str_data(self, main_key: str, data: list):
        return {main_key: " ".join(data)}

    def _extract_scheme_non_esc_data(self,main_key:str,data:list, pattern:str):
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
        patterns = [r"(\b{start}\b)\s*((?:(?!\b{end}\b).)*)\s*(\b{end}\b|$)".format(start=start, end=end)
            for start, end in zip(mention_start, mention_end)]


        final_dict = {}
        scheme_data = " ".join(data) if isinstance(data,list) else data
        unique_set = set()
        for pattern in patterns:
            if matches:= re.findall(pattern, scheme_data, re.MULTILINE):
                for match in matches:
                    key, value, dummy = match[0].strip().lower(),match[1].strip(),match[2]
                    if key not in unique_set:
                        final_dict[key] = value
                        unique_set.add(key)
        return {main_key:final_dict}
    
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
        patterns = [r"(\b{start}\b)\s*((?:(?!\b{end}\b).)*)\s*(\b{end}\b|$)".format(start=start, end=end)
            for start, end in zip(mention_start, mention_end)]


        final_dict = {}
        scheme_data = " ".join(data) if isinstance(data,list) else data
        scheme_data = re.sub(self.REGEX['escape']," ", scheme_data).strip()
        unique_set = set()
        for pattern in patterns:
            if matches:= re.findall(pattern, scheme_data, re.MULTILINE):
                for match in matches:
                    key, value, dummy = match[0].strip().lower(),match[1].strip(),match[2]
                    # print(key)
                    if key not in unique_set:
                        final_dict[key] = value
                        unique_set.add(key)
        return {main_key:final_dict}
    
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
    
    def _extract_findall_select_first_data(self,main_key:str,data,pattern:str):
        generic_data = " ".join(data) if isinstance(data,list) else data
        generic_data = re.sub(self.REGEX['escape'], "", generic_data).strip()

        # print("Hello")
        matches = re.findall(self.REGEX[pattern], generic_data, re.IGNORECASE)
        print(matches)
        if matches:
            value = matches[0]
            # print(value)
            return {main_key:value}
        return {main_key:generic_data}
    
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
        for key,val in zip(keys,values):
            key,val = key.strip(), val.strip()
            if key in final_dict:
                continue
            final_dict[key] = val
        
        # print(final_dict)
        return{main_key:final_dict}
    
    def _extract_offset_data(self, main_key: str, data, pattern: str):
        """
        Extracts key-value pairs from text using regex patterns for keys and values,
        then offsets the mapping so that values are reassigned based on (N+1)/2 logic.
        Handles cases where values > keys by trimming or padding.

        Args:
            main_key (str): The top-level key for the returned dictionary.
            data (list | str): Text or list of strings to search.
            pattern (str): The regex key containing 'key' and 'value' sub-patterns.

        Returns:
            dict: A dictionary with the format {main_key: {key: value}} extracted
                and offset-mapped from the input text.
        """
        final_dict = {}
        metric_data = " ".join(data) if isinstance(data, list) else data
        metric_data = re.sub(self.REGEX["escape"], "", metric_data).strip()

        values = re.findall(self.REGEX[pattern]["value"], metric_data, re.IGNORECASE)
        keys = re.findall(self.REGEX[pattern]["key"], metric_data, re.IGNORECASE)

        n = len(keys)
        m = len(values)

        if n == 0 or m == 0:
            return {main_key: final_dict}

        # normalize lengths: trim or pad values to match keys
        if m > n:
            values = values[:n]  # trim extra values
        elif m < n:
            # pad with None if fewer values
            values.extend([None] * (n - m))

        offset = (n + 1) // 2

        for i, key in enumerate(keys):
            key = key.strip()
            target_index = (i + offset) % n
            val = values[target_index].strip() if values[target_index] else None
            if key not in final_dict:
                final_dict[key] = val

        return {main_key: final_dict}
    
    def _extract_iter_data(self, main_key: str, data, pattern: str):
        """
        Extracts key-value pairs by aligning regex 'key' and 'value' matches by order and position.
        Avoids overwriting duplicate keys; first match is preserved.
        """
        final_dict = {}
        metric_data = " ".join(data) if isinstance(data, list) else data
        metric_data = re.sub(self.REGEX["escape"], "", metric_data).strip()

        key_matches = [(m.group(), m.start()) for m in re.finditer(self.REGEX[pattern]["key"], metric_data, re.IGNORECASE)]
        value_matches = [(m.group(), m.start()) for m in re.finditer(self.REGEX[pattern]["value"], metric_data)]

        val_idx = 0
        for key, key_pos in key_matches:
            key = key.strip()
            if key in final_dict:
                continue  # Skip if already added

            while val_idx < len(value_matches) and value_matches[val_idx][1] < key_pos:
                val_idx += 1

            if val_idx < len(value_matches):
                final_dict[key] = value_matches[val_idx][0].strip()
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
    
    def _extract_benchmark_data(self,main_key:str,data:str,pattern:str):
        bench_data = f"{main_key} {data}"
        bench_data = re.sub(self.REGEX["escape"],"",bench_data).strip()
        if matches:=re.findall(self.REGEX[pattern],bench_data, re.IGNORECASE):
            return {"benchmark_index":matches[0]}
        return{"benchmark_index":f"{main_key} {data}"}
    
    def _extract_date_data(self,main_key:str,data:str,pattern:str):
        date_data = f"{main_key} {data}"
        date_data = re.sub(self.REGEX["escape"],"",date_data).strip()
        if matches:=re.findall(self.REGEX[pattern],date_data, re.IGNORECASE):
            return {"scheme_launch_date":matches[0]}
        return{"scheme_launch_date":f"{main_key} {data}"}
    
    
    def _extract_non_esc_data(self,main_key:str,data,pattern:str):
        benchmark_data = " ".join(data) if isinstance(data,list) else data
        matches = re.findall(self.REGEX[pattern],benchmark_data, re.IGNORECASE)
        return {main_key:matches[0] if matches else ""}
    
    def _extract_date_data(self, main_key:str,data:list, pattern:str):  # GROWW & Edelweiss
        date_data = "".join(main_key)
        matches = re.findall(self.REGEX[pattern],date_data, re.IGNORECASE)
        return {"inception_date": " ".join(matches)}
    
    def _update_benchmark_data(self,main_key:str,bench_data):
        bench_data = " ".join(bench_data) if isinstance(bench_data,list) else bench_data
        bench_data = re.sub(self.REGEX["escape"],"",bench_data,re.IGNORECASE)
        if match:=re.match(self.REGEX["benchmark"],bench_data,re.IGNORECASE):
            return {"benchmark_index":match[0]}
        return {main_key:bench_data}
   
    def _update_date_data(self,main_key:str,data):
        date_data = " ".join(data) if isinstance(data, list) else data
        date_data = re.sub(self.REGEX["escape"],"",date_data,re.IGNORECASE)
        if match := re.findall(self.REGEX["date"],date_data,re.IGNORECASE):
            return {"scheme_launch_date":match[0]}
        return {main_key:date_data}
    
    def _update_bench_sub_data(self,main_key:str,bench_data):
        bench_data = " ".join(bench_data) if isinstance(bench_data,list) else bench_data
        bench_data = re.sub(self.REGEX["escape"],"",bench_data,re.IGNORECASE)
        bench_data = re.sub(self.REGEX["sub"],"",bench_data,re.IGNORECASE)
        # if match:=re.match(self.REGEX["benchmark"],bench_data,re.IGNORECASE):
        #     return {"benchmark_index":match[0]}
        return {main_key:bench_data}

    
    # def _update_manager_data(self, main_key: str, data):
    #     final_list = []
    #     manager_data = " ".join(data) if isinstance(data, list) else data
    #     manager_data = re.sub(self.REGEX["escape"], "", manager_data).strip()
    
    #     names = re.findall(self.REGEX['manager']['name'], manager_data, re.IGNORECASE)
    #     # optional fields
    #     exps  = re.findall(self.REGEX['manager'].get('exp', ""), manager_data, re.IGNORECASE) if 'exp' in self.REGEX['manager'] else []
    #     sinces = re.findall(self.REGEX['manager'].get('since', ""), manager_data, re.IGNORECASE) if 'since' in self.REGEX['manager'] else []
    #     max_len = len(names)
    #     exps   += [""] * (max_len - len(exps))
    #     sinces += [""] * (max_len - len(sinces))

    #     for name, since, exp in zip(names, sinces, exps):
    #         final_list.append(self._return_manager_data(name=name, since=since, exp=exp))

    #     return {main_key: final_list}
    
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
    
    # dynamic function match
    # def _match_with_patterns(self, string: str, data: list, level:str):
    #     # logger = get_logger()
    #     try: 
    #         for pattern, (func_name, regex_key) in self.PATTERN[level].items():
    #             if re.match(pattern, string, re.IGNORECASE):
    #                 func = getattr(self, func_name)  # dynamic function|attribute lookup
    #                 if regex_key:
    #                     return func(string, data, regex_key)
    #                 return func(string, data)
    #     except Exception as e:
    #         self.LOGGER.error(f"_match_with_patterns->{level}->{string}")
    #         self.LOGGER.error(e)
    #         # print(f"ERROR _match_with_patterns->{level}->{string}")
    #     return self._extract_dummy_data(string, data)  # fallback

    # def _special_match_regex_to_content(self, string: str, data):
    #     # logger = get_logger()
    #     try:
    #         for pattern,func_name, in self.SPECIAL_FUNCTIONS.items():
    #             if re.match(pattern,string,re.IGNORECASE):
    #                 func = getattr(self, func_name) #dynamic function|attribute lookup
    #                 return func(string, data)    
    #     except Exception as e:
    #         self.LOGGER.error(f"_match_with_patterns->special")
    #         self.LOGGER.error(e)
    #         # print(f"special_match_with_patterns->{string}")
    #     return self._extract_dummy_data(string, data) #fallback
    
    @log_exceptions()
    def _match_with_patterns(self, string: str, data: list, level: str):
        """
        Dynamically matches regex pattern to method names and invokes them.
        Example: 'entry_load' → self._extract_load_data(...)
        """
        for pattern, (func_name, regex_key) in self.PATTERN[level].items():
            if re.match(pattern, string, re.IGNORECASE):
                func = getattr(self, func_name, None)
                if not func:
                    self.LOGGER.warning(f"[{level}] No method found for {func_name}")
                    return self._extract_dummy_data(string, data)
                return func(string, data, regex_key) if regex_key else func(string, data)
        return self._extract_dummy_data(string, data) #fallback


    @log_exceptions()
    def _special_match_regex_to_content(self, string: str, data):
        """
        Dynamically maps special regex patterns to content handlers.
        Used for handling unique cases defined in SPECIAL_FUNCTIONS.
        """
        for pattern, func_name in self.SPECIAL_FUNCTIONS.items():
            if re.match(pattern, string, re.IGNORECASE):
                func = getattr(self, func_name, None)
                if not func:
                    self.LOGGER.warning(f"[special] No method found for {func_name}")
                    return self._extract_dummy_data(string, data)
                return func(string, data)
        return self._extract_dummy_data(string, data) #fallback

    
    def _apply_special_handling(self, temp: dict) -> dict: #brother function of _special_match_regex_to_content 
        updated = temp.copy()
        for head, content in temp.items():
            result = self._special_match_regex_to_content(head, content)
            if result:
                updated.update(result)
        return updated

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
    
    # def _update_duplicate_fund_data(self, data: dict):
    #     final_data = data.copy()
    #     remove_fund = []
    #     for fund, content in data.items():
    #         clean_fund = self.UTILS._normalize_alphanumeric(fund)
    #         for regex, mutual_funds in self.DUPLICATE_FUNDS.items():
    #             matches = re.findall(regex, clean_fund, re.IGNORECASE)
    #             if matches:
    #                 print(f"match found: {regex} -> {fund}")
    #                 remove_fund.append(fund)
    #                 for dup_fund in mutual_funds:
    #                     if dup_fund not in final_data:
    #                         content["main_scheme_name"] = dup_fund
    #                         final_data[dup_fund] = content
    #                 break
        
    #     for fund in remove_fund:
    #         final_data.pop(fund, None)
            
    #     return final_data

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
        })
        
class BaseAMC(ReadrIns, GrandInsrData):
    @log_exceptions()
    def __init__(self, config: dict, regex:dict, path: str):
        GrandInsrData.__init__(self, config)
        ReadrIns.__init__(self, self.PARAMS,regex,path)




class AdityaBirlaINSR(BaseAMC): pass
class BajajLifeINSR(BaseAMC):pass
class BandhanLifeINSR(BaseAMC):pass
class AgeasLifeINSR(BaseAMC):pass
class AvivaLifeINSR(BaseAMC):pass
class ICICILifeINSR(BaseAMC):pass
class BhartiAxaLifeINSR(BaseAMC):pass
class CanaraHSBCLifeINSR(BaseAMC):pass
class EdelweissLifeINSR(BaseAMC):pass
class GeneraliLifeINSR(BaseAMC):pass
class HDFCLifeINSR(BaseAMC):pass
class IndiaFirstLifeINSR(BaseAMC):pass
class KotakLifeINSR(BaseAMC):pass
class LICINSR(BaseAMC):pass
class ShriramLifeINSR(BaseAMC):pass
class StarLifeINSR(BaseAMC):pass
class TataLifeINSR(BaseAMC):pass
class DigitLifeINSR(BaseAMC):pass
class ParmericaLifeINSR(BaseAMC):pass
class IndusNipponLifeINSR(BaseAMC):pass
class PNBLifeINSR(BaseAMC):pass
class ShriramINSR(BaseAMC):pass
class AxisMaxINSR(BaseAMC):pass
class SBILifeINSR(BaseAMC):pass
