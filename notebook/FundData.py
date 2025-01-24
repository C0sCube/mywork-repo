import re
import os
from pdfParse import Reader


class Samco(Reader):
    
    #FUND NAME DETAILS order-> flag, regex_fund_name, font_size, font_color
    fund_data =  [[25,20],r"^(samco|tata).*fund$",20.0,[-1]]
    content_bbox = [(35,120,250,765)]
    
    #CONTENT MANIPULATION PARAMS
    data_conditions = [[9.0,8.0],-1,20.0] #sizes, color, set_size
    
    def __init__(self, path: str,dry:str,fin:str):
        super().__init__(path,dry,fin)
    
    def return_required_header(self,string: str):
            replace_key = string
            if re.match(r'^nav.*', string, re.IGNORECASE):
                replace_key = "nav"
            elif re.match(r"^market", string, re.IGNORECASE):
                replace_key = "market_capital"  
            elif re.match(r"^assets", string, re.IGNORECASE):
                replace_key = "assets_under_management"
            elif re.match(r"^fund", string, re.IGNORECASE):
                replace_key = "fund_manager" 
            elif re.match(r"^scheme", string, re.IGNORECASE):
                replace_key = "scheme_details" 
            elif re.match(r"^investment", string, re.IGNORECASE):
                replace_key = "investment_objective"
            elif re.match(r"^quanti", string, re.IGNORECASE):
                replace_key = "quantitative_data"
            elif re.match(r"^portfolio", string, re.IGNORECASE):
                replace_key = "portfilio" 
            elif re.match(r"^industry", string, re.IGNORECASE):
                replace_key = "industry_allocation_of_equity"       
            return replace_key
    
    #REGEX FUNCTIONS
    def __return_invest_data(self,key:str,data:list):
        investment_objective = data
        values = " ".join(txt for txt in investment_objective)

        data = {
            key:values
        }

        return data

    def __return_scheme_data(self,key:str,data:list):
        scheme_data = data
        main_key = key
        structured_data = {main_key: {}}

        # Patterns
        date_pattern = r"^(.*?date)\s(\d{2}-[A-Za-z]{3}-\d{4})$"
        benchmark_pattern = r"^(Benchmark)\s+(.*)$"
        application_pattern = r"(?:·)?\d+(?:,\d{3})*(?:\.\d+)?/-"

        for data in scheme_data:
            if re.search(date_pattern, data, re.IGNORECASE):
                match = re.match(date_pattern, data, re.IGNORECASE)
                if match:
                    key = match.group(1)
                    value = match.group(2)
                    structured_data[main_key][key] = value
            elif re.search(benchmark_pattern, data, re.IGNORECASE):
                match = re.match(benchmark_pattern, data, re.IGNORECASE)
                if match:
                    key = match.group(1)
                    value = match.group(2)
                    structured_data[main_key][key] = value
            elif re.search(r"\b(min|application)\b", data, re.IGNORECASE):
                matches = re.findall(application_pattern, data, re.IGNORECASE)
                if matches:
                    cleaned_matches = [match.replace('·', '') for match in matches]
                    structured_data[main_key]["min_appl_amt"] = cleaned_matches
            elif re.search(r"\b(additional.* and in multiples of)\b", data, re.IGNORECASE):
                matches = re.findall(application_pattern, data, re.IGNORECASE)
                if matches:
                    cleaned_matches = [match.replace('·', '') for match in matches]
                    structured_data[main_key]["additional_amt"] = cleaned_matches

        return structured_data

    def __return_fund_data(self,key:str,data:list):
        fund_manager = data
        main_key = key
        strucuted_data = {main_key:[]}
        current_entry = None
        name_pattern = r'^(Ms\.|Mr\.)'
        manage_pattern = r'^\(|\)$'
        date_pattern = r'\b\w+ \d{1,2}, \d{4}\b'
        experience_pattern = r'^Total Experience: (.+)$'

        for data in fund_manager:
            if re.match(name_pattern,data):
                if current_entry:
                    strucuted_data[main_key].append(current_entry)
                current_entry = {
                    'name': data.split(",")[0].strip().lower(),
                    'designation': "".join(data.split(",")[1:]).strip().lower()
                }
                #print(data.split(",")[0],"".join(data.split(",")[1:]))
            elif re.match(manage_pattern,data):
                if "inception" in data.lower():
                    current_entry['managing_since'] = 'inception'
                else:
                    date = re.search(date_pattern, data)
                    current_entry['managing_since'] = date.group() if date != None else None
            elif re.match(experience_pattern,data):
                current_entry['total_experience'] = data.split(":")[1].strip().lower()
                #print(data.split(":")[1])

            
        if current_entry:  # Append the last entry
            strucuted_data[main_key].append(current_entry)
                
        return strucuted_data

    def __return_nav_data(self,key:str,data:list):
        main_key = key
        structured_data = {main_key: {}}
        
        growth_pattern = r"((?:Regular|Direct)\s+(?:Growth|IDCW))\s*:?\s*·\s*([\d.]+)"
        
        for line in data:
            matches = re.findall(growth_pattern, line)
            for key, value in matches:
                structured_data[main_key][key.strip().lower()] = float(value)
            
        return structured_data

    def __return_quant_data(self,key:str,data:list):
        qunatitative_data = data
        main_key = key

        strucuted_data = {main_key:{}}
        current_entry = None
        comment = ""

        ratio_pattern = r"\b(ratio|turnover)\b"
        annual_pattern = r'\b(annualised|YTM)\b'
        macaulay_pattern = r"\b(macaulay.*duration)\b"
        residual_pattern = r"\b(residual.*maturity)\b"
        modified_pattern = r"\b(modified.*duration)\b"

        for data in qunatitative_data:
            if re.search(ratio_pattern,data, re.IGNORECASE):
                key = data.split(":")[0].lower().strip()
                value = data.split(":")[1].lower().strip()
            elif re.search(annual_pattern,data, re.IGNORECASE):
                key = data.split(":")[0].lower().strip()
                value = data.split(":")[1].lower().strip()
            elif re.search(macaulay_pattern,data, re.IGNORECASE):
                key = data.split(":")[0].lower().strip()
                value = data.split(":")[1].lower().strip()
            elif re.search(residual_pattern,data, re.IGNORECASE):
                key = data.split(":")[0].lower().strip()
                value = data.split(":")[1].lower().strip()
            elif re.search(modified_pattern,data, re.IGNORECASE):
                key = data.split(":")[0].lower().strip()
                value = data.split(":")[1].lower().strip()
            else:
                comment+= data
            strucuted_data[main_key][key] = value
        
        strucuted_data[main_key]['comment'] = comment

        return strucuted_data

    def __return_aum_data(self,key:str,data:list):
        
        aum = data
        main_key = key
        strucuted_data = {main_key:{}}

        pattern = r"\b\d{1,3}(?:,\d{3})*(?:\.\d+)? Crs\b"

        for data in aum:
            if re.search(r'average', data, re.IGNORECASE):
                match = re.search(pattern, data)
                key = 'avg_aum (crs)'
            elif re.search(pattern, data):
                match = re.search(pattern, data)
                key = "aum (crs)"
            else:
                continue
            
            if match:
                strucuted_data[main_key][key] = float(match.group().split(" ")[0])

        return strucuted_data

    def __return_dummy_data(self,key:str,data:list):
        return {key:{}}


    #REGEX MAPPING FUNCTION
    def match_regex_to_content(self,string:str, data:list, *args):
        
        check_header = string
        
        if re.match(r"^Investment", check_header, re.IGNORECASE):
            return self.__return_invest_data(string,data)
        elif re.match(r"^Scheme", check_header, re.IGNORECASE):
            return self.__return_scheme_data(string, data)
        
        elif re.match(r"^NAV", check_header, re.IGNORECASE):
            return self.__return_nav_data(string, data)
        
        elif re.match(r"^Quant", check_header, re.IGNORECASE):
            return self.__return_quant_data(string, data)
        
        elif re.match(r"^Fund", check_header, re.IGNORECASE):
            return self.__return_fund_data(string, data)
        
        elif re.match(r"^Assets", check_header, re.IGNORECASE):
            return self.__return_aum_data(string, data)
        
        else:
            return self.__return_dummy_data(string,data)
             
class Tata(Reader):
    
    #FUND NAME DETAILS order-> flag, regex_fund_name, font_size, font_color
    fund_data = [[25,20,0,16],r"^(samco|tata|canara).*",12,[-1]]
    content_bbox = [(0,50,160,750)]
    
    #CONTENT MANIPULATION PARAMS
    data_conditions = [[5.0,6.0,8.0], -15570765, 20.0]
    
    
    def __init__(self, path: str,dry:str,fin:str):
        super().__init__(path,dry,fin)
    
    def return_required_header(self,string: str):
            replace_key = string
            if re.match(r'^nav.*', string, re.IGNORECASE):
                replace_key = "nav"
            elif re.match(r"^market", string, re.IGNORECASE):
                replace_key = "market_capital"  
            elif re.match(r"^assets", string, re.IGNORECASE):
                replace_key = "assets_under_management"
            elif re.match(r"^fund", string, re.IGNORECASE):
                replace_key = "fund_manager" 
            elif re.match(r"^scheme", string, re.IGNORECASE):
                replace_key = "scheme_details" 
            elif re.match(r"^investment", string, re.IGNORECASE):
                replace_key = "investment_objective"
            elif re.match(r"^quanti", string, re.IGNORECASE):
                replace_key = "quantitative_data"
            elif re.match(r"^portfolio", string, re.IGNORECASE):
                replace_key = "portfilio" 
            elif re.match(r"^industry", string, re.IGNORECASE):
                replace_key = "industry_allocation_of_equity"       
            return replace_key
    
    
    #REGEX FUNCTIONS
    def __extract_inv_data(self,key:str, data:list):
        return
    
    def __extract_fund_data(self,key:str, data:list):
        return
    
    def __extract_nav_data(self,key:str, data:list):
        return
    
    def __extract_turn_data(self,key:str, data:list):
        return
    
    def __extract_bench_data(self,key:str, data:list):
        return
    
    def __extract_load_data(self,key:str, data:list):
        return
    
    def __extract_aum_data(self,key:str, data:list):
        return
    
    def __extract_trkerr_data(self,key:str, data:list):
        return
    
    def __extract_volat_data(self,key:str, data:list):
        return
    
    def __extract_dum_data(self,key,data:list):
        return


    def match_regex_to_content(self, string:str, data:list, *args):
        return 
    
class FranklinTempleton(Reader):
    
    #FUND NAME DETAILS order-> flag, regex_fund_name, font_size, font_color
    fund_data =  [[25,20],r"^(Franklin|Templeton).*$",14.0,[-1]]
    content_bbox = [(0,5,180,812)]
    
    #CONTENT MANIPULATION PARAMS
    data_conditions = [[7],-16751720,20.0] #sizes, color, set_size
    
    def __init__(self, path: str,dry:str,fin:str):
        super().__init__(path,dry,fin)