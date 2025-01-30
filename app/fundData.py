import re, os, pprint
from app.pdfParse import Reader
from app.regex import Regex
import fitz


class Samco(Reader):
    
    PARAMS = {
        'fund': [[25,20],r"^(samco|tata).*fund$",[18,28],[-1]], #FUND NAME DETAILS order-> [flag], regex_fund_name, range(font_size), [font_color]
        'clip_bbox': [(35,120,250,765)],
        'line_x': 200.0,
        'data': [[7,10],[-1],20.0,['Inter-SemiBold']] #sizes, color, set_size font_name
    }
    
    def __init__(self, path: str,dry:str,fin:str, rep:str):
        super().__init__(path,dry,fin,rep, self.PARAMS)

    
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

    def __return_nav_data(self,main_key:str,data:list):
        pattern = r'(Regular Growth|Direct Growth|Regular IDCW|Direct IDCW)[\s:]+([\d]+\.\d+)'
        
        final_dict = {}
        for text in data:
            text = text.lower()
            matches = re.findall(pattern, text, re.IGNORECASE)
            for key, value in matches:
                if '.' in value:
                    final_dict[key] = float(value)
                else:
                    final_dict[key] = 'NA'
        return {main_key:final_dict}

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
                value = Regex.extract_decimals(data.split(":")[1].lower().strip())
            elif re.search(annual_pattern,data, re.IGNORECASE):
                key = data.split(":")[0].lower().strip()
                value = Regex.extract_decimals(data.split(":")[1].lower().strip())
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
    
    PARAMS = {
        'fund': [[25,20,0,16],r"^(samco|tata).*(fund|etf|fof|eof|funds|plan|\))$",[10,20],[-1]], #[flag], regex_fund_name, range(font_size), [font_color]
        'clip_bbox': [(0,50,160,750)],
        'line_x': 160.0,
        'data': [[5,8],[-15570765],20.0,['Swiss721BT-BoldCondensed']] #sizes, color, set_size font_name
    }
    
    
    def __init__(self, path: str,dry:str,fin:str, rep:str):
        super().__init__(path,dry,fin,rep, self.PARAMS)
    
    def return_required_header(self,string: str):
            replace_key = string
            if re.match(r'^nav.*', string, re.IGNORECASE):
                replace_key = "nav"
            elif re.match(r"^expense.*", string, re.IGNORECASE):
                replace_key = "expense_ratio"
            elif re.match(r"^volatility.*", string, re.IGNORECASE):
                replace_key = "volatility_measures"
            elif re.match(r"^.*investors$", string, re.IGNORECASE):
                replace_key = "add_investment"
            elif re.match(r".*investment$", string, re.IGNORECASE):
                replace_key = "min_investment"
            return replace_key
    
    
    #REGEX FUNCTIONS
    def __extract_inv_data(self,key:str, data:list):            
        return {key: ' '.join(data)}
    
    def __extract_nav_data(self,main_key:str, data:list):
        nav_data = data
        final_dict = {}
        pattern = r'(Regular - Growth|Direct - Growth|Regular - IDCW|Direct - IDCW)[\s:]+([\d]+\.\d+)'
        
        final_dict = {}
        for text in nav_data:
            text = text.lower()
            matches = re.findall(pattern, text, re.IGNORECASE)
            for key, value in matches:
                if '.' in value:
                    final_dict[key] = float(value)
                else:
                    final_dict[key] = 'NA'
        return {main_key:final_dict}
    
    def __extract_turn_data(self,main_key:str, data:list):
        turn_data = data
        final_dict = {}
        for text in turn_data:
            if re.match(r'^Portfolio.*',text, re.IGNORECASE):
                if matches := re.search(r"\d+\.\d+", text):
                    final_dict['portfolio_turnover_ratio(%)'] = Regex.extract_decimals(matches.group())
        return {main_key:final_dict}
    
    def __extract_load_data(self,main_key:str, data:list):
        
        load_data = data
        processing_flag = False
        entry_load, exit_load = "",""
        final_dict = {}
        for text in load_data:
            text = text.strip()
            if re.match(r'^Entry Load', text, re.IGNORECASE):
                processing_flag = False
            if re.match(r"^Exit Load", text,re.IGNORECASE):
                processing_flag = True
            
            if processing_flag:
                if "Not Applicable" in text:
                    entry_load += "Not Applicable"
                else:
                    exit_load+= f' {text}'
            else:
                if "Not Applicable" in text:
                    entry_load+= "Not Applicable"
                else:
                    entry_load+= f' {text}'
        final_dict['entry_load'] = entry_load.replace("Entry Load","").strip()
        final_dict['exit_load'] = exit_load.replace("Exit Load","").strip()
        
        return {main_key:final_dict}
    
    def __extract_manager_data(self,main_key:str, data:list):
        # Pattern to match content outside ()
        outside_pattern = r"^[^(]+"
        # Pattern to match content inside ()
        inside_pattern = r"\((.*?)\)"
        final_list = []
        manager_data = " ".join(data).split(',') #contains , seperated manager data
        for text in manager_data:
            text = text.lower()
            # Extract outside parentheses
            outside_match = re.search(outside_pattern, text)
            outside_text = outside_match.group().strip() if outside_match else ""

            # Extract inside parentheses
            inside_match = re.search(inside_pattern, text)
            inside_text = inside_match.group(1).strip() if inside_match else ""
            final_list.append({
                'name': outside_text,
                "experience": inside_text
            })
        
        return {main_key:final_list}  
    
    def __extract_volat_data(self,main_key:str, data:list):
        volat_data = data
        final_dict = {}
        final_dict['comment'] = ""
        for text in volat_data:
            text = text.lower()
            if re.match(r'^std.*',text, re.IGNORECASE):
                content = [Regex.extract_decimals(value) for value in text.split(" ")[-2:]]
                final_dict['std_deviaton'] = {
                    "fund": content[0],
                    "benchmark": content[1]
                }
            elif re.match(r'^sharpe.*',text, re.IGNORECASE):
                content = [Regex.extract_decimals(value) for value in text.split(" ")[-2:]]
                final_dict['sharpe_ratio'] = {
                    "fund": content[0],
                    "benchmark": content[1]
                }
            elif re.match(r'^r squared.*',text, re.IGNORECASE):
                content = [Regex.extract_decimals(value) for value in text.split(" ")[-2:]]
                final_dict['r_squared_ratio'] = {
                    "fund": content[0],
                    "benchmark": content[1]
                }
            elif re.match(r'^treynor.*',text, re.IGNORECASE):
                content = [Regex.extract_decimals(value) for value in text.split(" ")[-2:]]
                final_dict['treynor_ratio'] = {
                    "fund": content[0],
                    "benchmark": content[1]
                }
            elif re.match(r'^jenson.*',text, re.IGNORECASE):
                content = [Regex.extract_decimals(value) for value in text.split(" ")[-2:]]
                final_dict['jenson_ratio'] = {
                    "fund": content[0],
                    "benchmark": content[1]
                }
            elif re.match(r'^portfolio.*',text, re.IGNORECASE):
                content = [Regex.extract_decimals(value) for value in text.split(" ")[-2:]]
                final_dict['portfolio_beta'] = {
                    "fund": content[0],
                    "benchmark": content[1]
                }
            else:
                final_dict['comment']+= text
        
        return {main_key:final_dict}
    
    def __extract_exp_data(self,main_key:str, data:list):
        exp_data = data
        final_dict = {}
        for text in exp_data:
            key, value = "",""
            if "direct" in text.lower():
                key, value = text.split(" ")
                final_dict[key.lower()] = float(value) if value not in ['NA','na',r'N\A',r'n\a'] else value
            elif "regular" in text.lower():
                key, value = text.split(" ")
                final_dict[key.lower()] = float(value) if value not in ['NA','na',r'N\A',r'n\a'] else value
        return {main_key:final_dict}
    
    def __extract_dum_data(self,key,data:list):
        return {key:data}
    
    def __extract_singular_data(self,key,data:list):
        return{key:data[0] if len(data) == 1 else data}
    
    def __extract_singular_num_data(self,key,data:list):
        return{key:Regex.extract_decimals(data[0]) if len(data) == 1 else data}

    def match_regex_to_content(self, string:str, data:list, *args):
        check_header = string
        
        if re.match(r"^investment.*", check_header, re.IGNORECASE):
            return self.__extract_inv_data(string,data)
        elif re.match(r"^nav.*", check_header, re.IGNORECASE):
            return self.__extract_nav_data(string, data)
        elif re.match(r"^turn.*", check_header, re.IGNORECASE):
            return self.__extract_turn_data(string, data)
        elif re.match(r"^volat.*", check_header, re.IGNORECASE):
            return self.__extract_volat_data(string, data)
        elif re.match(r"^load.*", check_header, re.IGNORECASE):
            return self.__extract_load_data(string, data)
        elif re.match(r"^turn.*", check_header, re.IGNORECASE):
            return self.__extract_turn_data(string, data)
        elif re.match(r".*(manager|managers)$", check_header, re.IGNORECASE):
            return self.__extract_manager_data(string, data)
        elif re.match(r"^expense.*", check_header, re.IGNORECASE):
            return self.__extract_exp_data(string, data)
        elif re.match(r"^(benchmark|date).*", check_header, re.IGNORECASE):
            return self.__extract_singular_data(string, data)
        elif re.match(r"^(fund_size|monthly).*", check_header, re.IGNORECASE):
            return self.__extract_singular_num_data(string, data)
        else:
            return self.__extract_dum_data(string,data)    

class FranklinTempleton(Reader):
    
    PARAMS = {
        'fund': [[25,20],r"^(Franklin|Templeton).*$",[16,24],[-65794]], #[flag], regex_fund_name, range(font_size), [font_color]
        'clip_bbox': [(0,100,180,812)],
        'line_x': 180.0,
        'data': [[6,9],[-16751720],20.0,['ZurichBT-BoldCondensed']] #sizes, color, set_size font_name
    }
    
    def __init__(self, path: str,dry:str,fin:str, rep:str):
        super().__init__(path,dry,fin,rep, self.PARAMS)
        
    def return_required_header(self,string: str):
        replace_key = string
        if re.match(r'^nav.*', string, re.IGNORECASE):
            replace_key = "nav"
        elif re.match(r"^date", string, re.IGNORECASE):
            replace_key = "date_of_allotment"
        elif re.match(r"^fund_mana", string, re.IGNORECASE):
            replace_key = "fund_manager(s)" 
        elif re.match(r"^investment", string, re.IGNORECASE):
            replace_key = "investment_objective"
        elif re.match(r"^quanti", string, re.IGNORECASE):
            replace_key = "quantitative_data"
        elif re.match(r"^portfolio", string, re.IGNORECASE):
            replace_key = "portfilio" 
        elif re.match(r"^volatility", string, re.IGNORECASE):
            replace_key = "volatility_measures"
        elif re.match(r"^exit", string, re.IGNORECASE):
            replace_key = "exit_load"
        elif re.match(r"^entry", string, re.IGNORECASE):
            replace_key = "entry_load"
        elif re.match(r"^benchmark", string, re.IGNORECASE):
            replace_key = "benchmark"
        elif re.match(r"^fund_size", string, re.IGNORECASE):
            replace_key = "fund_size"      
        return replace_key   

    #REGEX FUNCTIONS
    def __extract_inv_data(self,key:str, data:list):            
        return {key: ' '.join(data)}
    
    def __extract_fund_size_data(self, main_key:str, data:list):
        fund_data = data
        pattern = r'(Month End|Monthly Average)[\s]+([\d]+\.\d+)'
        final_dict = {}
        for text in fund_data:
            text = text.lower()
            matches = re.findall(pattern, text, re.IGNORECASE)
            for key, value in matches:
                final_dict[key] = Regex.extract_decimals(value)
        return {main_key:final_dict}
    
    def __extract_turnover_data(self, main_key:str, data:list):
        fund_data = data
        pattern = r'^(Portfolio Turnover|Total Portfolio).*[\s]+([\d]+\.\d+)'
        final_dict = {}
        for text in fund_data:
            text = text.lower()
            matches = re.findall(pattern, text, re.IGNORECASE)
            for key, value in matches:
                final_dict[key] = Regex.extract_decimals(value)
        return {main_key:final_dict}
    
    def __extract_nav_data(self,main_key:str, data:list):
        nav_data = data
        final_dict = {}
        pattern = r'(Growth Plan|IDCW Plan|Direct - Growth Plan|Direct - IDCW Plan)[\s]+([\d]+\.\d+)'
        
        final_dict = {}
        for text in nav_data:
            text = text.lower()
            matches = re.findall(pattern, text, re.IGNORECASE)
            for key, value in matches:
                final_dict[key] = Regex.extract_decimals(value)
        return {main_key:final_dict}
    
    def __extract_volat_data(self,main_key:str, data:list):
        volat_data = data
        final_dict = {}
        pattern = r'(Sharpe Ratio|Standard Deviation|Beta|Annualised)[\s]+([\d]+\.\d+)'
        
        final_dict = {}
        for text in volat_data:
            text = text.lower().replace("*","").strip()
            matches = re.findall(pattern, text, re.IGNORECASE)
            for key, value in matches:
                final_dict[key.strip()] = Regex.extract_decimals(value)
        return {main_key:final_dict}
    
    def __extract_manager_data(self,main_key:str, data:list):
        return {main_key:" ".join(data)} 
    
    def __extract_dum_data(self,main_key:str, data:list):
        return {main_key:data} 
    
    def __extract_singular_data(self,key,data:list):
        return{key:data[0] if len(data) == 1 else data}
    
    def __extract_load_data(self,main_key:str, data:list):
    
        load_data = data
        processing_flag = False
        entry_load, exit_load = "",""
        final_dict = {}
        for text in load_data:
            text = text.strip()
            if re.match(r'^entry Load', text, re.IGNORECASE):
                processing_flag = False
            if re.match(r"^exit Load", text,re.IGNORECASE):
                processing_flag = True
            
            if processing_flag:
                if "il" in text:
                    entry_load += "nil"
                else:
                    exit_load+= f' {text}'
            else:
                if "nil" in text:
                    entry_load+= "nil"
                else:
                    entry_load+= f' {text}'
        final_dict['entry_load'] = entry_load.replace("ENTRY LOAD","").strip()
        final_dict['exit_load'] = exit_load.replace("EXIT LOAD","").strip()
        
        return {main_key:final_dict}
    
    def match_regex_to_content(self, string:str, data:list, *args):
        check_header = string
        
        if re.match(r"^(investment|type_of|scheme|multiples|minimum).*", check_header, re.IGNORECASE):
            return self.__extract_inv_data(string,data)
        elif re.match(r"^nav.*", check_header, re.IGNORECASE):
            return self.__extract_nav_data(string, data)
        elif re.match(r"^fund_mana.*", check_header, re.IGNORECASE):
            return self.__extract_manager_data(string, data)
        elif re.match(r"^(benchmark|date)", check_header, re.IGNORECASE):
            return self.__extract_singular_data(string, data)
        elif re.match(r"^fund_size.*", check_header, re.IGNORECASE):
            return self.__extract_fund_size_data(string, data)
        elif re.match(r"^turnover", check_header, re.IGNORECASE):
            return self.__extract_turnover_data(string, data)
        elif re.match(r"^load", check_header, re.IGNORECASE):
            return self.__extract_load_data(string, data)
        elif re.match(r"^volat", check_header, re.IGNORECASE):
            return self.__extract_volat_data(string, data)
        else:
            return self.__extract_dum_data(string,data)
    
    
class Bandhan(Reader):
    PARAMS = {
        'fund': [[20],r"^Bandhan.*(Fund|Funds|Plan|ETF)$", [13,24],[-1361884]], #FUND NAME DETAILS order-> flag, regex_fund_name, font_size, font_color
        'clip_bbox': [(0,80,200,812)],
        'line_x': 200.0,
        'data': [[6, 8], [-14475488], 20.0, ['Ubuntu-Bold']] #sizes, color, set_size font_name
    }
    
    def __init__(self, path: str,dry:str,fin:str, rep:str):
        super().__init__(path,dry,fin,rep, self.PARAMS) 
        
    def return_required_header(self,string: str):
        replace_key = string
        if re.match(r'^nav.*', string, re.IGNORECASE):
            replace_key = "nav"
        elif re.match(r"^about.*", string, re.IGNORECASE):
            replace_key = "about"
        elif re.match(r"^fund.*", string, re.IGNORECASE):
            replace_key = "fund_manager(s)"
        elif re.match(r"^other", string, re.IGNORECASE):
            replace_key = "volatility_measures"
        elif re.match(r".*investment$", string, re.IGNORECASE):
            replace_key = "min_investment"
        return replace_key
    
    #REGEX
    def __extract_dum_data(self,key,data:list):
        return {key:data}
    
    def __extract_inv_data(self,key:str, data:list):            
        return {key: ' '.join(data)}
    
    def __extract_total_expense_data(self,main_key:str, data:list):
        expense_data = data
        final_dict = {}
        pattern = r'(Regular|Direct)[\s]+([\d]+\.\d+)'
        
        final_dict = {}
        for text in expense_data:
            text = text.lower()
            matches = re.findall(pattern, text, re.IGNORECASE)
            for key, value in matches:
                final_dict[key] = Regex.extract_decimals(value)
        return {main_key:final_dict}
    
    def __extract_nav_data(self,main_key:str, data:list):
        nav_data = data
        final_dict = {}
        pattern = r'(Regular Plan Growth|Regular Plan IDCW|Direct Plan Growth|Direct Plan IDCW)[\s]+([\d]+\.\d+)'
        
        final_dict = {}
        for text in nav_data:
            text = text.lower().replace("@","")
            matches = re.findall(pattern, text, re.IGNORECASE)
            for key, value in matches:
                final_dict[key] = Regex.extract_decimals(value)
        return {main_key:final_dict}
    
    def __extract_port_data(self,main_key:str, data:list):
        nav_data = data
        final_dict = {}
        pattern = r'(Equity|Aggregate|Tracking Error.*)[\s]+([\d]+\.\d+)'
        
        final_dict = {}
        for text in nav_data:
            text = text.lower().replace('^','').replace('(Annualized)',"")
            matches = re.findall(pattern, text, re.IGNORECASE)
            for key, value in matches:
                final_dict[key] = Regex.extract_decimals(value)
        return {main_key:final_dict}
    
    def __extract_volat_data(self,main_key:str, data:list):
        nav_data = data
        final_dict = {}
        pattern = r'(Beta|R Squared|Standard Deviation \(Annualized\)|Sharpe\*|Modified Duration|Average Maturity|Macaulay Duration|Yield to Maturity)[\s]+([\d]+\.\d+)'
        
        final_dict = {}
        for text in nav_data:
            text = text.lower().replace('^','').replace('(Annualized)',"")
            matches = re.findall(pattern, text, re.IGNORECASE)
            for key, value in matches:
                final_dict[key] = Regex.extract_decimals(value)
        return {main_key:final_dict}
    
    def __extract_singular_data(self,key,data:list):
        return{key:data[0] if len(data) == 1 else data}
    
    def __extract_singular_num_data(self,key,data:list):
        return{key:Regex.extract_decimals(data[0]) if len(data) == 1 else data}

    def __extract_manager_data(self,main_key:str, data:list):
        return{main_key: " ".join(data)}
    
    def match_regex_to_content(self, string:str, data:list, *args):
        check_header = string
        
        if re.match(r"^(about|investment|sip|option).*", check_header, re.IGNORECASE):
            return self.__extract_inv_data(string,data)
        elif re.match(r"^nav.*", check_header, re.IGNORECASE):
            return self.__extract_nav_data(string, data)
        elif re.match(r"^(category|inception|benchmark).*", check_header, re.IGNORECASE):
            return self.__extract_singular_data(string, data)
        elif re.match(r"^fund.*", check_header, re.IGNORECASE):
            return self.__extract_manager_data(string, data)
        elif re.match(r"^portfolio.*", check_header, re.IGNORECASE):
            return self.__extract_port_data(string, data)
        elif re.match(r"^volat.*", check_header, re.IGNORECASE):
            return self.__extract_volat_data(string, data)
        elif re.match(r"^(month|monthly).*", check_header, re.IGNORECASE):
            return self.__extract_singular_data(string, data)
        elif re.match(r"^total.*", check_header, re.IGNORECASE):
            return self.__extract_total_expense_data(string, data)
        else:
            return self.__extract_dum_data(string,data) 
          
        
class Helios(Reader):
    
    PARAMS = {
        'fund': [[20], r'^Helios.*Fund$',[16,24],[-1]],
        'clip_box': [(0,5,245,812)],
        'line_x': 245.0,
        'data': [[7,10], [-1,-2545112], 30.0, ['Poppins-SemiBold']]
    }
    
    def __init__(self, path: str,dry:str,fin:str, rep:str):
        super().__init__(path,dry,fin,rep, self.PARAMS) 
        
    def return_required_header(self,string: str):
        replace_key = string
        if re.match(r'^nav.*', string, re.IGNORECASE):
            replace_key = "nav"
        elif re.match(r'.*objective$', string, re.IGNORECASE):
            replace_key = "investment_objective"
        return replace_key
    #REGEX
    
    def __extract_dum_data(self,key,data:list):
        return {key:data}
    
    def __extract_inv_data(self,key:str, data:list):            
        return {key: ' '.join(data)}

    def __extract_total_expense_data(self,main_key:str, data:list):
        expense_data = data
        final_dict = {}
        pattern = r'(Regular Plan|Direct Plan)[\s]+([\d]+\.\d+)'
        
        final_dict = {}
        for text in expense_data:
            text = text.lower()
            matches = re.findall(pattern, text, re.IGNORECASE)
            for key, value in matches:
                final_dict[key] = Regex.extract_decimals(value)
        return {main_key:final_dict}
    
    def __extract_nav_data(self,main_key:str, data:list):
        nav_data = data
        final_dict = {}
        pattern = r'(Regular Plan - Growth Option|Regular Plan - IDCW Option|Direct Plan - Growth Option|Direct Plan - IDCW Option)[\s]+([\d]+\.\d+)'
        
        final_dict = {}
        for text in nav_data:
            text = text.lower()
            matches = re.findall(pattern, text, re.IGNORECASE)
            for key, value in matches:
                final_dict[key.strip()] = Regex.extract_decimals(value)
        return {main_key:final_dict}

    def __extract_aum_data(self,main_key:str, data:list):
        aum_data = data
        final_dict = {}
        pattern = r'(Monthly Avg AUM|Month end AUM)[\s]+([\d]+\.\d+)'
        
        final_dict = {}
        for text in aum_data:
            text = text.lower()
            matches = re.findall(pattern, text, re.IGNORECASE)
            for key, value in matches:
                final_dict[key.strip()] = Regex.extract_decimals(value)
        return {main_key:final_dict}
    
    def match_regex_to_content(self, string:str, data:list):
        check_header = string
        if re.match(r"^(investment).*", check_header, re.IGNORECASE):
            return self.__extract_inv_data(string,data)
        elif re.match(r"^total.*", check_header, re.IGNORECASE):
            return self.__extract_total_expense_data(string, data)
        elif re.match(r"^nav.*", check_header, re.IGNORECASE):
            return self.__extract_nav_data(string, data)
        return self.__extract_dum_data(string,data) 
          
class Edelweiss(Reader):
    
    PARAMS = {
        'fund': [[20], r'^(Edelweiss|Bharat)',[12,20],[-16298334]],
        'clip_box': [(0,5,410,812)],
        'line_x': 410.0,
        'data': [[5,9], [-16298334,-6204255], 20.0, ['Roboto-Bold']]
    }
    
    def __init__(self, path: str,dry:str,fin:str, rep:str):
        super().__init__(path,dry,fin,rep,self.PARAMS)
        
    
    def get_proper_fund_names(self,path:str,pages:list):
        
        doc = fitz.open(path)
        
        final_fund_names = dict()
        final_objectives = dict()
        
        for pgn in range(doc.page_count):
            fund_names = ''
            objective_names = ''
            
            if pgn in pages:
                page = doc[pgn]            
                blocks = page.get_text("dict")['blocks']
                for count,block in enumerate(blocks):
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            text = span['text'].strip()
                            if count in range(1,2):  #contains fund name        
                                fund_names += f'{text} '
                            
                            if count in range(4,5): #contains objectives
                                objective_names+= f'{text} '
                           
            final_fund_names[pgn] = fund_names
            final_objectives[pgn] = objective_names

        return final_fund_names, final_objectives
    
    def return_required_header(self,string: str):
        replace_key = string
        if re.match(r'^nav.*', string, re.IGNORECASE):
            replace_key = "nav"
        elif re.match(r"^total.*", string, re.IGNORECASE):
            replace_key = "total_expense_ratio"
        elif re.match(r"^fund.*", string, re.IGNORECASE):
            replace_key = "fund_manager(s)"
        elif re.match(r"^benchmark", string, re.IGNORECASE):
            replace_key = "benchmark"
        elif re.match(r'^plan', string, re.IGNORECASE):
            replace_key = "plan/options"
        elif re.match(r'^exit', string, re.IGNORECASE):
            replace_key = "exit_load"
        return replace_key                      

    #REGEX 
    def __extract_dum_data(self,key,data:list):
        return {key:data}
    
    def match_regex_to_content(self, string:str, data:list, *args):
        check_header = string
        
        # if re.match(r"^(about|investment|sip|option).*", check_header, re.IGNORECASE):
        #     return self.__extract_inv_data(string,data)
        # elif re.match(r"^nav.*", check_header, re.IGNORECASE):
        #     return self.__extract_nav_data(string, data)
        # elif re.match(r"^(category|inception|benchmark).*", check_header, re.IGNORECASE):
        #     return self.__extract_singular_data(string, data)
        # elif re.match(r"^fund.*", check_header, re.IGNORECASE):
        #     return self.__extract_manager_data(string, data)
        # elif re.match(r"^portfolio.*", check_header, re.IGNORECASE):
        #     return self.__extract_port_data(string, data)
        # elif re.match(r"^volat.*", check_header, re.IGNORECASE):
        #     return self.__extract_volat_data(string, data)
        # elif re.match(r"^(month|monthly).*", check_header, re.IGNORECASE):
        #     return self.__extract_singular_data(string, data)
        # elif re.match(r"^total.*", check_header, re.IGNORECASE):
        #     return self.__extract_total_expense_data(string, data)
        # else:
        return self.__extract_dum_data(string,data) 


class HSBC(Reader):
    
    PARAMS = {
        'fund': [[20,16], r'^(HSBC|Bharat).*Fund$',[12,20],[-1237724]],
        'clip_box': [(0,5,180,812)],
        'line_x': 180.0,
        'data': [[6,8], [-16777216], 30.0, ['Arial-BoldMT']]
    }
    
    def __init__(self, path: str,dry:str,fin:str, rep:str):
        super().__init__(path,dry,fin,rep)            
        
class Invesco(Reader):
    
    PARAMS = {
        'fund': [[20,16], r'^(Invesco|Bharat).*Fund$',[12,20],[-16777216]],
        'clip_box': [(0,135,185,812)],
        'line_x': 180.0,
        'data': [[7,9], [-16777216], 30.0, ['Graphik-Semibold']]
    }
    
    def __init__(self, path: str,dry:str,fin:str, rep:str):
        super().__init__(path,dry,fin,rep)
        
class ITI(Reader):
    
    PARAMS = {
        'fund': [[20,16], r'^(ITI|Bharat).*Fund$',[14,24],[-1]],
        'clip_box': [(0,105,180,812)],
        'line_x': 180.0,
        'data': [[5,8], [-1688818,-1165277], 30.0, ['Calibri-Bold']]
    }
    
    def __init__(self, path: str,dry:str,fin:str, rep:str):
        super().__init__(path,dry,fin,rep) 

class JMMF(Reader):
    
    PARAMS = {
        'fund': [[20,16], r'^(JM|Bharat).*Fund$',[14,24],[-10987173]],
        'clip_box': [(390,105,596,812)],
        'line_x': 390.0,
        'data': [[6,9], [-1], 30.0, ['MyriadPro-BoldCond']]
    }
    
    def __init__(self, path: str,dry:str,fin:str, rep:str):
        super().__init__(path,dry,fin,rep)

class DSP(Reader):
    
    PARAMS = {
        'fund': [[20,16], r'^(DSP|Bharat).*(Fund|ETF|FTF|FOF)$|^(DSP|Bharat)',[14,24],[-1]],
        'clip_box': [(0,5,120,812),[480,5,596,812]],
        'line_x': 120.0,
        'data': [[7,10], [-16777216], 30.0, ['TrebuchetMS-Bold']]
    }
    
    
    def __init__(self, path: str,dry:str,fin:str, rep:str):
        super().__init__(path,dry,fin,rep)
        
class BankOfIndia(Reader):
    
    PARAMS = {
        'fund': [[20,16], r'^(DSP|Bharat).*(Fund|ETF|FTF|FOF)$|^(DSP|Bharat)',[14,24],[-1]],
        'clip_box': [(0,5,120,812),[480,5,596,812]],
        'line_x': 120.0,
        'data': [[7,10], [-16777216], 30.0, ['TrebuchetMS-Bold']]}
    
    def __init__(self, path: str,dry:str,fin:str, rep:str):
        super().__init__(path,dry,fin,rep)
        
class Kotak(Reader):
    
    PARAMS = {
        'fund': [[20,16], r'^(Kotak|Bharat).*(Fund|ETF|FTF|FOF)$|^Kotak',[12,20],[-15319437]],
        'clip_box': [(0,5,150,812),],
        'line_x': 150.0,
        'data': [[5,8], [-15445130,-14590595], 30.0, ['Frutiger-Bold']]}
    
    def __init__(self, path: str,dry:str,fin:str, rep:str):
        super().__init__(path,dry,fin,rep)

class LIC(Reader):
    
    PARAMS = {
        'fund': [[20,16], r'^(LIC|Bharat).*(Fund|ETF|FTF|FOF)$',[12,20],[-15319437]],
        'clip_box': [(0,5,150,812),],
        'line_x': 150.0,
        'data': [[5,8], [-15445130,-14590595], 30.0, ['Frutiger-Bold']]}
    
    def __init__(self, path: str,dry:str,fin:str, rep:str):
        super().__init__(path,dry,fin,rep)          

class MahindraManu(Reader):
    PARAMS = {
        'fund': [[20,16], r'',[12,20],[-15319437]],
        'clip_box': [(0,65,200,812)],
        'line_x': 200.0,
        'data': [[7,10], [-7392877,-16749906,-7953091,-7767504,-12402502,-945627,], 30.0, ['QuantumRise-Bold','QuantumRise','QuantumRise-Semibold']]}
    
    def __init__(self, path: str,dry:str,fin:str, rep:str):
        super().__init__(path,dry,fin,rep)
        
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

class MotilalOswal(Reader):
    PARAMS = {
        'fund': [[20,16], r'^(Motilal|Oswal).*(Fund|ETF|EOF|FOF|FTF|Path)$',[20,28],[-13616547]],
        'clip_box': [(0,65,170,812)],
        'line_x': 170.0,
        'data': [[7,12], [-13948375], 30.0, ['Calibri-Bold']]}
    
    def __init__(self, path: str,dry:str,fin:str, rep:str):
        super().__init__(path,dry,fin,rep)   

class NJMF(Reader):
    PARAMS = {
        'fund': [[20,16,0], r'^(NJ).*(Fund|ETF|EOF|FOF|FTF|Path)$',[16,24],[-13604430]],
        'clip_box': [(0,5,250,812)],
        'line_x': 250.0,
        'data': [[6,11], [-14475488], 30.0, ['Swiss721BT-Medium']]}
    
    def __init__(self, path: str,dry:str,fin:str, rep:str):
        super().__init__(path,dry,fin,rep)
                
class QuantMF(Reader):
    PARAMS = {
        'fund': [[16,0], r'^(quant).*(Fund|ETF|EOF|FOF|FTF|Path)$',[16,24],[-13604430]],
        'clip_box': [(0,5,180,812)],
        'line_x': 180.0,
        'data': [[6,11], [-16777216], 30.0, ['Calibri,Bold',]]}
    
    def __init__(self, path: str,dry:str,fin:str, rep:str):
        super().__init__(path,dry,fin,rep)

class Sundaram(Reader):
    PARAMS = {
        'fund': [[4,0], r'^(Sundaram).*(Fund|ETF|EOF|FOF|FTF|Path|Fund*|Fund -)$|^Sundaram',[14,18],[-16625248]],
        'clip_box': [(0,5,220,812)],
        'line_x': 220.0,
        'data': [[6,13], [-1], 30.0, ['UniversNextforMORNW02-Cn',]]}
    
    def __init__(self, path: str,dry:str,fin:str, rep:str):
        super().__init__(path,dry,fin,rep)

class Taurus(Reader):
    PARAMS = {
        'fund': [[4,20], r'^(Taurus).*(Fund|ETF|EOF|FOF|FTF|Path|Fund*)$',[16,24],[-9754846]],
        'clip_box': [(0,65,210,812)],
        'line_x': 210.0,
        'data': [[6,12], [-9754846], 30.0, ['Calibri-Bold']]}
    
    def __init__(self, path: str,dry:str,fin:str, rep:str):
        super().__init__(path,dry,fin,rep)

class Trust(Reader):
    
    PARAMS = {
        'fund': [[4,20], r'^(Trust).*(Fund|ETF|EOF|FOF|FTF|Path|Fund*)$',[16,22],[-1]],
        'clip_box': [(0,65,180,812)],
        'line_x': 180.0,
        'data': [[7,12], [-1, -14475488], 30.0, ['Roboto-Bold']]}
    
    def __init__(self, path: str,dry:str,fin:str, rep:str):
        super().__init__(path,dry,fin,rep)

class UTI(Reader):
    PARAMS = {
        'fund': [[20], r'^(UTI).*(Fund|ETF|EOF|FOF|FTF|Path|Fund\*|Plan\*|Duration)$',[14,24],[-65794]],
        'clip_box': [(0,65,200,812)],
        'line_x': 200.0,
        'data': [[7,10], [-65794,-1], 30.0, ['Calibri-Bold']]}
    
    def __init__(self, path: str,dry:str,fin:str, rep:str):
        super().__init__(path,dry,fin,rep)

class WhiteOak(Reader):
    PARAMS = {
        'fund': [[20], r'^(whiteOak).*(Fund|ETF|EOF|FOF|FTF|Path|Fund\*|Plan\*|Duration)$',[16,24],[-13159371]],
        'clip_box': [(0, 85, 240, 812)],
        'line_x': 240.0,
        'data': [[7,11], [-65794,-1], 30.0, ['MyriadPro-Bold']]}
    
    def __init__(self, path: str,dry:str,fin:str, rep:str):
        super().__init__(path,dry,fin,rep)

class BajajFinServ(Reader):
    
    PARAMS = {
        'fund': [[20],r'Bajaj.*(Fund|Path|ETF|FOF|EOF)$',[14,24],[-16753236]], #FUND NAME DETAILS order-> flag, regex_fund_name, font_size, font_color
        'clip_bbox': [(360,5,612,812)],
        'line_x': 180.0,
        'data': [[6,12],[-1,-15376468],30.0,['Rubik-SemiBold']] #sizes, color, set_size
    }
    
    def __init__(self, path: str,dry:str,fin:str, rep:str):
        super().__init__(path,dry,fin,rep)
        
class ThreeSixtyOne(Reader):
    
    PARAMS = {
        'fund': [[20],r'360 ONE.*(Fund|Path|ETF|FOF|EOF)$',[18,24],[-16777216]], #FUND NAME DETAILS order-> flag, regex_fund_name, font_size, font_color
        'clip_bbox': [(0,5,160,812)],
        'line_x': 160.0,
        'data': [[6,10],[-10791002],30.0,['SpaceGrotesk-SemiBold']] #sizes, color, set_size
    }
    
    def __init__(self, path: str,dry:str,fin:str, rep:str):
        super().__init__(path,dry,fin,rep)
        
class BarodaBNP(Reader):
    PARAMS = {
        'fund': [[0],r'^Baroda BNP',[12,18],[-13619152]], #FUND NAME DETAILS order-> flag, regex_fund_name, font_size, font_color
        'clip_bbox': [(0,65,210, 700)],
        'line_x': 210.0,
        'data': [[6,10],[-12566464],30.0,['Unnamed-T3']] #sizes, color, set_size
    }
    
    def __init__(self, path: str,dry:str,fin:str, rep:str):
        super().__init__(path,dry,fin,rep)
        
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
            
            # print(f"\n----{pgn}----"," ".join(combined_text))

        doc.close()
        return fund_titles
    
class NAVI(Reader):
    PARAMS = {
        'fund': [[20],r'^NAVI.*',[23,33],[-19456]], #FUND NAME DETAILS order-> flag, regex_fund_name, font_size, font_color
        'clip_bbox': [(0,75,320, 700)],
        'line_x': 320.0,
        'data': [[14,20],[-12844976],30.0,['NaviHeadline-Bold']] #sizes, color, set_size
    }
    
    def __init__(self, path: str,dry:str,fin:str, rep:str):
        super().__init__(path,dry,fin,rep,self.PARAMS)
        
    def return_required_header(self,string: str):
            replace_key = string
            if re.match(r'^net.*', string, re.IGNORECASE):
                replace_key = "nav"
            elif re.match(r"^fund_manager", string, re.IGNORECASE):
                replace_key = "fund_manager(s)"
            elif re.match(r"^fund_size.*", string, re.IGNORECASE):
                replace_key = "aum" 
            elif re.match(r"^equity.*", string, re.IGNORECASE):
                replace_key = "equity" 
            elif re.match(r"^investment", string, re.IGNORECASE):
                replace_key = "investment_objective"
            elif re.match(r"^tracking", string, re.IGNORECASE):
                replace_key = "tracking_error"
            elif re.match(r"^performance.*", string, re.IGNORECASE):
                replace_key = "fund_performance" 
            return replace_key
        
    #REGEX
    def __return_dummy_data(self,main_key:str,data:list):
        return{main_key:data}
    def __return_invest_data(self,main_key:str,data:list):
        return {main_key: " ".join(data)}
    def __extract_nav_data(self,main_key:str, data:list):
        nav_data = data
        final_dict = {}
        pattern = r'^(Direct Plan - Growth Option|Regular Plan - Growth Option)[\s]+([\d]+\.\d+)'
        
        final_dict = {}
        for text in nav_data:
            text = text.lower()
            matches = re.findall(pattern, text, re.IGNORECASE)
            for key, value in matches:
                final_dict[key] = Regex.extract_decimals(value)
        return {main_key:final_dict}
    
    def __extract_aum_data(self,main_key:str, data:list):
        final_dict = {}
        pattern = r'^(AUM|Monthly Average AUM)[\s:]+([\d]+\.\d+)'
        
        for text in data:
            if '|' in text:
                aum_data = [i.strip() for i in text.split('|')]
                for aum in aum_data:
                    aum = aum.lower()
                    matches = re.findall(pattern, aum, re.IGNORECASE)
                    for key, value in matches:
                        final_dict[key] = Regex.extract_decimals(value)
        return {main_key:final_dict}
    
    # def __extract_scheme_data(self,main_key:str, data:list):
    #     final_dict = {}
    #     pattern = r'^(Inception Date\s\(.*\)|Index|Minimum Application Amount|Portfolio Turnover Ratio \(Times\))[\s:]+.*'    
    #     for text in data:
    #         text = text.lower()
    #         matches = re.findall(pattern, text, re.IGNORECASE)
    #         for key, value in matches:
    #             final_dict[key] = value
    #     return {main_key:final_dict}
    
    #REGEX MAPPING FUNCTION
    def match_regex_to_content(self,string:str, data:list):
        
        check_header = string
        
        if re.match(r"^investment.*", check_header, re.IGNORECASE):
            return self.__return_invest_data(string,data)
        elif re.match(r"^nav.*", check_header, re.IGNORECASE):
            return self.__extract_nav_data(string, data)
        elif re.match(r"^aum.*", check_header, re.IGNORECASE):
            return self.__extract_aum_data(string, data)
        # elif re.match(r"^scheme.*", check_header, re.IGNORECASE):
        #     return self.__extract_scheme_data(string, data)
        else:
            return self.__return_dummy_data(string,data)
    
    
    
class Zerodha(Reader):
    
    PARAMS = {
        'fund': [[20,0],r'^Zerodha.*',[20,30],[-16777216]], #FUND NAME DETAILS order-> flag, regex_fund_name, font_size, font_color
        'clip_bbox': [(0,5,340, 700)],
        'line_x': 340.0,
        'data': [[14,20],[-16777216],30.0,['Unnamed-T3']] #sizes, color, set_size
    }
    
    def __init__(self, path: str,dry:str,fin:str, rep:str):
        super().__init__(path,dry,fin,rep, self.PARAMS)
        
    def return_required_header(self,string: str):
            replace_key = string
            if re.match(r'^fund_size', string, re.IGNORECASE):
                replace_key = "fund_size"
            elif re.match(r"^fund_manager", string, re.IGNORECASE):
                replace_key = "fund_manager" 
            elif re.match(r"^scheme", string, re.IGNORECASE):
                replace_key = "scheme_details" 
            elif re.match(r"^investment", string, re.IGNORECASE):
                replace_key = "investment_objective"
            elif re.match(r"^quali", string, re.IGNORECASE):
                replace_key = "qualitative_data"
            elif re.match(r"^past", string, re.IGNORECASE):
                replace_key = "past_performance"
            else:
                replace_key = "dummy"      
            return replace_key
        
    def __return_invest_data(self,main_key:str,data:list):
        return {main_key: " ".join(data)}

    def __return_scheme_data(self, main_key:str, data:list):
        scheme_details = data
        final_dict = {}
        for text in scheme_details:
            key, value = '',''
            if match:= re.match(r'^allotment.*', text, re.IGNORECASE):
                key,value = [i.strip() for i in text.split(':')]
            elif match:= re.match(r'^expense.*', text, re.IGNORECASE):
                key,value = [i.strip() for i in text.split(':')]
            elif match:= re.match(r'^benchmark.*',text, re.IGNORECASE):
                key,value = [i.strip() for i in text.split(':')]
            elif match:= re.match(r'^nav.*',text, re.IGNORECASE):
                key,value = [i.strip() for i in text.split(':')]
                value = float(value)
            elif match:= re.match(r'^launched.*',text, re.IGNORECASE):
                key,value = [i.strip() for i in text.split(':')]
            elif match:= re.match(r'^lock-in.*',text, re.IGNORECASE):
                key,value = [i.strip() for i in text.split(':')]
            elif match:= re.match(r'^exit.*',text, re.IGNORECASE):
                key,value = [i.strip() for i in text.split(':')]
            elif match:= re.match(r'^creation.*',text, re.IGNORECASE):
                key,value = [i.strip() for i in text.split(':')]
            elif match:= re.match(r'^expense.*',text, re.IGNORECASE):
                key,value = [i.strip() for i in text.split(':')]
            
            key = "_".join(key.lower().split(" "))   
            if key not in final_dict and key !="":
                final_dict[key] = value
        
        return {main_key:final_dict}

    def __return_aum_data(self,main_key:str, data:list):
        aum_data = data
        final_dict = {}
        for text in aum_data:
            key,value = '',''
            if match:= re.match(r'^Month.*', text, re.IGNORECASE):
                key,value = [i.strip() for i in text.split(':')]
            elif match:= re.match(r'^Monthly.*', text, re.IGNORECASE):
                key,value = [i.strip() for i in text.split(':')]
            elif match:= re.match(r'^Quarterly.*',text, re.IGNORECASE):
                key,value = [i.strip() for i in text.split(':')]
            key +='(crs)'
            key = "_".join(key.lower().split(" "))
            value = float(value.split(" ")[0])
            if key not in final_dict and key !="":
                final_dict[key] = value

        return {main_key:final_dict}
    
    def __return_quant_data(self,main_key:str, data:list):
        quant_data = data
        final_dict = {}
        for text in quant_data:
            key,value = '',''
            if match:= re.match(r'^Portfolio.*', text, re.IGNORECASE):
                key,value = [i.strip() for i in text.split(':')]
                value = float(value)
            elif match:= re.match(r'^Tracking.*', text, re.IGNORECASE):
                key,value = [i.strip() for i in text.split(':')]
            
            key = "_".join(key.lower().split(" "))   
            
            if key not in final_dict and key !="":
                final_dict[key] = value
        return {main_key:final_dict}
    
    def __return_manager_data(self,main_key:str,data:list):
        manager_data = data
        final_list = []
        for c, text in enumerate(manager_data):
            if re.match(r'^Total.*', text,re.IGNORECASE):
                name = manager_data[c-1]
                exp_key,exp_val = manager_data[c].split(':')
                since_key,since_val =  manager_data[c+1].split(':')
                
                final_list.append({
                    'name': name,
                    'designation': '',
                    exp_key.lower():exp_val.strip(),
                    since_key.lower():since_val.strip()
                })
        return {main_key: final_list}

    def __return_dummy_data(self,main_key:str,data:list):
        return{main_key:data}
    
    #REGEX MAPPING FUNCTION
    def match_regex_to_content(self,string:str, data:list, *args):
        
        check_header = string
        
        if re.match(r"^investment.*", check_header, re.IGNORECASE):
            return self.__return_invest_data(string,data)
        elif re.match(r"^scheme.*", check_header, re.IGNORECASE):
            return self.__return_scheme_data(string, data)
        
        elif re.match(r"^(quant|qual).*", check_header, re.IGNORECASE):
            return self.__return_quant_data(string, data)
        
        elif re.match(r".*(managers|manager)$", check_header, re.IGNORECASE):
            return self.__return_manager_data(string, data)
        
        elif re.match(r"^fund.*size$", check_header, re.IGNORECASE):
            return self.__return_aum_data(string, data)
        
        else:
            return self.__return_dummy_data(string,data)   
  
#something