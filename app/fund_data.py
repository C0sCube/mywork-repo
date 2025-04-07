import re, os,json, json5,ocrmypdf #type:ignore
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

        #amc indicators
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
        
    #extract 
    def _extract_dummy_data(self,main_key:str,data):
        return {main_key:data}
    
    def _extract_and_trim_data(self,main_key:str,data,pattern:str):
        trim_data = " ".join(data) if isinstance(data,list) else data
        trim_data = re.sub(self.REGEX["escape"],"",trim_data).strip()
        return {main_key:trim_data[:self.REGEX[pattern]] if len(trim_data)>self.REGEX[pattern] else trim_data}
    
    def _extract_bench_data(self,main_key:str,data,pattern:str):
        data = " ".join(data) if isinstance(data,list) else data
        benchmark_data = re.sub(self.REGEX['escape'],"",data).strip()
        matches = re.findall(self.REGEX[pattern],benchmark_data, re.IGNORECASE)
        return {main_key:matches[0] if matches else ""}
    
    def _extract_scheme_data(self,main_key:str,data:list, pattern:str):
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
        return {main_key: ' '.join(data)}
    
    def _extract_generic_data(self, main_key: str, data, pattern: str):
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
        metric_data = " ".join(data) if isinstance(data,list) else data
        metric_data = re.sub(self.REGEX["escape"],"",metric_data).strip()
        final_dict = {}
        values = re.findall(self.REGEX[pattern]["value"],metric_data,re.IGNORECASE)
        keys = re.findall(self.REGEX[pattern]["key"],metric_data,re.IGNORECASE)
        for k,v in zip(keys,values):
            final_dict[k.strip()] = v.strip()
        return{main_key:final_dict}  

    def _extract_load_data(self,main_key:str,data:list, pattern:str):
        load_data = " ".join(data) if isinstance(data,list) else data
        load_data = re.sub(self.REGEX['escape'], "", load_data).strip()
        final_dict = {'entry_load':"","exit_load":""}
        if matches:= re.findall(self.REGEX[pattern],load_data.strip(), re.IGNORECASE):
            for match in matches:
                entry_,exit_ = match 
            final_dict['entry_load'], final_dict['exit_load'] = entry_.strip(),exit_.strip()
        return {main_key:final_dict}
     
    def _extract_amt_data(self,main_key:str, data, pattern:str):
        amt_data = " ".join(data) if isinstance(data,list) else data
        amt_data = re.sub(self.REGEX['escape'],"",amt_data).strip()
        final_dict = {'amt':"",'thraftr':""}
        if matches:= re.findall(self.REGEX[pattern],amt_data,re.IGNORECASE):
            amt,thraftr = matches[0]
            final_dict['amt'], final_dict['thraftr'] = amt,thraftr
        return {main_key:final_dict}
    
    def _extract_manager_data(self, main_key: str, data, pattern: str):
        final_list = []
        manager_data = " ".join(data) if isinstance(data, list) else data
        manager_data = re.sub(self.REGEX['escape'], "", manager_data).strip()

        pattern_info = self.REGEX[pattern]
        regex_pattern = pattern_info['pattern']
        field_names = pattern_info['fields']

        if matches := re.findall(regex_pattern, manager_data, re.IGNORECASE):
            for match in matches:
                if isinstance(match, str):
                    match = (match,)
                record = {field_names[i]: match[i] if i < len(match) else "" for i in range(len(field_names))} #kwargs
                final_list.append(self._return_manager_data(**record))

        return {main_key: final_list}
    
    def _extract_lump_data(self, main_key: str, data, pattern:list):
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
            final_dict['min_amt'] = min_amt
            final_dict['add_amt'] = add_amt
    
        return {main_key: final_dict}

    # #match
    def _match_with_patterns(self, string: str, data: list, level:str):
        try: 
            for pattern, (func_name, regex_key) in self.PATTERN[level].items():
                if re.match(pattern, string, re.IGNORECASE):
                    func = getattr(self, func_name)  # dynamic function lookup
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
                    func = getattr(self, func_name) #dynamic function lookup
                    return func(string, data)    
        except Exception as e:
            logger.error(e)
            return
        return self._extract_dummy_data(string, data)
    
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
    
    # def _merge_fund_data(self, data: dict):
    #     if not isinstance(data, dict):
    #         return data  # Only process dicts

    #     for new_key, keys_to_merge in self.MERGEKEYS.items():
    #         values = [data[key] for key in keys_to_merge if key in data]

    #         if all(isinstance(v, list) for v in values):
    #             # Merge as a list
    #             merged_value = []
    #             for v in values:
    #                 merged_value.extend(v)
    #         elif all(isinstance(v, dict) for v in values):
    #             # Merge as a dictionary
    #             merged_value = {}
    #             for v in values:
    #                 merged_value.update(v)
    #         else:
    #             # Mixed types: Handle string + dict
    #             merged_value = {}
    #             for key in keys_to_merge:
    #                 if key in data:
    #                     if isinstance(data[key], dict):
    #                         merged_value.update(data[key])  # Merge dict normally
    #                     else:
    #                         merged_value[key] = data[key]  # Store string under its key
            
    #         for key in keys_to_merge:
    #             data.pop(key, None)
    #         if merged_value:
    #             data[new_key] = merged_value  

    #     return data
    
    def _merge_fund_data(self, data: dict):
        if not isinstance(data, dict):
            return data  # Only process dicts

        for new_key, patterns in self.MERGEKEYS.items():
            # Find matching keys using regex patterns
            keys_to_merge = [key for key in data if any(re.search(pattern, key, re.IGNORECASE) for pattern in patterns)]
            values = [data[key] for key in keys_to_merge if key in data]

            if all(isinstance(v, list) for v in values): #list + list
                merged_value = []
                for v in values:
                    merged_value.extend(v)
            elif all(isinstance(v, dict) for v in values): #dict + dict
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
            
            for key in keys_to_merge: #remove original keys
                data.pop(key, None)

            # Add the merged value if it's not empty
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
    
    def _update_imp_data(self,data:dict,fund:str, pgn:list):
        return data.update({
            "amc_name":self.IMP_DATA['amc_name'],
            "main_scheme_name":fund,
            "monthly_aaum_date": (datetime.today().replace(day=1) - relativedelta(days=1)).strftime("%d%B%Y").upper(),
            "page_number":pgn,
            "mutual_fund_name":self.IMP_DATA['mutual_fund_name'], 
        })

#1 <>
class ThreeSixtyOne(Reader,GrandFundData):   
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) 

#2 
class BajajFinServ(Reader,GrandFundData):  
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) 
#3 <>
class Bandhan(Reader,GrandFundData):  
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) 
#4
class BankOfIndia(Reader,GrandFundData):   
    def __init__(self,paths_config:str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) 
#5 <>
class BarodaBNP(Reader,GrandFundData):
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS)   
#6 
class Canara(Reader,GrandFundData):
    
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) 
    
    def _update_manager_data(self,main_key:str,manager_data):
        name = r"(?:Mr\.?|Mrs\.?|Ms\.?)\s+([A-Z][a-z]+\s[A-Z][a-z]+)"
        exp = r"\b\d+\s*Years?\b"
        since = r"\bSince\s*([0-9]+\s*-\s*[A-Za-z]+\.?\s*-\s*[0-9]+)\b"
        nsample, msample, esample = [], [], []
        nlength = 0
        value = " ".join(manager_data.values())
        nsample = re.findall(name, value, re.IGNORECASE)
        esample = re.findall(exp, value, re.IGNORECASE)
        msample = re.findall(since, value, re.IGNORECASE)
        
        nlength = len(nsample)
        msample += [""] * (nlength - len(msample))
        esample += [""] * (nlength - len(esample))
        
        final_list = [self._return_manager_data(since=m,name=n,exp=e)for n, m, e in zip(nsample, msample, esample)]
        return {main_key:final_list}

#7
class DSP(Reader,GrandFundData):

    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) 

#8 <> 
class Edelweiss(Reader,GrandFundData):
    
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) 
    def _extract_date_data(self, main_key:str,data:list, pattern:str):
        date_data = "".join(main_key)
        matches = re.findall(self.REGEX[pattern],date_data, re.IGNORECASE)
        return {"inception_date": " ".join(matches)}
#9 <>
class FranklinTempleton(Reader,GrandFundData):
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) 

#10 
class HDFC(Reader,GrandFundData):
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) 
    
    def _extract_manager_data(self, main_key: str, data, pattern:str):
        DATE_PATTERN = r"([A-Za-z]+\s*\d+),"
        NAME_PATTERN = r"([A-Za-z]+\s[A-Za-z]+)"
        EXP_PATTERN = r"over (\d+)"
        YEAR_PATTERN = r"(\d{4})"

        manager_data = " ".join(data)
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

#11
class GROWW(Reader,GrandFundData):
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) 
        
    def _extract_date_data(self, main_key:str,data:list, pattern:str):
        date_data = "".join(main_key)
        matches = re.findall(self.REGEX[pattern],date_data, re.IGNORECASE)
        return {"inception_date": " ".join(matches)}
#12 <>
class Helios(Reader,GrandFundData):
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) 

#13 
class HSBC(Reader,GrandFundData):
    
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) 
#14
class ICICI(Reader,GrandFundData):
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) 
#15 <>
class Invesco(Reader,GrandFundData): 
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) 
#16 <>
class ITI(Reader,GrandFundData):
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) 
#17 <>
class Kotak(Reader,GrandFundData): #Lupsum issues
    
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) 
#18
class LIC(Reader,GrandFundData): #Lupsum issues
    
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) 

    def get_proper_fund_names(self,input_pdf:str, bbox = (0, 0, 400, 100)):
        clipped_pdf = input_pdf.replace(".pdf", "_clipped.pdf")
        ocr_pdf = input_pdf.replace(".pdf", "_ocr.pdf")
        
        with fitz.open(input_pdf) as doc:
            with fitz.open() as new_doc:
                for page_num in range(len(doc)):
                    new_page = new_doc.new_page(width=bbox[2] - bbox[0], height=bbox[3] - bbox[1])
                    new_page.show_pdf_page(new_page.rect, doc, page_num, clip=bbox)
                new_doc.save(clipped_pdf)
        
        ocrmypdf.ocr(clipped_pdf, ocr_pdf, deskew=True, force_ocr=True)
        
        pattern = "((?:LI?i?C|BSE|BANK|SMALL|HEALTH).*?(?:FUND|Path|ETF|FTF|EOF|FOF|PLAN|SAVER|FUND\\s*OF\\s*FUND))"
        extracted_titles = {}

        with fitz.open(ocr_pdf) as doc:
            for page_num, page in enumerate(doc):
                page_content = page.get_text("text")
                text = " ".join(page_content.split("\n"))
                if matches := re.findall(pattern, text, re.IGNORECASE):
                    extracted_titles[page_num] = matches[0]
        return extracted_titles
#19 <>
class MahindraManu(Reader,GrandFundData):
    
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) 
#20 <>
class MIRAE(Reader,GrandFundData):
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) 
#21 <>
class MotilalOswal(Reader,GrandFundData): #Lupsum issues
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) 
#22 <>
class NAVI(Reader,GrandFundData): #Lupsum issues
    
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) 
    def get_proper_fund_names(self,path: str):
        pattern = "(Navi.*?(?:Fund|Fund of Fund))"
        title = {}
        with fitz.open(path) as doc:
            for pgn, page in enumerate(doc):
                text = " ".join(page.get_text("text", clip=(0, 0, 500, 150)).split("\n"))
                text = re.sub("[^A-Za-z0-9\\s\\-\\(\\).,]+", "", text).strip()
                if matches := re.findall(pattern, text):
                    title[pgn] = matches[0]
        return title
    
    def _extract_benchmark_data(self,main_key:str,data:str,pattern:str):
        if matches:=re.findall(self.REGEX[pattern],f"{main_key} {data}",re.IGNORECASE):
            return {"benchmark_index":matches[0]}
        return{"benchmark_index":data}
#23 <>
class Nippon(Reader,GrandFundData):
    
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) 
#24
class NJMF(Reader,GrandFundData):
   
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS)
        
    def _update_manager_data(self,main_key:str,manager_data):
        exp ="\\d{1,2} years"
        name = "(?:Mr\\.?|Mrs\\.?|Ms\\.?)\\s*([A-Za-z]+\\s*[A-Za-z]+)"
        since = "(?:since|from)\\s*([A-Za-z]+\\s*\\d{1,2},\\s*\\d{3,4}|inception)"
        nsample, msample, esample = [], [], []
        value = " ".join(manager_data) if isinstance(manager_data,list) else manager_data
        nsample = re.findall(name, value, re.IGNORECASE)
        esample = re.findall(exp, value, re.IGNORECASE)
        msample = re.findall(since, value, re.IGNORECASE)
        final_list = [self._return_manager_data(since=m,name=n,exp=e)for n, m, e in zip(nsample, msample, esample)]
        return {main_key:final_list}
#25
class OldBridge(Reader,GrandFundData):
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) 

#26
class PGIM(Reader, GrandFundData):
    
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) 
        
#27
class PPFAS(Reader,GrandFundData):
    
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) 

    def get_proper_fund_names(self,path: str):
        pattern = "(Parag Parikh.*?(?:Funds?|ETF|Fo?O?F|Plans?))"
        title = {}   
        with fitz.open(path) as doc:
            for pgn, page in enumerate(doc):
                text = " ".join(page.get_text("text", clip=(0,0,400,60)).split("\n"))
                text = re.sub("[^A-Za-z0-9\\s\\-\\(\\).,]+", "", text).strip()
                # print(text)
                if matches := re.findall(pattern, text, re.DOTALL):
                    title[pgn] = " ".join(matches[0].strip().split())
                    # print(matches[0],pgn)
        return title
#28
class QuantMF(Reader,GrandFundData): #Lupsum issues
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand
        Reader.__init__(self,paths_config, self.PARAMS) 
#29 
class Quantum(Reader,GrandFundData): #Lupsum issues
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand
        Reader.__init__(self,paths_config, self.PARAMS) 
#30 <>
class Samco(Reader, GrandFundData):
    
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) 
#31
class SBI(Reader, GrandFundData):
    
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) 
    
    def _extract_manager_data(self, main_key: str, data, pattern: str):
        name = "(?:Mr\\.?|Mrs\\.?|Ms\\.?)\\s*([A-Za-z.]+\\s*[A-Za-z]+)"
        since = "((?:\\(w.e.f\\.?)?[A-Za-z]+\\s*\\d{4}\\s*(?:\\()?)"
        exp = "([0-9]+ years)"

        final_list = []
        manager_data = " ".join(data) if isinstance(data,list) else data
        manager_data =re.sub(self.REGEX["escape"], "", manager_data).strip()
        n = re.findall(name,manager_data, re.IGNORECASE)
        s = re.findall(since,manager_data, re.IGNORECASE)
        e = re.findall(exp,manager_data, re.IGNORECASE)
        
        adjust = lambda target, lst: target[:len(lst)] + ([target[-1]] * abs(len(target) - len(lst)) if lst else [""])
        n,s = adjust(n,e),adjust(s,e)
        for name,since,exp in zip(n,s,e):
            final_list.append(self._return_manager_data(name=name,since=since,exp=exp))
        return {main_key: final_list}

#32
class SBIPassive(Reader, GrandFundData):
    
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) 
        
    def get_proper_fund_names(self,input_pdf:str, bbox = (0, 0, 400, 50)):
        clipped_pdf = input_pdf.replace(".pdf", "_clipped.pdf")
        ocr_pdf = input_pdf.replace(".pdf", "_ocr.pdf")
        
        with fitz.open(input_pdf) as doc:
            with fitz.open() as new_doc:
                for page_num in range(len(doc)):
                    new_page = new_doc.new_page(width=bbox[2] - bbox[0], height=bbox[3] - bbox[1])
                    new_page.show_pdf_page(new_page.rect, doc, page_num, clip=bbox)
                new_doc.save(clipped_pdf)
        
        ocrmypdf.ocr(clipped_pdf, ocr_pdf, deskew=True, force_ocr=True)
        
        pattern = r"((?:SBI|i\s*_|S35).*$)"
        extracted_titles = {}

        with fitz.open(ocr_pdf) as doc:
            for page_num, page in enumerate(doc):
                page_content = page.get_text("text")
                text = " ".join(page_content.split("\n"))
                # print(text)
                if matches := re.findall(pattern, text, re.IGNORECASE):
                    extracted_titles[page_num] = matches[0]
        return extracted_titles
    
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
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) 

#34 <>
class Tata(Reader,GrandFundData):  
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) 
#35 <>
class Taurus(Reader,GrandFundData): #Lupsum issues
    
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) 
#36
class Trust(Reader,GrandFundData):
    
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS)    
#37
class Union(Reader,GrandFundData):   
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS)  
#38
class UTI(Reader,GrandFundData):
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) 
#39 <>
class WhiteOak(Reader,GrandFundData):
    
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) 
#40
class Zerodha(Reader,GrandFundData):
    
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name)
        Reader.__init__(self,paths_config, self.PARAMS)
#41 Aditya Birla
class AdityaBirla(Reader,GrandFundData):
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) 
        
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
    
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) 
    
    def get_proper_fund_names(self,path: str):
        pattern = r"(Axis\s*.+?(?:Fund|Path|ETF|FOF|Path))"
        title = {}
        with fitz.open(path) as doc:
            for pgn, page in enumerate(doc):
                text = " ".join(page.get_text("text", clip=(0, 0, 500, 80)).split("\n"))
                text = re.sub(self.REGEX["escape"], "", text).strip()
                if matches := re.findall(pattern, text, re.DOTALL):
                    title[pgn] = matches[0] 
        return title
    
    def _extract_manager_data(self, main_key:str, data:list,pattern:str):
        final_list = []

        manager_data = " ".join(data) if isinstance(data,list) else data
        manager_data = re.sub(self.REGEX['escape'],"", manager_data).strip()

        if matches:= re.findall(self.REGEX[pattern],manager_data, re.IGNORECASE):
            for match in matches:
                name,exp, since = match
                final_list.append(self._return_manager_data(name=name,since=since,exp=exp))
        return {main_key:final_list}
    
#43 JMMF
class JMMF(Reader,GrandFundData):
    
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) 
    
    def _extract_ptr_data(self, main_key:str,data = ""):
        s = main_key.replace("portfolio_turnover_ratio_","")
        data = f"{ s[:-4]}.{s[-4:]}"
        return {main_key:data}

    def _extract_date_data(self,main_key:str,data:list):
        return{main_key:{"scheme_date":main_key.replace("inception_date_",""),"benchmark":data[1]}}

# 44 Shriram
class Shriram(Reader,GrandFundData):
    def __init__(self, paths_config: str,fund_name:str):
        GrandFundData.__init__(self,fund_name) #load from Grand first
        Reader.__init__(self,paths_config, self.PARAMS) 