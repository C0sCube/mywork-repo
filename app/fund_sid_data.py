import re, os,json,sys, json5,ocrmypdf,io,pytesseract, inspect #type:ignore
from app.parse_sid_pdf import ReaderSIDKIM

import fitz #type:ignore

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.config_loader import get_config
from app.parse_sid_regex import *

# +===========COMPLETE THE DOC STRINGS ===============+


class GrandSidData:
    def __init__(self, amc_id: str):
        config = get_config()
        fund_config = config.sid_params.get(amc_id, {})

        self.PARAMS = fund_config.get("PARAMS", {})
        self.REGEX = fund_config.get("REGEX", {})

        self.SELECTKEYS = fund_config.get("SELECTKEYS", [])
        self.MERGEKEYS = fund_config.get("MERGEKEYS", {})
        self.CLONEKEYS = fund_config.get("CLONEKEYS", {})
        self.COMBINEKEYS = fund_config.get("COMBINEKEYS", {})
        self.PROMOTEKEYS = fund_config.get("PROMOTEKEYS", {})
        self.DELETEKEYS = fund_config.get("DELETEKEYS", [])

        self.IMP_DATA = fund_config.get("IMP_DATA", {})
        self.PREV_KEY_DATA = fund_config.get("PRE_DATA_SELECT", [])
        self.SPECIAL_FUNCTIONS = fund_config.get("SPECIAL_FUNCTIONS", {})

        self.PATTERN = {
            "primary": fund_config.get("PATTERN_TO_FUNCTION", {}),
            "secondary": fund_config.get("SECONDARY_PATTERN_TO_FUNCTION", {}),
            "tertiary": fund_config.get("TERTIARY_PATTERN_TO_FUNCTION", {}),
        }

        self.MAIN_MAP = fund_config.get("MAIN_MAP", {})
        
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
        # scheme_data = re.sub(self.REGEX['escape'],"", scheme_data).strip()
        unique_set = set()
        for pattern in patterns:
            if matches:= re.findall(pattern, scheme_data, re.MULTILINE|re.IGNORECASE):
                for match in matches:
                    key, value, dummy = match[0].strip().lower(),match[1].strip(),match[2]
                    if key not in unique_set:
                        final_dict[key] = value
                        unique_set.add(key)
        return {main_key:final_dict}
    
    def _extract_str_data(self, main_key: str, data: list):
        return {main_key: " ".join(data)}
    
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
        
        if final_dict:           
            return {main_key:final_dict}
        else:
            return{main_key:generic_data}
    
    def _extract_generic_non_escape_data(self, main_key: str, data, pattern: str):
        """
            Extracts values or key-value pairs from text using regex. Escape chars not removed
            Args:
                main_key (str): Top-level key for the returned dict.
                data (list | str): Input text to search.
                pattern (str): Regex key for matching patterns.
            Returns:
                dict: {main_key: value or {key: value}} based on match structure.
        """
        final_dict = {}
        generic_data = " ".join(data) if isinstance(data,list) else data
        # generic_data = re.sub(self.REGEX['escape'], "", generic_data).strip()
      
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
                    
        # return {main_key:final_dict}
        if final_dict:           
            return {main_key:final_dict}
        else:
            return{main_key:generic_data}
            
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
        # print("running manager data")
        final_list = []
        manager_regex = self.REGEX.get(pattern,{})
        if not isinstance(data,list):
            print("_extract_manager_data -> data not list")
            return {"fund_manager":[]}
        
        for manager in data:
            temp = {}
            for key, val in manager.items():
                if not val or key not in manager_regex:
                    continue
                if not isinstance(val,str):
                    if isinstance(val,list):
                        val = " ".join(val)
                    val = str(val)
                clean_val = re.findall(manager_regex[key],val,re.IGNORECASE)
                temp[key] = " ".join(clean_val)
            if temp.get("name"):
                final_list.append(temp)
                
        return {"fund_manager": final_list}
    
    def _return_alloc_data(self, instr = "",min = "",max= "",total = "",risk = ""):
        return {
            "instrument":instr.title().strip(),
            "min": min.title().strip(),
            "max": max.title().strip(),
            "total": total.title().strip(),
            "risk_profile": risk.title().strip()
        }
    
    def _extract_asset_data(self, main_key: str, data, pattern: str):
        if not isinstance(data,list):
            print("_extract_manager_data -> data not list")
            return {main_key:data}
        final_list = []
        asset_params = self.REGEX[pattern]
        asset_order = list(asset_params["order"].split("|"))
        regex = SidKimRegex()
        for content in data:
            content = regex._normalize_alphanumeric_and_symbol(content,"&%")
            if matches := re.findall(asset_params["pattern"],content, re.IGNORECASE):
                for match in matches:
                    record = {asset_order[i]: match[i] if i < len(match) else "" for i in range(len(asset_order))}
                    final_list.append(self._return_alloc_data(**record))
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
            print(f"[ERROR] in _match_with_patterns for: {string}: {e}")
            return self._extract_dummy_data(string, data)

        return self._extract_dummy_data(string, data)  # fallback
    
    # def _match_with_patterns(self, string: str, data: list, level:str):
    #     try: 
    #         for pattern, content in self.PATTERN[level].items():
    #             func_name, regex_key = content.split("~~")
    #             if regex_key == "None":
    #                 regex_key = None
    #             if re.match(pattern, string, re.IGNORECASE):
    #                 func = getattr(self, func_name)  # dynamic function|attribute lookup
    #                 if regex_key:
    #                     return func(string, data, regex_key)
    #                 return func(string, data)
    #     except Exception as e:
    #         print(f"[ERROR] in _match_with_patterns for: {string}: {e}")
    #         return self._extract_dummy_data(string, data)

    #     return self._extract_dummy_data(string, data)  # fallback

    def _special_match_regex_to_content(self, string: str, data):
        try:
            for pattern,func_name, in self.SPECIAL_FUNCTIONS.items():
                if re.match(pattern,string,re.IGNORECASE):
                    func = getattr(self, func_name) #dynamic function|attribute lookup
                    return func(string, data)    
        except Exception as e:
            print(f"[ERROR] in _special_match_regex_to_content {e}")
            return self._extract_dummy_data(string, data)
        return self._extract_dummy_data(string, data) #fallback
    
    def _apply_special_handling(self, temp: dict) -> dict: #brother function of _special_match_regex_to_content 
        updated = temp.copy()
        for head, content in temp.items():
            result = self._special_match_regex_to_content(head, content)
            if result:
                updated.update(result)
        return updated
   
   
   # CRUD Dict Ops
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
    
    def _promote_key_from_dict(self, data: dict):
        for section_key_pattern, promote_map in self.PROMOTEKEYS.items():
            section_regex = re.compile(section_key_pattern, re.IGNORECASE)
            matched_section_key = None
            for key in data:
                if section_regex.search(key):
                    matched_section_key = key
                    break
            # print(matched_section_key)
            if not matched_section_key:
                continue
            for new_key, pattern_str in promote_map.items():
                pattern = re.compile(pattern_str, re.IGNORECASE)
                for key, val in data[matched_section_key].items():
                    if pattern.search(key):
                        # print(key,new_key)
                        data[new_key] = val
                        del data[matched_section_key][key]
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

    def _delete_fund_data_by_key(self, data: dict) -> dict:
        new_data = {}
        for key, value in data.items():
            if not any(re.search(pat, key, re.IGNORECASE) for pat in self.DELETEKEYS):
                new_data[key] = value
        return new_data

                
    # clean + other
    def _select_by_regex(self, data:dict):
        finalData = {}
        for key, value in data.items():
            if any(re.match(pattern, key, re.IGNORECASE) for pattern in self.SELECTKEYS):
                finalData[key] = value
        return finalData
    
    def _update_imp_data(self, data: dict, typez = "sid"):
        updated_data = data.copy()  #optional but keep this
        if typez == "sid":
            updated_data.update({
                "amc_name": self.IMP_DATA.get('amc_name', ''),
                "mutual_fund_name": self.IMP_DATA.get('mutual_fund_name', ''),
                "face_value": self.IMP_DATA.get("face_value", ''),
                "offer_price": self.IMP_DATA.get("offer_price", ''),
            })
        elif typez == "kim":
            updated_data.update({
                "amc_name": self.IMP_DATA.get('amc_name', ''),
                "mutual_fund_name": self.IMP_DATA.get('mutual_fund_name', ''),
                "description":""
                # "face_value": self.IMP_DATA.get("face_value", ''),
                # "offer_price": self.IMP_DATA.get("offer_price", ''),
            })
        else:
            print(f"[ERROR] _update_imp_data wrong or typo for sid/kim")
            return updated_data
        
        return updated_data

class ThreeSixtyOneSIDKIM(ReaderSIDKIM, GrandSidData):
    def __init__(self, amc_id: str, path: str):
        GrandSidData.__init__(self, amc_id)
        ReaderSIDKIM.__init__(self, self.PARAMS, path)

class AdityaBirlaSIDKIM(ReaderSIDKIM, GrandSidData):
    def __init__(self, amc_id: str, path: str):
        GrandSidData.__init__(self, amc_id)
        ReaderSIDKIM.__init__(self, self.PARAMS, path)

class AngelOneSIDKIM(ReaderSIDKIM, GrandSidData):
    def __init__(self, amc_id: str, path: str):
        GrandSidData.__init__(self, amc_id)
        ReaderSIDKIM.__init__(self, self.PARAMS, path)

class AXISMFSIDKIM(ReaderSIDKIM, GrandSidData):
    def __init__(self, amc_id: str, path: str):
        GrandSidData.__init__(self, amc_id)
        ReaderSIDKIM.__init__(self, self.PARAMS, path)

class BajajFinServSIDKIM(ReaderSIDKIM, GrandSidData):
    def __init__(self, amc_id: str, path: str):
        GrandSidData.__init__(self, amc_id)
        ReaderSIDKIM.__init__(self, self.PARAMS, path)

class BandhanSIDKIM(ReaderSIDKIM, GrandSidData):
    def __init__(self, amc_id: str, path: str):
        GrandSidData.__init__(self, amc_id)
        ReaderSIDKIM.__init__(self, self.PARAMS, path)

class BankOfIndiaSIDKIM(ReaderSIDKIM, GrandSidData):
    def __init__(self, amc_id: str, path: str):
        GrandSidData.__init__(self, amc_id)
        ReaderSIDKIM.__init__(self, self.PARAMS, path)

class BarodaBNPSIDKIM(ReaderSIDKIM, GrandSidData):
    def __init__(self, amc_id: str, path: str):
        GrandSidData.__init__(self, amc_id)
        ReaderSIDKIM.__init__(self, self.PARAMS, path)

class CanaraSIDKIM(ReaderSIDKIM, GrandSidData):
    def __init__(self, amc_id: str, path: str):
        GrandSidData.__init__(self, amc_id)
        ReaderSIDKIM.__init__(self, self.PARAMS, path)

class DSPSIDKIM(ReaderSIDKIM, GrandSidData):
    def __init__(self, amc_id: str, path: str):
        GrandSidData.__init__(self, amc_id)
        ReaderSIDKIM.__init__(self, self.PARAMS, path)

class HDFCSIDKIM(ReaderSIDKIM, GrandSidData):
    def __init__(self, amc_id: str, path: str):
        GrandSidData.__init__(self, amc_id)
        ReaderSIDKIM.__init__(self, self.PARAMS, path)

class EdelweissSIDKIM(ReaderSIDKIM, GrandSidData):
    def __init__(self, amc_id: str, path: str):
        GrandSidData.__init__(self, amc_id)
        ReaderSIDKIM.__init__(self, self.PARAMS, path)

class FranklinTempletonSIDKIM(ReaderSIDKIM, GrandSidData):
    def __init__(self, amc_id: str, path: str):
        GrandSidData.__init__(self, amc_id)
        ReaderSIDKIM.__init__(self, self.PARAMS, path)

class GROWWSIDKIM(ReaderSIDKIM, GrandSidData):
    def __init__(self, amc_id: str, path: str):
        GrandSidData.__init__(self, amc_id)
        ReaderSIDKIM.__init__(self, self.PARAMS, path)

class HeliosSIDKIM(ReaderSIDKIM, GrandSidData):
    def __init__(self, amc_id: str, path: str):
        GrandSidData.__init__(self, amc_id)
        ReaderSIDKIM.__init__(self, self.PARAMS, path)

class HSBCSIDKIM(ReaderSIDKIM, GrandSidData):
    def __init__(self, amc_id: str, path: str):
        GrandSidData.__init__(self, amc_id)
        ReaderSIDKIM.__init__(self, self.PARAMS, path)

class ICICISIDKIM(ReaderSIDKIM, GrandSidData):
    def __init__(self, amc_id: str, path: str):
        GrandSidData.__init__(self, amc_id)
        ReaderSIDKIM.__init__(self, self.PARAMS,  path)

class InvescoSIDKIM(ReaderSIDKIM, GrandSidData):
    def __init__(self, amc_id: str, path: str):
        GrandSidData.__init__(self, amc_id)
        ReaderSIDKIM.__init__(self, self.PARAMS,  path)

class ITISIDKIM(ReaderSIDKIM, GrandSidData):
    def __init__(self, amc_id: str, path: str):
        GrandSidData.__init__(self, amc_id)
        ReaderSIDKIM.__init__(self, self.PARAMS,  path)

class JMMFSIDKIM(ReaderSIDKIM, GrandSidData):
    def __init__(self, amc_id: str, path: str):
        GrandSidData.__init__(self, amc_id)
        ReaderSIDKIM.__init__(self, self.PARAMS,  path)

class KotakSIDKIM(ReaderSIDKIM, GrandSidData):
    def __init__(self, amc_id: str, path: str):
        GrandSidData.__init__(self, amc_id)
        ReaderSIDKIM.__init__(self, self.PARAMS,  path)

class LICSIDKIM(ReaderSIDKIM, GrandSidData):
    def __init__(self, amc_id: str, path: str):
        GrandSidData.__init__(self, amc_id)
        ReaderSIDKIM.__init__(self, self.PARAMS,  path)

class MahindraManuSIDKIM(ReaderSIDKIM, GrandSidData):
    def __init__(self, amc_id: str, path: str):
        GrandSidData.__init__(self, amc_id)
        ReaderSIDKIM.__init__(self, self.PARAMS,  path)

class MIRAESIDKIM(ReaderSIDKIM, GrandSidData):
    def __init__(self, amc_id: str, path: str):
        GrandSidData.__init__(self, amc_id)
        ReaderSIDKIM.__init__(self, self.PARAMS,  path)

class MotilalOswalSIDKIM(ReaderSIDKIM, GrandSidData):
    def __init__(self, amc_id: str, path: str):
        GrandSidData.__init__(self, amc_id)
        ReaderSIDKIM.__init__(self, self.PARAMS,  path)

class NAVISIDKIM(ReaderSIDKIM, GrandSidData):
    def __init__(self, amc_id: str, path: str):
        GrandSidData.__init__(self, amc_id)
        ReaderSIDKIM.__init__(self, self.PARAMS,  path)

class NipponSIDKIM(ReaderSIDKIM, GrandSidData):
    def __init__(self, amc_id: str, path: str):
        GrandSidData.__init__(self, amc_id)
        ReaderSIDKIM.__init__(self, self.PARAMS,  path)

class NJMFSIDKIM(ReaderSIDKIM, GrandSidData):
    def __init__(self, amc_id: str, path: str):
        GrandSidData.__init__(self, amc_id)
        ReaderSIDKIM.__init__(self, self.PARAMS,  path)

class OldBridgeSIDKIM(ReaderSIDKIM, GrandSidData):
    def __init__(self, amc_id: str, path: str):
        GrandSidData.__init__(self, amc_id)
        ReaderSIDKIM.__init__(self, self.PARAMS,  path)

class SamcoSIDKIM(ReaderSIDKIM, GrandSidData):
    def __init__(self, amc_id: str, path: str):
        GrandSidData.__init__(self, amc_id)
        ReaderSIDKIM.__init__(self, self.PARAMS,  path)

class PGIMSIDKIM(ReaderSIDKIM, GrandSidData):
    def __init__(self, amc_id: str, path: str):
        GrandSidData.__init__(self, amc_id)
        ReaderSIDKIM.__init__(self, self.PARAMS,  path)

class PPFASSIDKIM(ReaderSIDKIM, GrandSidData):
    def __init__(self, amc_id: str, path: str):
        GrandSidData.__init__(self, amc_id)
        ReaderSIDKIM.__init__(self, self.PARAMS,  path)

class QuantMFSIDKIM(ReaderSIDKIM, GrandSidData):
    def __init__(self, amc_id: str, path: str):
        GrandSidData.__init__(self, amc_id)
        ReaderSIDKIM.__init__(self, self.PARAMS,  path)

class QuantumSIDKIM(ReaderSIDKIM, GrandSidData):
    def __init__(self, amc_id: str, path: str):
        GrandSidData.__init__(self, amc_id)
        ReaderSIDKIM.__init__(self, self.PARAMS,  path)

class SBISIDKIM(ReaderSIDKIM, GrandSidData):
    def __init__(self, amc_id: str, path: str):
        GrandSidData.__init__(self, amc_id)
        ReaderSIDKIM.__init__(self, self.PARAMS,  path)

class ShriramSIDKIM(ReaderSIDKIM, GrandSidData):
    def __init__(self, amc_id: str, path: str):
        GrandSidData.__init__(self, amc_id)
        ReaderSIDKIM.__init__(self, self.PARAMS,  path)

class SundaramSIDKIM(ReaderSIDKIM, GrandSidData):
    def __init__(self, amc_id: str, path: str):
        GrandSidData.__init__(self, amc_id)
        ReaderSIDKIM.__init__(self, self.PARAMS,  path)

class TataSIDKIM(ReaderSIDKIM, GrandSidData):
    def __init__(self, amc_id: str, path: str):
        GrandSidData.__init__(self, amc_id)
        ReaderSIDKIM.__init__(self, self.PARAMS,  path)

class TaurusSIDKIM(ReaderSIDKIM, GrandSidData):
    def __init__(self, amc_id: str, path: str):
        GrandSidData.__init__(self, amc_id)
        ReaderSIDKIM.__init__(self, self.PARAMS,  path)

class TrustSIDKIM(ReaderSIDKIM, GrandSidData):
    def __init__(self, amc_id: str, path: str):
        GrandSidData.__init__(self, amc_id)
        ReaderSIDKIM.__init__(self, self.PARAMS,  path)

class UnionSIDKIM(ReaderSIDKIM, GrandSidData):
    def __init__(self, amc_id: str, path: str):
        GrandSidData.__init__(self, amc_id)
        ReaderSIDKIM.__init__(self, self.PARAMS,  path)

class UTISIDKIM(ReaderSIDKIM, GrandSidData):
    def __init__(self, amc_id: str, path: str):
        GrandSidData.__init__(self, amc_id)
        ReaderSIDKIM.__init__(self, self.PARAMS,  path)

class WhiteOakSIDKIM(ReaderSIDKIM, GrandSidData):
    def __init__(self, amc_id: str, path: str):
        GrandSidData.__init__(self, amc_id)
        ReaderSIDKIM.__init__(self, self.PARAMS,  path)

class ZerodhaSIDKIM(ReaderSIDKIM, GrandSidData):
    def __init__(self, amc_id: str, path: str):
        GrandSidData.__init__(self, amc_id)
        ReaderSIDKIM.__init__(self, self.PARAMS,  path)

class UnifiSIDKIM(ReaderSIDKIM, GrandSidData):
    def __init__(self, amc_id: str, path: str):
        GrandSidData.__init__(self, amc_id)
        ReaderSIDKIM.__init__(self, self.PARAMS,  path)

class JioBlackRockSIDKIM(ReaderSIDKIM, GrandSidData):
    def __init__(self, amc_id: str, path: str):
        GrandSidData.__init__(self, amc_id)
        ReaderSIDKIM.__init__(self, self.PARAMS,  path)
