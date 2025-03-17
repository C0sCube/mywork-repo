import re, os,json, json5 #type:ignore
from app.parse_pdf import Reader
from logging_config import logger
import fitz #type:ignore
from datetime import datetime
from dateutil.relativedelta import relativedelta #type: ignore

AMC_PATH = os.path.join(os.getcwd(),"data\\config\\params.json5")
class GrandFundData:
    
    def __init__(self,fund_name:str):
        with open(AMC_PATH, "r") as file:
            config = json5.load(file)
        
        #all amc data
        fund_config = config.get(fund_name, {})
        # print(fund_config)

        #amc indicators
        self.PARAMS = fund_config.get("PARAMS", {})
        self.REGEX = fund_config.get("REGEX", {})
        self.PATTERN_TO_FUNCTION = fund_config.get("PATTERN_TO_FUNCTION", {})
        self.SECONDARY_PATTERN_TO_FUNCTION = fund_config.get("SECONDARY_PATTERN_TO_FUNCTION",{})
        self.TERTIARY_PATTERN_TO_FUNCTION = fund_config.get("TERTIARY_PATTERN_TO_FUNCTION",{})
        self.SELECTKEYS = fund_config.get("SELECTKEYS",{})
        self.MERGEKEYS = fund_config.get("MERGEKEYS",{})
        self.COMBINEKEYS = fund_config.get("COMBINEKEYS",{})
        self.IMP_DATA = fund_config.get("IMP_DATA",{})
        
    #extract 
    def _extract_dummy_data(self,key:str,data):
        return {key:data}
    
    def _extract_scheme_data(self,main_key:str,data:list, pattern:str):
        regex_ = self.REGEX[pattern] #list
        mention_start = regex_[:-1]
        mention_end = regex_[1:]

        patterns = [r"(\b{start}\b)\s*(.+?)\s*(\b{end}\b|$)".format(start=start, end=end)
            for start, end in zip(mention_start, mention_end)]

        final_dict = {}
        scheme_data = " ".join(data)
        scheme_data = re.sub(self.REGEX['escape'],"", scheme_data).strip()
        unique_set = set()
        for pattern in patterns:
            if matches:= re.findall(pattern, scheme_data, re.MULTILINE|re.IGNORECASE):
                for match in matches:
                    key, value, dummy = match[0].strip().lower(),match[1].strip(),match[2]
                    if key not in unique_set:
                        final_dict[key] = value
                        unique_set.add(key)
        return {main_key:final_dict}
    
    def _extract_str_data(self, key: str, data: list):
        return {key: ' '.join(data)}
    
    def _extract_generic_data(self, main_key: str, data, pattern: str):
        final_dict = {}

        generic_data = [data] if isinstance(data,str) else data 
        for text in generic_data:
            text = re.sub(self.REGEX['escape'], "", text).strip()
            matches = re.findall(self.REGEX[pattern], text, re.IGNORECASE)
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

    def _extract_load_data(self,main_key:str,data:list, pattern:str):
        load_data = " ".join(data) if isinstance(data,list) else data
        load_data = re.sub(self.REGEX['escape'], "", load_data).strip()
        final_dict = {}
        if matches:= re.findall(self.REGEX[pattern],load_data.strip(), re.IGNORECASE):
            for match in matches:
                entry_,exit_ = match
            
            final_dict['entry_load'] = entry_
            final_dict['exit_load'] = exit_
        return {main_key:final_dict}
     
    def _extract_amt_data(self,main_key:str, data, pattern:str):

        amt_data = " ".join(data) if isinstance(data,list) else data
        amt_data = re.sub(self.REGEX['escape'],"",amt_data).strip()
        matches = re.findall(self.REGEX[pattern],amt_data,re.IGNORECASE)
        final_dict = {}
        for match in matches:
            if len(match) == 2:
                amt, thraftr = match
                final_dict['amt'], final_dict['thraftr'] = amt,thraftr
            elif len(match) == 3:
                min_type,amt,thraftr = match
                
                final_dict[min_type] = {"amt": amt,"thraftr":thraftr,}
                
        return {main_key:final_dict}
    
    #match
    def _match_regex_to_content(self, string: str, data: list,*args):
        try:
            for pattern, (func_name, regex_key) in self.PATTERN_TO_FUNCTION.items():
                if re.match(pattern, string, re.IGNORECASE):
                    func = getattr(self, func_name) #dynamic function lookup
                    if regex_key:
                        return func(string, data, regex_key)
                    return func(string, data)
                
        except Exception as e:
            logger.error(e)
            return
        
        return self._extract_dummy_data(string, data) #fallback
    
    def _secondary_match_regex_to_content(self, string: str, data: list,*args):
        try:
            for pattern, (func_name, regex_key) in self.SECONDARY_PATTERN_TO_FUNCTION.items():
                if re.match(pattern, string, re.IGNORECASE):
                    func = getattr(self, func_name) #dynamic function lookup
                    if regex_key:
                        return func(string, data, regex_key)
                    return func(string, data)
            
        except Exception as e:
            logger.error(e)
            return
        
        return self._extract_dummy_data(string, data) #fallback
    
    def _tertiary_match_regex_to_content(self, string: str, data: list,*args):
        try:
            for pattern, (func_name, regex_key) in self.TERTIARY_PATTERN_TO_FUNCTION.items():
                if re.match(pattern, string, re.IGNORECASE):
                    func = getattr(self, func_name) #dynamic function lookup
                    if regex_key:
                        return func(string, data, regex_key)
                    return func(string, data)
            
        except Exception as e:
            logger.error(e)
            return
        
        return self._extract_dummy_data(string, data) #fallback
    
    #merge and select
    # def _merge_fund_data(self, data:dict):
    #     if not isinstance(data, dict):
    #         return data

    #     for new_key, keys_to_merge in self.MERGEKEYS.items():
    #         if all(isinstance(data.get(key), list) for key in keys_to_merge if key in data):
    #             # Merge as a list
    #             merged_value = []
    #             for key in keys_to_merge:
    #                 if key in data:
    #                     merged_value.extend(data[key])
    #                     data.pop(key, None)
    #         else:
    #             # Merge as a dictionary
    #             merged_value = {key: data[key] for key in keys_to_merge if key in data}
    #             for key in keys_to_merge:
    #                 data.pop(key, None)

    #         if merged_value:
    #             data[new_key] = merged_value  

    #     return data
    
    def _merge_fund_data(self, data: dict):
        if not isinstance(data, dict):
            return data  # Only process dicts

        for new_key, keys_to_merge in self.MERGEKEYS.items():
            values = [data[key] for key in keys_to_merge if key in data]

            if all(isinstance(v, list) for v in values):
                # Merge as a list
                merged_value = []
                for v in values:
                    merged_value.extend(v)
            elif all(isinstance(v, dict) for v in values):
                # Merge as a dictionary
                merged_value = {}
                for v in values:
                    merged_value.update(v)
            else:
                # Mixed types: Handle string + dict
                merged_value = {}
                for key in keys_to_merge:
                    if key in data:
                        if isinstance(data[key], dict):
                            merged_value.update(data[key])  # Merge dict normally
                        else:
                            merged_value[key] = data[key]  # Store string under its key

            # Remove original keys and insert merged value
            for key in keys_to_merge:
                data.pop(key, None)
            if merged_value:
                data[new_key] = merged_value  

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

    def _select_by_regex(self, data:dict):
        finalData = {}

        for key, value in data.items():
            if any(re.match(pattern, key, re.IGNORECASE) for pattern in self.SELECTKEYS):
                finalData[key] = value  # Keep only matching keys
        return finalData
    
    def _return_manager_data(self, since = "",name = "",desig= "",exp = ""):
        return {
            "managing_fund_since":since.title().strip(),
            "name": name.title().strip(),
            "qualification": desig.title().strip(),
            "total_exp": exp.title().strip()
        }
        
    def __last_day_of_previous_month(self):
        today = datetime.today()
        last_day = today.replace(day=1) - relativedelta(days=1)
        formatted_date = f"{last_day.day} {last_day.strftime('%B').strip().upper()} {last_day.year}"
        
        return "".join(formatted_date.split())
    
    def _update_imp_data(self,data:dict,fund:str, pgn:list):
        return data.update({
            "amc_name":self.IMP_DATA['amc_name'],
            "main_scheme_name":fund,
            "monthly_aaum_date": self.__last_day_of_previous_month(),
            "page_number":pgn,
            "mutual_fund_name":self.IMP_DATA['mutual_fund_name'], 
        })

#1 <>
class ThreeSixtyOne(Reader,GrandFundData):
    
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) #Pass params
    
    def _extract_manager_data(self, main_key: str, data: list, pattern:str):
        final_list = []
        manager_data = " ".join(data)
        manager_data = re.sub(self.REGEX['escape'], "", manager_data).strip()
        if matches := re.findall(self.REGEX[pattern], manager_data, re.IGNORECASE):
            for match in matches:
                name, exp = match
                final_list.append(self._return_manager_data(name = name, exp = exp))
        return {main_key: final_list}

#2 
class BajajFinServ(Reader,GrandFundData):
    
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) #Pass params
    
    def _extract_manager_data(self, main_key: str, data: list, pattern:str):
        final_list = []
        manager_data = " ".join(data) if isinstance(data,list) else data
        manager_data = re.sub(self.REGEX['escape'], "", manager_data).strip()
        if matches := re.findall(self.REGEX[pattern], manager_data, re.IGNORECASE):
            for match in matches:
                name, desig,since ,exp = match
                final_list.append(self._return_manager_data(name = name,desig=desig,since=since,exp = exp))
        return {main_key: final_list}
#3 <>
class Bandhan(Reader,GrandFundData):
    
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) #Pass params
        
    def _extract_manager_data(self, main_key:str, data:list,pattern:str):
        final_list = []
        manager_data = " ".join(data)
        manager_data = re.sub(self.REGEX['escape'],"",manager_data).strip()
        matches = re.findall(self.REGEX[pattern], manager_data, re.IGNORECASE)
        for match in matches:
            name, since = match
            final_list.append(self._return_manager_data(name= name,since= since))
        return {main_key:final_list}
        
        

#4
class BankOfIndia(Reader,GrandFundData):
    
    def __init__(self,paths_config:str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) #Pass params

    def _extract_manager_data(self, main_key:str, data:list,pattern:str):
        final_list = []
        manager_data = " ".join(data)
        manager_data = re.sub(self.REGEX['escape'],"",manager_data).strip()
        matches = re.findall(self.REGEX[pattern], manager_data, re.IGNORECASE)
        for match in matches:
            name, since,exp = match
            final_list.append(self._return_manager_data(name= name,since= since, exp=exp))
        return {main_key:final_list}

#5 <>
class BarodaBNP(Reader,GrandFundData): #Lupsum issues
    
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) #Pass params
    
    def _extract_manager_data(self, main_key:str, data:list,pattern:str):
        final_list = []
        manager_data = " ".join(data)
        manager_data = re.sub(self.REGEX['escape'],"",manager_data).strip()
        matches = re.findall(self.REGEX[pattern], manager_data, re.IGNORECASE)
        for match in matches:
            name, since, exp = match
            final_list.append(self._return_manager_data(name= name,since= since, exp=exp))
        return {main_key:final_list}
    
    def _extract_lumpsum_data(self,main_key:str,data:list,pattern:str):
        if not data:
            return {main_key:data}
        
        lump_data = " ".join(data)
        lump_data = re.sub(self.REGEX['escape'],"",lump_data).strip()
        final_dict = {}
        if matches:= re.findall(self.REGEX[pattern],lump_data, re.IGNORECASE):
            for match in matches:
                for key, value in match:
                    if not key: #key == ""
                        return {main_key:value}
                    else:
                        final_dict[key] = value
        
        return {main_key:final_dict}
            
    def _extract_aum_data(self, main_key: str, data: list, pattern: str):
        final_dict = {}
        for text in data:
            text = re.sub(self.REGEX['escape'], "", text.strip())
            
            if matches:= re.findall(self.REGEX[pattern], text, re.IGNORECASE):
                for match in matches:
                        key, value = match
                        final_dict[key.strip()] = value.strip()
            elif matches:= re.findall(self.REGEX['date'], text, re.IGNORECASE):
                date = matches[0]
                final_dict['inception_date'] = date

        return {"aum":final_dict}
    
    def get_proper_fund_names(self, path:str, pages:list, bbox:set):
        doc = fitz.open(path)
        
        fund_titles = dict()
        for pgn in range(doc.page_count):
            if pgn in pages:
                page = doc[pgn]
                blocks = page.get_text('dict', clip=bbox)['blocks']
                combined_text = []
        
                for block in blocks:
                    for line in block.get('lines', []):
                        for span in line.get('spans', []):
                            text = span.get('text', "")
                            if re.search(r'^Baroda BNP', text) or re.search(r'Fund$', text):
                                combined_text.append(text)
                fund_titles[pgn] = " ".join(combined_text)
            else:
                fund_titles[pgn] = ""
        doc.close()
        return fund_titles

#6 
class Canara(Reader,GrandFundData):
    
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) #Pass params

#7
class DSP(Reader):
    
    PARAMS = {
        'fund': [[20,16], r'^(DSP|Bharat).*(Fund|ETF|FTF|FOF)$|^(DSP|Bharat)',[14,24],[-1]],
        'clip_bbox': [(0,5,120,812),],#[480,5,596,812]],
        'line_x': 120.0,
        'data': [[7,10], [-16777216], 30.0, ['TrebuchetMS-Bold']],
        'content_size':[30.0,10.0]
    }
    
    
    def __init__(self, paths_config:str):
        super().__init__(paths_config, self.PARAMS)
        
    #REGEX
    def __return_all_data(self,main_key,data:list):
        return {main_key:data}
    
    def __extract_inv_data(self,main_key:str, data:list):            
        return {main_key: ' '.join(data)}
    
    #MAPPING
    def match_regex_to_content(self, string:str, data:list):
        check_header = string
        if re.match(r"^investment.*", check_header, re.IGNORECASE):
            return self.__extract_inv_data(string,data)
        # elif re.match(r"^aum.*", check_header, re.IGNORECASE):
        #     return self.__extract_aum_data(string, data)
        # elif re.match(r"^fund_mana.*", check_header, re.IGNORECASE):
        #     return self.__extract_manager_data(string, data)
        # elif re.match(r"^metrics.*", check_header, re.IGNORECASE):
        #     return self.__extract_metric_data(string, data)
        return self.__return_all_data(string,data)

#8 <>
class Edelweiss(Reader,GrandFundData):
    
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) #Pass params
    
    def get_proper_fund_names(self, path: str, pages: list):
        doc = fitz.open(path)
        final_fund_names,final_objectives = {},{}

        for pgn in pages:
            fund_names, objective_names = [], []
            page = doc[pgn]  
            blocks = page.get_text("dict").get("blocks", [])

            for count, block in enumerate(blocks):
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span["text"].strip()
                        if count == 1:  # Fund
                            fund_names.append(text)
                        elif count == 4:  # Objective
                            objective_names.append(text)

            final_fund_names[pgn] = " ".join(fund_names)
            final_objectives[pgn] = " ".join(objective_names)

        return final_fund_names, final_objectives
      
    def _extract_date_data(self, main_key:str,data:list, pattern:str):
        date_data = "".join(main_key)
        matches = re.findall(self.REGEX[pattern],date_data, re.IGNORECASE)
        return {"inception_date": " ".join(matches)}
    
    def _extract_manager_data(self, main_key:str, data:list, pattern:str):
        manager_data = data
        final_list = []
        for text in manager_data:
            text = text.strip()
            if matches:= re.findall(self.REGEX[pattern], text, re.IGNORECASE):
                for match in matches:
                    name,exp,since = match
                    final_list.append(self._return_manager_data(name=name,exp=exp,since=since))
                
        return {main_key:final_list}
    
    def _extract_aum_data(self,main_key:str, data:list,pattern:str):
        final_dict = {}
        for text in data:
            text = re.sub(self.REGEX['escape'],"",text).strip()
            if matches:= re.findall(self.REGEX[pattern],text, re.IGNORECASE):
                for value1, value2 in matches:
                    final_dict['Month End Aum'], final_dict['Monthly Average Aum'] = value1, value2

        return {main_key:final_dict}

#9 <>
class FranklinTempleton(Reader,GrandFundData):
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) #Pass params
    
    def _extract_manager_data(self, main_key: str, data, pattern:str):
        manager_data = " ".join(data) if isinstance(data, list) else data
        manager_data = re.sub(self.REGEX["escape"], "", manager_data).strip()
        final_list = []
        if matches := re.findall(self.REGEX[pattern], manager_data, re.IGNORECASE):
            for match in matches:
                name = match
                final_list.append(self._return_manager_data(name=name))
        return {main_key: final_list}

#10 
class HDFC(Reader,GrandFundData):
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) #Pass params
    
    def _extract_manager_data(self, main_key: str, data, pattern:str):
        manager_data = " ".join(data) if isinstance(data, list) else data
        manager_data = re.sub(self.REGEX["escape"], "", manager_data).strip()
        final_list = []
        if matches := re.findall(self.REGEX[pattern], manager_data, re.IGNORECASE):
            for match in matches:
                name,desig,since,exp = match
                final_list.append(self._return_manager_data(name=name,desig=desig,since=since,exp=exp))
        return {main_key: final_list}    
    

#11
class GROWW(Reader,GrandFundData):
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) #Pass params
    
    def _extract_manager_data(self, main_key: str, data, pattern:str):
        manager_data = " ".join(data) if isinstance(data,list) else data
        manager_data = re.sub(self.REGEX["escape"], "", manager_data).strip()
        final_list = []
        if matches := re.findall(self.REGEX[pattern], manager_data, re.IGNORECASE):
            for match in matches:
                name,desig,since,exp = match
                final_list.append(self._return_manager_data(name=name,desig=desig,exp=exp, since=since))
        return {main_key: final_list}

    def _extract_date_data(self, main_key:str,data:list, pattern:str):
        date_data = "".join(main_key)
        matches = re.findall(self.REGEX[pattern],date_data, re.IGNORECASE)
        return {"inception_date": " ".join(matches)}
    
    def _extract_metric_data(self, main_key:str, data, pattern:str):
        final_dict = {}
        metric_data = " ".join(data) if isinstance(data,list) else data
        metric_data = re.sub(self.REGEX['escape'],"",metric_data).strip()
        indice_pattern,value_pattern = self.REGEX[pattern]
        match1 = re.findall(indice_pattern,metric_data,re.IGNORECASE)
        match2 = re.findall(value_pattern,metric_data,re.IGNORECASE)
        for key,value in zip(match1,match2):
            final_dict[key] = value
        
        return {main_key:final_dict}        
#12 <>
class Helios(Reader,GrandFundData):
    
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) #Pass params
        
    def _extract_manager_data(self, main_key:str, data, pattern:str):
        manager_data = re.sub(self.REGEX['escape'],"", data).strip()
        final_list = []
        if matches:= re.findall(self.REGEX[pattern],manager_data,re.IGNORECASE):
            for match in matches:
                name,since,exp = match
                final_list.append(self._return_manager_data(name=name,since=since,exp=exp))
        
        return {main_key: final_list}

#13 

#14

#15 <>
class Invesco(Reader,GrandFundData): #Lupsum issues
    
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) #Pass params
        
    def _extract_manager_data(self, main_key:str, data:list,pattern:str):
        manager_data = " ".join(data)
        manager_data = re.sub(self.REGEX['escape'],"",manager_data).strip()
        final_list = []
        matches = re.findall(self.REGEX[pattern], manager_data, re.IGNORECASE)
        for match in matches:
            name,exp,since = match
            final_list.append(self._return_manager_data(name=name,since=since,exp=exp))
        
        return {main_key:final_list}

#16 <>
class ITI(Reader,GrandFundData):
    
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) #Pass params
     
    def _extract_nav_data(self,main_key:str, data:list, pattern:str):
        final_dict = {}
        for text in data:
            text = re.sub(self.REGEX['escape'], "", text).strip()
            if matches := re.findall(self.REGEX[pattern], text, re.IGNORECASE):
                for match in matches:
                    key, regular, direct = match
                    final_dict[f'Regular {key}'] = regular
                    final_dict[f'Direct {key}'] = direct
        return {main_key: final_dict}
    
    def _extract_manager_data(self, main_key:str, data:list, pattern:str):
        manager_data = " ".join(data)
        manager_data = re.sub(self.REGEX['escape'],"",manager_data).strip()
        final_list = []  
        matches= re.findall(self.REGEX[pattern], manager_data, re.IGNORECASE)
        for match in matches:
            name,since,exp = match
            final_list.append(self._return_manager_data(name=name,since=since))
                
        return {main_key:final_list}

#17 <>
class Kotak(Reader,GrandFundData): #Lupsum issues
    
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) #Pass params
        
    def _extract_manager_data(self, main_key:str, data:list,pattern:str):
        final_list = []
        for text in data:
            text = re.sub(self.REGEX['escape'],'',text).strip()
            matches = re.findall(self.REGEX[pattern], text, re.IGNORECASE)
            name = matches
            final_list.append(self._return_manager_data(name=" ".join(name)))
        
        return {main_key:final_list}
    
    def _extract_nav_data(self,main_key:str, data:list,pattern:str):
        final_dict = {}
        for text in data:
            text = re.sub(self.REGEX['escape'],"",text).strip()
            if matches := re.findall(self.REGEX[pattern], text, re.IGNORECASE):
                for index, reg, direct in matches:
                    final_dict[f'Regular {index}'] = reg
                    final_dict[f'Direct {index}'] = direct
        return {main_key:final_dict}

#18
class LIC(Reader,GrandFundData): #Lupsum issues
    
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) #Pass params

    def get_proper_fund_names(self,path: str): #send ocr path btw
        doc = fitz.open(path)
        title = {}
        for pgn in range(doc.page_count):
            page = doc[pgn]
            blocks = page.get_text("dict")['blocks']
            text_all = " ".join(
                span["text"].strip()
                for block in blocks[:4]
                for line in block.get("lines", [])
                for span in line.get("spans", [])
                if span["text"].strip()
            )

            text_all = re.sub(self.REGEX['escape'], '', text_all).strip()
            matches = re.findall(self.PARAMS['fund']['regex'], text_all, re.IGNORECASE)
            title[pgn] = matches[0] if matches else ""

        return title
    
    def _extract_manager_data(self,main_key:str, data:list, pattern:str):
        final_list = []
        manager_data = " ".join(data)
        manager_data = re.sub(self.REGEX['escape'], "", manager_data).strip()
        matches = re.findall(self.REGEX[pattern], manager_data, re.IGNORECASE)
        for match in matches:
            name,exp = match
            final_list.append(self._return_manager_data(name=name,exp=exp))
        return {main_key:final_list}
    
#19 <>
class MahindraManu(Reader,GrandFundData):
    
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) #Pass params
        
    def get_proper_fund_names(self,path:str,pages:list):
        
        doc = fitz.open(path)
        final_fund_names = dict()
        
        for pgn in range(doc.page_count):
            fund_names = ''
            if pgn in pages:
                page = doc[pgn]            
                blocks = page.get_text("dict")['blocks']
                
                sorted_blocks = sorted(blocks,key=lambda k:(k['bbox'][1],k['bbox'][0]))
                for count,block in enumerate(sorted_blocks):
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            text = span['text'].strip()
                            if count in range(0,2): #contains fund name        
                                fund_names += f'{text} '
            if matches:= re.search(r'\bMahindra.*?(Fund|ETF|EOF|FOF|FTF|Path)\b', fund_names, re.IGNORECASE):           
                final_fund_names[pgn] = matches.group()
            else:
                final_fund_names[pgn] = ''

        return final_fund_names

    def _extract_manager_data(self,main_key:str, data:list, pattern:str):
        final_list = []
        manager_data = " ".join(data)
        manager_data = re.sub(self.REGEX['escape'], "", manager_data).strip()
        matches = re.findall(self.REGEX[pattern], manager_data, re.IGNORECASE)
        for match in matches:
            name,exp,since = match
            final_list.append(self._return_manager_data(name=name,exp=exp,since=since))
        return {main_key:final_list}
    
    def _extract_nav_data(self,main_key:str, data:list,pattern:str):
        final_dict = {}
        nav_data = data
        for text in nav_data:
            text = re.sub(self.REGEX['escape'], "", text.strip())
            if matches := re.findall(self.REGEX[pattern], text, re.IGNORECASE):
                for index, reg, direct in matches:
                    final_dict[f'Regular {index}'] = reg
                    final_dict[f'Direct {index}'] = direct
        
        return {main_key: final_dict}
    
    #something

#20 <>
class MIRAE(Reader,GrandFundData):
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) #Pass params
     
    def get_proper_fund_names(self, path:str,pages:list):
        
        doc = fitz.open(path)
        final_fund_names = dict()
        pattern = r'MIRAE ASSET .*?\b(?:ETF|EOF|FOF|FTF|FUND|FUND OF FUND|INDEX FUND)\b'
        
        for pgn in range(doc.page_count):
            text_all = ''
            if pgn in pages:
                # print(pgn)
                page = doc[pgn]            
                blocks = page.get_text("dict")['blocks']
                
                sorted_blocks = sorted(blocks,key=lambda k:(k['bbox'][1],k['bbox'][0]))
                for count,block in enumerate(sorted_blocks):
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            text = span['text'].strip()
                            if count in range(0,1):
                                text_all+=f" {text}"

            if matches := re.findall(pattern, text_all.strip(), re.DOTALL):
                final_fund_names[pgn] = matches[0]
            else:
                final_fund_names[pgn] = ""
        return final_fund_names

#21 <>
class MotilalOswal(Reader,GrandFundData): #Lupsum issues
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) #Pass params
    
    def _extract_manager_data(self, main_key:str, data:list,pattern:str):
        final_list = []
        manager_data = " ".join(data)
        manager_data = re.sub(self.REGEX['escape'], "", manager_data).strip()
        if matches:= re.findall(self.REGEX[pattern], manager_data, re.IGNORECASE):
            for match in matches:
                name, since, exp = match
                final_list.append(self._return_manager_data(name=name,since=since,exp=exp))
        
        return {main_key:final_list}
    
    def _extract_amt_data(self, main_key:str,data:list, pattern:str):
        amt_data = " ".join(data)
        final_dict = {}
        amt_data = re.sub(self.REGEX['escape'],'',amt_data).strip()
        if matches:= re.findall(self.REGEX[pattern],amt_data,re.IGNORECASE):
            for match in matches:
                name,amt,thraftr = match
                final_dict[name] = {
                    'amt': amt,
                    'thraftr':thraftr
                }
        return {main_key:final_dict}

#22 <>
class NAVI(Reader,GrandFundData): #Lupsum issues
    
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) #Pass params
        
    def _extract_manager_data(self, main_key:str, data:list,pattern:str):
        final_list = []
        manager_data = " ".join(data)
        manager_data = re.sub(self.REGEX['escape'], "", manager_data).strip()
        for text in data:
            matches = re.findall(self.REGEX[pattern], text, re.IGNORECASE)
            for match in matches:
                name, since = match
                final_list.append(self._return_manager_data(name=name,since=since))
        
        return {main_key:final_list}

#23 <>
class Nippon(Reader,GrandFundData):
    
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) #Pass params
    
    def _extract_manager_data(self,main_key:str,data:list, pattern:str):
        manager_data = data
        final_list = []
        for idx in range(0,len(manager_data),2):
            df = " ".join(manager_data[idx:idx+2])
            if matches := re.findall(self.REGEX[pattern], df, re.IGNORECASE):
                name, desig, since,exp = matches[0]
                final_list.append(self._return_manager_data(name=name,desig=desig,since=since,exp=exp))
        return {main_key:final_list}

#24
class NJMF(Reader):
    PARAMS = {
        'fund': [[20,16,0], r'^(NJ).*(Fund|ETF|EOF|FOF|FTF|Path|Scheme)$',[16,24],[-13604430]],
        'clip_bbox': [(0,5,250,812)],
        'line_x': 250.0,
        'data': [[6,11], [-14475488], 30.0, ['Swiss721BT-Medium']],
        'content_size':[30.0,10.0]
        }
    
    def __init__(self, paths_config:str):
        super().__init__(paths_config, self.PARAMS)
        
    #REGEX
    def __return_all_data(self,main_key,data:list):
        return {main_key:data}
    
    def __extract_inv_data(self,main_key:str, data:list):            
        return {main_key: ' '.join(data).strip()}
    
    def __extract_ter_data(self,main_key:str,data:list):
        pattern = r'(Regular Plan|Direct Plan)\s*([\d,.]+)%?'
        ter_data = data
        final_dict = {}
        for text in ter_data:
            text =  re.sub(r"[\^#*\$]", "", text.strip())
            if matches:= re.findall(pattern, text, re.IGNORECASE):
                for key, value in matches:
                    final_dict[key] = value
        
        return {main_key:final_dict}
    
    def __extract_nav_data(self,main_key:str, data:list):
        pattern = r'(.+?IDCW|.+?Growth)\s([\d.]+)'
        final_dict = {}
        nav_data = data
        for text in nav_data:
            text = re.sub(r"[\^#*\$]", "", text.strip())
            if matches := re.findall(pattern, text, re.IGNORECASE):
                for key, value in matches:
                    final_dict[key] = value
        
        return {main_key: final_dict}
    
    def __extract_metric_data(self,main_key:str, data:list):
        pattern =  r'(Monthly AAUM|Latest AUM\s\(.*\)|Beta|Portfolio Turnover Ratio|Standard Deviation|Sharpe Ratio|Average Maturity|YTM|Yield to Maturity|Macaulay Duration|Modified Duration)\s*([\d,.]+)'
        final_dict = {}
        metric_data = data
        for text in metric_data:
            text = re.sub(r"[\^#*\$,]", "", text.strip())
            if matches := re.findall(pattern, text, re.IGNORECASE):
                for key, value in matches:
                    final_dict[key] = value
        
        return {main_key: final_dict}
    
    
    #MAPPING
    def match_regex_to_content(self, string: str, data: list):
        pattern_to_function = {
            r"^(exit|entry|investment|date_of|options|plans|benchmark|additional_bench|monthly_average|closing_aum|type_of).*": self.__extract_inv_data,
            r"^nav.*": self.__extract_nav_data,
            r"^total.*": self.__extract_ter_data,
            r"^metric.*": self.__extract_metric_data,
        }

        for pattern, func in pattern_to_function.items():
            if re.match(pattern, string, re.IGNORECASE):
                return func(string, data)

        return self.__return_all_data(string, data)

#25
class OldBridge(Reader,GrandFundData):
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) #Pass params

#26

#27

#28

#29 
class Quantum(Reader,GrandFundData): #Lupsum issues
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand
        Reader.__init__(self,paths_config, self.PARAMS) #Pass params
    
    def _extract_manager_data(self, main_key: str, data: list, pattern: str):
        final_list = []
        manager_data = "".join(data)
        manager_data = re.sub(self.REGEX['escape'], "", manager_data).strip()
        if matches := re.findall(self.REGEX[pattern], manager_data, re.IGNORECASE):
            for match in matches:
                name, exp,since = match
                final_list.append(self._return_manager_data(name=name,since=since, exp=exp))
        return {main_key: final_list}
    

#30 <>
class Samco(Reader, GrandFundData):
    
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) #Pass params

    def _extract_manager_data(self, main_key: str, data: list, pattern: str):
        final_list = []
        for i in range(0, len(data), 3):
            txt = " ".join(data[i:i+3])
            txt = re.sub(self.REGEX['escape'], "", txt).strip()
            if matches := re.findall(self.REGEX[pattern], txt, re.IGNORECASE):
                for match in matches:
                    name, desig, since, exp = match
                    final_list.append(self._return_manager_data(name=name,desig=desig,since=since, exp=exp))
        return {main_key: final_list}

#31
class SBI(Reader, GrandFundData):
    
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) #Pass params

#32

#33 <>
class Sundaram(Reader,GrandFundData): #Lupsum issues
    
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) #Pass params
        
    def _extract_manager_data(self, main_key:str, data,pattern:str):
        final_list = []
        manager_data = " ".join(data) if isinstance(data,list) else data
        manager_data = re.sub(self.REGEX['escape'], "", manager_data.strip())
        if matches:=re.findall(self.REGEX[pattern],manager_data,re.IGNORECASE):
            for match in matches:
                name = match
                final_list.append(self._return_manager_data(name=name))
        
        return {main_key:final_list} 
  
#34 <>
class Tata(Reader,GrandFundData): #Lupsum issues
    
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) #Pass params
    
    def _extract_manager_data(self, main_key:str, data:list,pattern:str):
        final_list = []
        manager_data = " ".join(data)
        manager_data = re.sub(self.REGEX['escape'], "", manager_data).strip()
        if matches:=re.findall(self.REGEX[pattern],manager_data,re.IGNORECASE):
            for match in matches:
                name,since,exp = match
                final_list.append(self._return_manager_data(since = since,name = name,exp=exp))
        
        return {main_key:final_list} 

#35 <>
class Taurus(Reader,GrandFundData): #Lupsum issues
    
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) #Pass params
        
    def _extract_manager_data(self, main_key:str, data:list,pattern:str):
        final_list = []
        manager_data = " ".join(data)
        manager_data = re.sub(self.REGEX['escape'], "", manager_data.strip())
        if matches:=re.findall(self.REGEX[pattern],manager_data,re.IGNORECASE):
            for match in matches:
                name,since,exp = match
                final_list.append(self._return_manager_data(name=name,since=since,exp=exp))
        
        return {main_key:final_list}

#36
class Trust(Reader):
    
    PARAMS = {
        'fund': [[4,20], r'^(Trust).*(Fund|ETF|EOF|FOF|FTF|Path|Fund*)$',[16,22],[-1]],
        'clip_bbox': [(0,135,180,812)],
        'line_x': 180.0,
        'data': [[8,11], [-1], 30.0, ['Roboto-Bold']],
        'content_size':[30.0,10.0]
        }
    
    def __init__(self,paths_config:str):
        super().__init__(paths_config, self.PARAMS)
    
    #REGEX
    def __return_all_data(self,main_key,data:list):
        return {main_key:data}
    
    def __extract_inv_data(self,main_key:str, data:list):            
        return {main_key: ' '.join(data)}
    
    def __extract_metric_data(self,main_key:str, data:list):
        metric_data = data
        final_dict = {}
        pattern = r'^(Yield|Average Maturity|Port?olio Turnover|Standard Devia[ti]?on|Modified Duration|Annualised Yield|Macaulay Duration|Tracking Error|Sharpe Ra[ti]?o|Beta|R Squared|Treynor)\s*(-?[\d,.]+)'
        for text in metric_data:
            text = re.sub(r"[\^\*:*\$]", "", text.strip())
            matches = re.findall(pattern, text, re.IGNORECASE)
            for key, value in matches:
                final_dict[key] = value
        return {main_key:final_dict}
    
    def __extract_nav_data(self,main_key:str, data:list):
        nav_data = data
        final_dict = {}
        pattern = r'(Growth|Regular|Direct)\s*([\d,.]+)\s*([\d,.]+)?'
        for text in nav_data:
            text = re.sub(r"[\^\*:*\$]", "", text.strip())
            matches = re.findall(pattern, text, re.IGNORECASE)
            for key, v1,v2 in matches:
                if key == "Growth":
                    final_dict["Regular Growth"] =v1
                    final_dict["Direct Growth"] =v2
                elif key == 'Regular' or key == 'Direct':
                    final_dict[f"total_expense_ratio {key}"] = v1
        return {main_key:final_dict}

    def __extract_scheme_data(self, main_key:str, data:list):
        mention_start = [
        "Date of Allotment",
        "Fund Manager",
        "Fund Size",
        "Load Structure",
        "Benchmark",
        "Minimum Additional",
        r"Minimum Redemption\s*\/\s*Switch-out Amount",
    ]
        
        mention_end = mention_start[1:] + ["End_of_Data"]

        # Generate regex patterns dynamically
        patterns = [r"({start}\s*)(.+?)({end}|$)".format(start=start, end=end)
            for start, end in zip(mention_start, mention_end)]
        final_dict = {}
        scheme_data = " ".join(data)
        scheme_data = re.sub(r"[\^#*\$:;]", "", scheme_data)
        
        for pattern in patterns:
            if matches:= re.findall(pattern, scheme_data, re.DOTALL): #not used ignorecase
                for match in matches:
                    key, value, dummy = match
                    value = value.strip()
                    final_dict[key.strip()] = value

        return {main_key:final_dict}
    
    #MAPPING
    def match_regex_to_content(self, string: str, data: list):
        pattern_to_function = {
            r"^investment.*": self.__extract_inv_data,
            r"^metric": self.__extract_metric_data,
            r"^nav": self.__extract_nav_data,
            r"^scheme": self.__extract_scheme_data
        }

        for pattern, func in pattern_to_function.items():
            if re.match(pattern, string, re.IGNORECASE):
                return func(string, data)

        return self.__return_all_data(string, data)

#37
class Union(Reader):
    PARAMS = {
        'fund': [[20,4],r'^.*(Plan|Sensex|Fund|Path|ETF|FOF|EOF|Funds)$',[8,16],[-14453103]], #FUND NAME DETAILS order-> flag, regex_fund_name, font_size, font_color
        'clip_bbox': [(0,140,180,812)],
        'line_x': 180.0,
        'data': [[8,14],[-65794],30.0,['Swiss721BT-Bold']], #sizes, color, set_size
        'content_size':[30.0,10.0]
    }
    
    def __init__(self, paths_config):
        super().__init__(paths_config, self.PARAMS)
    
    #Fund Regex  
    def __return_all_data(self,main_key:str,data:list):
        return{main_key:data}
    def __extract_scheme_data(self,main_key:str, data:list):
        scheme_data = " ".join(data)
        scheme_data = re.sub(r'[\-\*;:,\^]+', '', scheme_data)
        mention_start = [
        "Investment Objective",
        "CoFund Managers",
        "Indicative Investment Horizon",
        "Date of allotment",
        "Assets Under Management",
        "Benchmark Index",
        "Expense Ratio as on",
        "Load Structure",
        "Active Stock Position in Scheme"]
    
        mention_end = mention_start[1:] + ["End_of_Data"]

        # Generate regex patterns dynamically
        patterns = [r"({start}\s*)(.+?)({end}|$)".format(start=start, end=end)
            for start, end in zip(mention_start, mention_end)]
        final_dict = {}
        
        for pattern in patterns:
            if matches:= re.findall(pattern, scheme_data, re.DOTALL|re.IGNORECASE): #not used ignorecase
                for match in matches:
                    key, value, dummy = match
                    value = value.strip()
                    final_dict[key.strip()] = value
        return {main_key:final_dict}
    
    
    def __extract_invest_data(self,main_key:str,data:list):
        return {main_key: " ".join(data)}
    
    #MAPPING FUNCTION
    def match_regex_to_content(self, string: str, data: list):
        pattern_to_function = {
            r"^(investment|minimum|entry|exit|load|plans|scheme_launch|benchmark).*": self.__extract_invest_data,
            r"^scheme.*": self.__extract_scheme_data,
        }

        for pattern, func in pattern_to_function.items():
            if re.match(pattern, string, re.IGNORECASE):
                return func(string, data)

        return self.__return_all_data(string, data)

#38
class UTI(Reader):
    PARAMS = {
        'fund': [[20], r'^(UTI).*(Fund|ETF|EOF|FOF|FTF|Path|Fund\*|Plan\*|Duration)$',[14,24],[-65794]],
        'clip_bbox': [(0,65,200,812)],
        'line_x': 200.0,
        'data': [[7,10], [-65794,-1], 30.0, ['Calibri-Bold']],
        'content_size':[30.0,8.0]
        }
    
    def __init__(self, paths_config:str):
        super().__init__(paths_config, self.PARAMS)
        
    #REGEX
    def __return_all_data(self,main_key:str,data:list):
        return{main_key:data}
    def __extract_invest_data(self,main_key:str,data:list):
        return {main_key: " ".join(data)}
    def __extract_total_exp_data(self,main_key:str,data:list):
        total_data = data
        final_dict = {}
        pattern = r'^(Regular|Direct)[\s:?]+([\d]+\.\d+)'
        for text in total_data:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for key, value in matches:
                final_dict[key] = value
        return {main_key:final_dict}
    
    def __extract_aum_data(self,main_key:str, data:list):
        aum_data = data
        pattern = r'(.+Average|.+AUM)\s*([\d,.]+)'
        final_dict = {}
        for text in aum_data:
            text = re.sub(r"[\^#*\$:;]", "", text.strip())
            if matches:= re.findall(pattern, text, re.IGNORECASE):
                for key, value in matches:
                    final_dict[key] = value
        return {main_key:final_dict}
    
    def __extract_nav_data(self,main_key:str, data:list):
        nav_data = data
        pattern = r'(.+Option)\s*([\d,.]+)'
        final_dict = {}
        for text in nav_data:
            text = re.sub(r"[\^#*\$:;]", "", text.strip())
            if matches:= re.findall(pattern, text, re.IGNORECASE):
                for key, value in matches:
                    final_dict[key] = value
        return {main_key:final_dict}
    
    def __extract_load_data(self,main_key:str, data:list):
        load_data = " ".join(data)
        load_data = re.sub(r'[\*.:\^;]+', "", load_data)
        
        entry_pattern = r"Entry Load\s*(N ?IL|.*)\s*(?=Exit Load)"
        exit_pattern = r"Exit Load\s*(.*?)$" 
        final_dict = {}
        
        entry_data = re.findall(entry_pattern,load_data, re.IGNORECASE|re.DOTALL)
        exit_data = re.findall(exit_pattern, load_data, re.IGNORECASE|re.DOTALL)
        
        final_dict['entry_load'] = " ".join(entry_data)
        final_dict['exit_load'] = " ".join(exit_data)
        
        return {main_key:final_dict}
    
    def __extract_manager_data(self, main_key:str, data:list):
        scheme_data = data
        final_list = []
        manager_pattern = r'\b(?:Mr|Mrs|Ms)\s+[A-Z][a-zA-Z]+\s+[A-Z][a-zA-Z]+'
        since_pattern = r'Managing the scheme since\s+([A-Za-z0-9]+[\s-]+[A-Za-z0-9]+)'

        for index in range(0,len(scheme_data),2):
            manager_data = {"experience":"","designation":""}
            for text in scheme_data[index:index+2]:
                text = re.sub(r'[\#\*.:;]+','', text.strip())
                if matches := re.findall(manager_pattern, text, re.IGNORECASE):
                    manager_data['name'] = matches[0]
                elif matches:= re.findall(since_pattern,text, re.IGNORECASE):
                    manager_data['managing_since'] = matches[0]
                
            final_list.append(manager_data)
             
        return {main_key:final_list}
    
    #MAPPING FUNCTION
    def match_regex_to_content(self, string: str, data: list):
        pattern_to_function = {
            r"^(date|benchmark|scheme_launch|additional).*": self.__extract_invest_data,
            r"^investment.*": self.__extract_invest_data,  # Since it's a comment
            r"^total.*": self.__extract_total_exp_data,
            r"^nav.*": self.__extract_nav_data,
            r"^aum.*": self.__extract_aum_data,
            r"^load.*": self.__extract_load_data,
            r"fund_manager": self.__extract_manager_data
        }

        for pattern, func in pattern_to_function.items():
            if re.match(pattern, string, re.IGNORECASE):
                return func(string, data)

        return self.__return_all_data(string, data)

#39 <>
class WhiteOak(Reader,GrandFundData):
    
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) #Pass params
        
    def get_proper_fund_names(self,path:str,pages:list):
        
        doc = fitz.open(path)
        final_fund_names = dict()
        
        for pgn in range(doc.page_count):
            fund_names = ''
            if pgn in pages:
                page = doc[pgn]            
                blocks = page.get_text("dict")['blocks']
                
                sorted_blocks = sorted(blocks,key=lambda k:(k['bbox'][1],k['bbox'][0]))
                for count,block in enumerate(sorted_blocks):
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            text = span['text'].strip()
                            if count in range(0,2): #contains fund name        
                                fund_names += f'{text} '
            if matches:= re.search(r'\bMahindra.*?(Fund|ETF|EOF|FOF|FTF|Path)\b', fund_names, re.IGNORECASE):           
                final_fund_names[pgn] = matches.group()
            else:
                final_fund_names[pgn] = ''

        return final_fund_names

    def _extract_nav_data(self,main_key:str, data:list,pattern:str):
        final_dict = {}
        for text in data:
            text = re.sub(self.REGEX['escape'], "", text.strip())
            if matches:= re.findall(self.REGEX[pattern], text, re.IGNORECASE):
                for k1,v1,k2,v2 in matches:
                    final_dict[f'Direct {k1}'] = v1
                    final_dict[f'Regular {k2}'] = v2
        return {main_key:final_dict}
    
    def _extract_manager_data(self, main_key:str, data:list,pattern:str):
        final_list = []
    
        manager_data = " ".join(data)
        manager_data = re.sub(self.REGEX['escape'],"", manager_data).strip()

        if matches:= re.findall(self.REGEX[pattern],manager_data, re.IGNORECASE):
            for match in matches:
                name,desig,since,exp = match
                final_list.append(self._return_manager_data(name=name,desig=desig,since=since,exp=exp))
        return {main_key:final_list}

#40
class Zerodha(Reader,GrandFundData):
    
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name)
        Reader.__init__(self,paths_config, self.PARAMS)
        
    def _extract_manager_data(self, main_key:str, data:list,pattern:str):
        final_list = []

        manager_data = " ".join(data)
        manager_data = re.sub(self.REGEX['escape'],"", manager_data).strip()

        if matches:= re.findall(self.REGEX[pattern],manager_data, re.IGNORECASE):
            for match in matches:
                name,desig,since,exp = match
                final_list.append(self._return_manager_data(name=name,since=since,desig=desig,exp=exp))
        return {main_key:final_list}
    
#41 Aditya Birla
class AdityaBirla(Reader,GrandFundData):
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) #Pass params
 
#42 Axis Mutual

#43 JMMF
class JMMF(Reader,GrandFundData):
    
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) #Pass params
        

