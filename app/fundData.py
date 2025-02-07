import re, os, pprint
from app.pdfParse import Reader
from app.fundRegex import FundRegex
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

    
    #FundRegex FUNCTIONS
    def __return_invest_data(self,main_key:str,data:list):
       return {main_key: " ".join(data)}

    def __return_scheme_data(self,main_key:str,data:list):
        mention_start = [
        "Inception Date",
        "Benchmark",
        r"Min\.?\s*Application",
        "Additional",
        "Entry Load",
        "Exit Load",
        "Total Expense",
        ]

        mention_end = mention_start[1:] + ["End_of_Data"]

        # Generate regex patterns dynamically
        patterns = [r"({start})\s*(.+?)\s*({end}|$)".format(start=start, end=end)
            for start, end in zip(mention_start, mention_end)]
        #other patterns
        ter_pattern = r'([\d,.]+)%\s+([\d,.]+)%'
        
        final_dict = {}
        scheme_data = " ".join(data)
        for pattern in patterns:
            if matches:= re.findall(pattern, scheme_data, re.DOTALL|re.IGNORECASE):
                for match in matches:
                    key, value, dummy = match
                    value = value.strip()
                    final_dict[key] = value
        
        return {main_key:final_dict}

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
        nav_data = data
        pattern = r'(Regular Growth|Direct Growth|Regular IDCW|Direct IDCW)\s*([\d,.]+)'
        final_dict = {}
        for text in nav_data:
            text = re.sub(r'[:,:\*\^]', "", text.strip())
            if matches := re.findall(pattern, text, re.IGNORECASE):
                for key, value in matches:
                    final_dict[key] = value
                
        return {main_key:final_dict}

    def __return_quant_data(self,main_key:str,data:list):
        quant_data = data
        pattern = r'(Portfolio Turnover Ratio|Annualised Portfolio YTM|Macaulay Duration|Residual Maturity|Modified Duration|Residual Maturity|Beta|Treynor .*|Sharpe .*)\s*([\d,.]+)'
        final_dict =  {}
        for text in quant_data:
            text = re.sub(r'[:;\*\^~]','', text.strip())
            if matches:= re.findall(pattern, text, re.IGNORECASE):
                for key, value in matches:
                    final_dict[key] = value

        return{main_key:final_dict}
    
    def __return_aum_data(self,main_key:str,data:list):
        aum_data = data
        pattern = r'(AUM|Average AUM).*?([\d,]+\.\d{2})'
        final_dict = {}
        for text in aum_data:
            text = re.sub(r'[:;\*\^~]','', text.strip())
            if matches:= re.findall(pattern, text, re.IGNORECASE):
                for key, value in matches:
                    final_dict[key] = value

        return{main_key:final_dict}


    def __return_dummy_data(self,key:str,data:list):
        return {key: data}


    #FundRegex MAPPING FUNCTION
    def match_regex_to_content(self,string:str, data:list, *args):
        
        check_header = string
        
        if re.match(r"^Investment.*", check_header, re.IGNORECASE):
            return self.__return_invest_data(string,data)
        elif re.match(r"^Scheme.*", check_header, re.IGNORECASE):
            return self.__return_scheme_data(string, data)
        
        elif re.match(r"^nav", check_header, re.IGNORECASE):
            return self.__return_nav_data(string, data)
        
        elif re.match(r"^metrics.*", check_header, re.IGNORECASE):
            return self.__return_quant_data(string, data)
        
        elif re.match(r"fund_manager.*", check_header, re.IGNORECASE):
            return self.__return_fund_data(string, data)
        
        elif re.match(r"^aum", check_header, re.IGNORECASE):
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
    
    #FundRegex FUNCTIONS
    def __extract_inv_data(self,key:str, data:list):            
        return {key: ' '.join(data)}
    
    def __extract_nav_data(self,main_key:str, data:list):
        nav_data = data
        final_dict = {}
        pattern = r'(Reg\s?-\s?Growth|Direct\s?-\s?Growth|Reg\s?-\s?IDCW|Direct\s?-\s?IDCW)[\s:]+([\d]+\.\d+)'       
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
                    final_dict['portfolio_turnover_ratio'] = FundRegex.extract_decimals(matches.group())
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
                content = [value for value in text.split(" ")[-2:]]
                final_dict['std_deviaton'] = {
                    "fund": content[0],
                    "benchmark": content[1]
                }
            elif re.match(r'^sharpe.*',text, re.IGNORECASE):
                content = [value for value in text.split(" ")[-2:]]
                final_dict['sharpe_ratio'] = {
                    "fund": content[0],
                    "benchmark": content[1]
                }
            elif re.match(r'^r squared.*',text, re.IGNORECASE):
                content = [value for value in text.split(" ")[-2:]]
                final_dict['r_squared_ratio'] = {
                    "fund": content[0],
                    "benchmark": content[1]
                }
            elif re.match(r'^treynor.*',text, re.IGNORECASE):
                content = [value for value in text.split(" ")[-2:]]
                final_dict['treynor_ratio'] = {
                    "fund": content[0],
                    "benchmark": content[1]
                }
            elif re.match(r'^jenson.*',text, re.IGNORECASE):
                content = [value for value in text.split(" ")[-2:]]
                final_dict['jenson_ratio'] = {
                    "fund": content[0],
                    "benchmark": content[1]
                }
            elif re.match(r'^portfolio.*',text, re.IGNORECASE):
                content = [value for value in text.split(" ")[-2:]]
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
        return{key:FundRegex.extract_decimals(data[0]) if len(data) == 1 else data}

    def match_regex_to_content(self, string:str, data:list, *args):
        check_header = string
        
        if re.match(r"^(investment|multiples).*", check_header, re.IGNORECASE):
            return self.__extract_inv_data(string,data)
        elif re.match(r"^nav.*", check_header, re.IGNORECASE):
            return self.__extract_nav_data(string, data)
        elif re.match(r"^turn.*", check_header, re.IGNORECASE):
            return self.__extract_turn_data(string, data)
        elif re.match(r"^metrics.*", check_header, re.IGNORECASE):
            return self.__extract_volat_data(string, data)
        elif re.match(r"^load.*", check_header, re.IGNORECASE):
            return self.__extract_load_data(string, data)
        elif re.match(r"^turn.*", check_header, re.IGNORECASE):
            return self.__extract_turn_data(string, data)
        elif re.match(r".*(manager|managers)$", check_header, re.IGNORECASE):
            return self.__extract_manager_data(string, data)
        elif re.match(r"^expense.*", check_header, re.IGNORECASE):
            return self.__extract_exp_data(string, data)
        elif re.match(r"^(benchmark|scheme_launch).*", check_header, re.IGNORECASE):
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
        elif re.match(r"^volat", string, re.IGNORECASE):
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

    #FundRegex FUNCTIONS
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
                final_dict[key] = FundRegex.extract_decimals(value)
        return {main_key:final_dict}
    
    def __extract_turnover_data(self, main_key:str, data:list):
        fund_data = data
        pattern = r'^(Portfolio Turnover|Total Portfolio).*[\s]+([\d]+\.\d+)'
        final_dict = {}
        for text in fund_data:
            text = text.lower()
            matches = re.findall(pattern, text, re.IGNORECASE)
            for key, value in matches:
                final_dict[key] = FundRegex.extract_decimals(value)
        return {main_key:final_dict}
    
    def __extract_nav_data(self,main_key:str, data:list):
        nav_data = data
        final_dict = {}
        pattern = r'(Growth Plan|IDCW Plan|Direct\s?-\s?Growth Plan|Direct\s?-\s?IDCW Plan)[\s]+([\d]+\.\d+)'
        
        final_dict = {}
        for text in nav_data:
            text = text.lower()
            matches = re.findall(pattern, text, re.IGNORECASE)
            for key, value in matches:
                final_dict[key] = FundRegex.extract_decimals(value)
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
                final_dict[key.strip()] = value
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
        elif re.match(r"^metrics", check_header, re.IGNORECASE):
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
    
    #FundRegex
    def __extract_dum_data(self,key,data:list):
        return {key:data}
    
    def __extract_inv_data(self,key:str, data:list):            
        return {key: ' '.join(data)}
    
    def __extract_total_expense_data(self,main_key:str, data:list):
        expense_data = data
        final_dict = {}
        pattern = r'(Regular|Direct)[\s]+([\d]+(?:\.\d+)?|NA|Nil)'
        for text in expense_data:
            text = text.lower()
            matches = re.findall(pattern, text, re.IGNORECASE)
            for key, value in matches:
                final_dict[key] = value
        return {main_key:final_dict}
    
    def __extract_nav_data(self,main_key:str, data:list):
        nav_data = data
        final_dict = {}
        pattern = r'(Regular Plan Growth|Regular Plan IDCW|Direct Plan Growth|Direct Plan IDCW)[\s]+([\d]+(?:\.\d+)?|NA|Nil)'
        for text in nav_data:
            text = text.lower().replace("@","")
            matches = re.findall(pattern, text, re.IGNORECASE)
            for key, value in matches:
                final_dict[key] = value
        return {main_key:final_dict}
    
    def __extract_port_data(self,main_key:str, data:list):
        nav_data = data
        final_dict = {}
        pattern = r'(Equity|Aggregate|Tracking Error.*)[\s]+([\d]+(?:\.\d+)?|NA|Nil)'
        for text in nav_data:
            text = text.lower().replace('^','').replace('(Annualized)',"")
            matches = re.findall(pattern, text, re.IGNORECASE)
            for key, value in matches:
                final_dict[key] = value
        return {main_key:final_dict}
    
    def __extract_volat_data(self,main_key:str, data:list):
        nav_data = data
        final_dict = {}
        pattern = r'(Beta|R Squared|Standard Deviation \(Annualized\)|Sharpe\*|Modified Duration|Average Maturity|Macaulay Duration|Yield to Maturity)[\s]+([\d]+(?:\.\d+)?|NA|Nil)'

        for text in nav_data:
            text = text.lower().replace('^','').replace('(Annualized)',"")
            matches = re.findall(pattern, text, re.IGNORECASE)
            for key, value in matches:
                final_dict[key] = value
        return {main_key:final_dict}
    
    def __extract_singular_data(self,key,data:list):
        return{key:data[0] if len(data) == 1 else data}
    
    def __extract_singular_num_data(self,key,data:list):
        return{key:FundRegex.extract_decimals(data[0]) if len(data) == 1 else data}

    def __extract_manager_data(self,main_key:str, data:list):
        return{main_key: " ".join(data)}
    
    def match_regex_to_content(self, string:str, data:list, *args):
        check_header = string
        
        if re.match(r"^(about|investment|sip|option).*", check_header, re.IGNORECASE):
            return self.__extract_inv_data(string,data)
        elif re.match(r"^nav.*", check_header, re.IGNORECASE):
            return self.__extract_nav_data(string, data)
        elif re.match(r"^(category|scheme_launch|benchmark).*", check_header, re.IGNORECASE):
            return self.__extract_singular_data(string, data)
        elif re.match(r"^fund.*", check_header, re.IGNORECASE):
            return self.__extract_manager_data(string, data)
        elif re.match(r"^portfolio.*", check_header, re.IGNORECASE):
            return self.__extract_port_data(string, data)
        elif re.match(r"^metrics.*", check_header, re.IGNORECASE):
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
        
    #FundRegex
    
    def __extract_dum_data(self,key,data:list):
        return {key:data}
    
    def __extract_inv_data(self,key:str, data:list):            
        return {key: ' '.join(data)}

    def __extract_total_expense_data(self,main_key:str, data:list):
        expense_data = data
        final_dict = {}
        pattern = r'(Regular Plan|Direct Plan)[\s]+([\d]+(?:\.\d+)?|NA|Nil)'
        
        final_dict = {}
        for text in expense_data:
            text = text.lower()
            matches = re.findall(pattern, text, re.IGNORECASE)
            for key, value in matches:
                final_dict[key] = value
        return {main_key:final_dict}
    
    def __extract_nav_data(self,main_key:str, data:list):
        nav_data = data
        final_dict = {}
        pattern = r'(Regular Plan\s?-\s?Growth Option|Regular Plan\s?-\s?IDCW Option|Direct Plan\s?-\s?Growth Option|Direct Plan\s?-\s?IDCW Option)[\s]+([\d]+(?:\.\d+)?|NA|Nil)'
        
        final_dict = {}
        for text in nav_data:
            text = text.lower()
            matches = re.findall(pattern, text, re.IGNORECASE)
            for key, value in matches:
                final_dict[key.strip()] = value
        return {main_key:final_dict}

    def __extract_aum_data(self,main_key:str, data:list):
        aum_data = data
        final_dict = {}
        pattern = r'(Monthly Avg AUM|Month End AUM)\s*([\d,.]+)'
        for text in aum_data:
            text = text.lower()
            matches = re.findall(pattern, text, re.IGNORECASE)
            for key, value in matches:
                final_dict[key.strip()] = value
        return {main_key:final_dict}
    
    def __extract_ptr_data(self,main_key:str, data:list):
        ter_data = data
        final_dict = {}
        pattern = r'(Equity Turnover|Total Turnover)\s*([\d,.]+)'
        for text in ter_data:
            text = text.lower()
            matches = re.findall(pattern, text, re.IGNORECASE)
            for key, value in matches:
                final_dict[key.strip()] = value
        return {main_key:final_dict}
    
    def __extract_scheme_data(self, main_key:str, data:list):
        # Define start and end markers
        mention_start = [
            "Scheme Category",
            "Benchmark",
            "Plans and Options",
            "Inception Date",
            "Minimum Investment Amount",
            "Additional Investment Amount",
            "Fund Manager",
            "Entry Load",
            "Exit Load",
            "Face Value per Unit"
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
    
    def match_regex_to_content(self, string:str, data:list):
        check_header = string
        if re.match(r"^(investment).*", check_header, re.IGNORECASE):
            return self.__extract_inv_data(string,data)
        elif re.match(r"^total.*", check_header, re.IGNORECASE):
            return self.__extract_total_expense_data(string, data)
        elif re.match(r"^aum.*", check_header, re.IGNORECASE):
            return self.__extract_aum_data(string, data)
        elif re.match(r"^nav.*", check_header, re.IGNORECASE):
            return self.__extract_nav_data(string, data)
        elif re.match(r"^portfolio$", check_header, re.IGNORECASE):
            return self.__extract_scheme_data(string, data)
        # elif re.match(r"^portfolio_turover_ratio.*", check_header, re.IGNORECASE): #error here portfolio is read
        #     return self.__extract_ptr_data(string, data)
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
                        

    #FundRegex 
    def __extract_dum_data(self,main_key:str,data:list):
        return {main_key:data}
    
    def __extract_inv_data(self,main_key:str, data:list):
        return {main_key:" ".join(data)}
    
    def __extract_nav_data(self,main_key:str, data:list):
        nav_data = data
        final_dict = {}
        pattern = r'(.+?)\s(\d+\.\d+)'
        for text in nav_data:
            text = text.strip()
            matches = re.findall(pattern, text, re.IGNORECASE)
            for key, value in matches:
                final_dict[key] = value
        return {main_key:final_dict}
    
    def __extract_aum_data(self,main_key:str, data:list):
        aum_data = data
        final_dict = {}
        pattern = r'Rs\.\s([\d,]+\.\d+).*Rs\.\s([\d,]+\.\d+).*'
        for text in aum_data:
            text = text.strip()
            if matches:= re.findall(pattern,text, re.IGNORECASE):
                for value1, value2 in matches:
                    final_dict['Month End Aum'], final_dict['Monthly Average Aum'] = value1, value2

        return {main_key:final_dict}
    
    def __extract_expense_data(self, main_key:str, data:list):
        expense_data = data
        final_dict = {}
        pattern = r'(Regular Plan|Direct Plan)\s([\d.]+)%'
        for text in expense_data:
            text = text.strip()
            if matches:= re.findall(pattern, text, re.IGNORECASE):
                for key, value in matches:
                    final_dict[key] = value
        
        return {main_key:final_dict}
    
    def __extract_manager_data(self, main_key:str, data:list):
        manager_data = data
        final_list = []
        pattern = r"(Mr\.|Ms\.)\s([A-Za-z\s]+)\s(\d{1,2}\syears)\s(.*)"
        
        for text in manager_data:
            text = text.strip()
            if matches:= re.findall(pattern, text, re.IGNORECASE):
                for match in matches:
                    dummy,name,exp,date = match
                    final_list.append({
                        "name":name,
                        "designation":"",
                        "managing_since": date,
                        "experience": exp
                    })
                
        return {main_key:final_list}
    def match_regex_to_content(self, string:str, data:list, *args):
        check_header = string  
        if re.match(r"^(minimum|additional|benchmark|exit).*", check_header, re.IGNORECASE):
            return self.__extract_inv_data(string,data)
        elif re.match(r"^nav.*", check_header, re.IGNORECASE):
            return self.__extract_nav_data(string, data)
        elif re.match(r"^aum.*", check_header, re.IGNORECASE):
            return self.__extract_aum_data(string, data)
        elif re.match(r"^total.*", check_header, re.IGNORECASE):
            return self.__extract_expense_data(string, data)
        elif re.match(r"^fund.*", check_header, re.IGNORECASE):
            return self.__extract_manager_data(string, data)
        else:
            return self.__extract_dum_data(string,data) 

class HSBC(Reader):
    
    PARAMS = {
        'fund': [[20,16], r'^(HSBC|Bharat).*Fund$',[12,20],[-1237724]],
        'clip_bbox': [(0,100,180,812)],
        'line_x': 180.0,
        'data': [[6,8], [-16777216], 30.0, ['Arial-BoldMT']]
    }
    
    def __init__(self, path: str,dry:str,fin:str, rep:str):
        super().__init__(path,dry,fin,rep, self.PARAMS)
        
    #Fund REGEX
    def __extract_dum_data(self,key,data:list):
        return {key:data}
    
    def __extract_inv_data(self,key:str, data:list):            
        return {key: ' '.join(data)}
    
    #MAPPING
    def match_regex_to_content(self, string:str, data:list):
        check_header = string
        if re.match(r"^(investment).*", check_header, re.IGNORECASE):
            return self.__extract_inv_data(string,data)
        # elif re.match(r"^total.*", check_header, re.IGNORECASE):
        #     return self.__extract_total_expense_data(string, data)
        # elif re.match(r"^nav.*", check_header, re.IGNORECASE):
        #     return self.__extract_nav_data(string, data)
        # elif re.match(r"^portfolio.*", check_header, re.IGNORECASE): #error here portfolio is read
        #     return self.__extract_scheme_data(string, data)
        return self.__extract_dum_data(string,data)     
        
class Invesco(Reader):
    
    PARAMS = {
        'fund': [[20,16], r'^(Invesco|Bharat).*Fund$',[12,20],[-16777216]],
        'clip_bbox': [(0,135,185,812)],
        'line_x': 180.0,
        'data': [[7,9], [-16777216], 30.0, ['Graphik-Semibold']]
    }
    
    def __init__(self, path: str,dry:str,fin:str, rep:str):
        super().__init__(path,dry,fin,rep, self.PARAMS)
    
     #REGEX
    
    def __extract_dum_data(self,main_key,data:list):
        return {main_key:data}
    
    def __extract_inv_data(self,main_key:str, data:list):            
        return {main_key: ' '.join(data)}
    
    def __extract_aum_data(self,main_key:str, data:list):
        aum_data = data
        pattern = r'[Rr]\s?([\d,]+\.\d+)\s?crores'
        for text in aum_data:
            text = text.strip()
            if matches:= re.findall(pattern, text, re.IGNORECASE):
                return {main_key:" ".join(matches)}
    
    def __extract_metric_data(self,main_key:str,data:list):
        metric_data = data
        pattern = r'(Standard Deviation|Beta|Sharpe Ratio|Fund P/B|YTM\d*|Average Maturity|Macaulay Duration|Modified Duration)\s([\d.]+\d+).*'
        final_dict = {}
        for text in metric_data:
            text = text.strip()
            if matches:= re.findall(pattern, text, re.IGNORECASE):
                for key, value in matches:
                    final_dict[key] = value
                    
        return {main_key:final_dict}
    
    def __extract_nav_data(self, main_key:str, data:list):
        nav_data = data
        final_dict = {}
        pattern = r"(Growth|IDCW|Daily IDCW|Weekly IDCW|Monthly IDCW|Quarterly IDCW|Annual IDCW|Discretionary IDCW|Bonus)\s([\d,]+\.\d+)"

        for text in nav_data:
            text = text.strip()
            if matches:= re.findall(pattern,text, re.IGNORECASE):
                plan_type = "Regular Plan"  # Default to Regular Plan
                for metric, value in matches:
                    if metric == "Growth":  # Growth indicates a new plan section
                        plan_type = "Direct Plan" if plan_type == "Regular Plan" else "Regular Plan" 
                    final_dict[f'{plan_type} - {metric}'] = value

        return {main_key:final_dict}
    
    def __extract_expense_data(self,main_key:str, data:list):
        expense_data = data
        final_dict = {}
        pattern = r'(Regular|Direct)\s([\d.]+)%'
        for text in expense_data:
            text = text.strip()
            if matches:= re.findall(pattern,text, re.IGNORECASE):
                for key, value in matches:
                    final_dict[key] = value
        
        return {main_key:final_dict}
    
    def __extract_ptr_data(self,main_key:str, data:list):
        ter_data = data
        ter = ""
        pattern = r'.*\s([\d.]+)'
        for text in ter_data:
            if matches:= re.findall(pattern,text, re.IGNORECASE):
                ter+=matches[0]
        
        return{main_key:ter}
    
    def __extract_manager_data(self, main_key:str, data:list):
        manager_data = " ".join(data)
        final_list = []
        pattern = r"([A-Za-z\s]+)Total Experience\s(\d+\s?Years).*?(?:Experience in managing this fund:\s?|Since\s)(\w+\s\d{1,2},\s\d{4})"
        matches = re.findall(pattern, manager_data, re.IGNORECASE)
        for name,exp,since in matches:
            final_list.append({
                'name':name,
                "designation":"",
                "experience": exp,
                "managing_since": since
            })
        return {main_key:final_list}
    
    #MAPPING
    def match_regex_to_content(self, string:str, data:list):
        check_header = string
        if re.match(r"^(load|investment|scheme_launch|benchmark|minimum|additional).*", check_header, re.IGNORECASE):
            return self.__extract_inv_data(string,data)
        elif re.match(r"^nav.*", check_header, re.IGNORECASE):
            return self.__extract_nav_data(string, data)
        elif re.match(r"^(aum|aaum).*", check_header, re.IGNORECASE):
            return self.__extract_aum_data(string, data)
        elif re.match(r"^metric.*", check_header, re.IGNORECASE):
            return self.__extract_metric_data(string, data)
        elif re.match(r"^total.*", check_header, re.IGNORECASE):
            return self.__extract_expense_data(string, data)
        elif re.match(r"^portfolio.*", check_header, re.IGNORECASE):
            return self.__extract_ptr_data(string, data)
        elif re.match(r"^fund.*", check_header, re.IGNORECASE):
            return self.__extract_manager_data(string, data)
        return self.__extract_dum_data(string,data) 

class MIRAE(Reader):
    
    PARAMS = {
        'fund': [[20,16],r'^MIRAE.*',[26,36],[-687584]],
        'clip_bbox': [(0,190,270,812)],
        'line_x': 270.0,
        'data': [[8,12], [-14991759], 30.0, ['SpoqaHanSans-Bold']]
    }
    
    def __init__(self, path: str,dry:str,fin:str, rep:str):
        super().__init__(path,dry,fin,rep, self.PARAMS)
    
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
     #REGEX
    
    def __extract_dum_data(self,main_key,data:list):
        return {main_key:data}
    
    def __extract_inv_data(self,main_key:str, data:list):            
        return {main_key: ' '.join(data)}
    
    def __extract_scheme_data(self, main_key:str, data:list):
        # Define start and end markers
        mention_start = [
            "Fund Managers",
            "Allotment Date",
            "Benchmark",
            'Net AUM',
            "Tracking Error Value",
            "Exit Load",
            "Plan Available",
        ]
        
        mention_end = mention_start[1:] + [" End_of_Data"]

        # Generate regex patterns dynamically
        patterns = [r"({start}\s*)(.+?)({end}|$)".format(start=start, end=end)
            for start, end in zip(mention_start, mention_end)]
        final_dict = {}
        scheme_data = " ".join(data) + " End_of_Data"
        scheme_data = re.sub(r"[\^#*\$:;~]", "", scheme_data)
        
        for pattern in patterns:
            if matches:= re.findall(pattern, scheme_data, re.DOTALL|re.IGNORECASE): #not used ignorecase
                for match in matches:
                    key, value, dummy = match
                    final_dict[key.strip()] = value
                
        return {main_key:final_dict}
    
    def __extract_nav_data(self, main_key:str, data:list):
        nav_data = " ".join(data)
        matches = re.search(r'[\d,.]+', nav_data)
        return{main_key:matches.group()}
    
    def __extract_metric_data(self,main_key:str, data:list):
        metric_data = data
        final_dict = {}
        pattern = r'^(Average Maturity|Modified Duration|Macaulay Duration|Annualized Portfolio YTM|Beta|Sharpe Ratio|YTM|Jensons .*|Treynor .*)\s*([\d,.]+)'
        for text in metric_data:
            text = re.sub(r'[\*~:\^;]',"",text.strip())
            matches = re.findall(pattern, text, re.IGNORECASE)
            for key, value in matches:
                final_dict[key.strip()] = value
        return {main_key:final_dict}
    
    def __extract_expense_data(self,main_key:str, data:list):
        expense_data = data
        final_dict = {}
        pattern = r'^(Regular Plan|Direct Plan)\s*([\d,.]+)'
        for text in expense_data:
            text = re.sub(r'[\*~:\^;]',"",text.strip())
            matches = re.findall(pattern, text, re.IGNORECASE)
            for key, value in matches:
                final_dict[key.strip()] = value
        return {main_key:final_dict}
    
    #MAPPING
    def match_regex_to_content(self, string:str, data:list):
        check_header = string
        if re.match(r"^(scheme).*", check_header, re.IGNORECASE):
            return self.__extract_scheme_data(string,data)
        elif re.match(r"^nav.*", check_header, re.IGNORECASE): #error here portfolio is read
            return self.__extract_nav_data(string, data)
        elif re.match(r"^metric.*", check_header, re.IGNORECASE): 
            return self.__extract_metric_data(string, data)
        elif re.match(r"^expense.*", check_header, re.IGNORECASE): 
            return self.__extract_expense_data(string, data)
        return self.__extract_dum_data(string,data)

class ITI(Reader):
    
    PARAMS = {
        'fund': [[20,16], r'^(ITI|Bharat).*Fund$',[14,24],[-1]],
        'clip_bbox': [(0,105,180,812)],
        'line_x': 180.0,
        'data': [[5,8], [-1688818,-1165277], 30.0, ['Calibri-Bold']]
    }
    
    def __init__(self, path: str,dry:str,fin:str, rep:str):
        super().__init__(path,dry,fin,rep, self.PARAMS)
        
     #REGEX
    def __extract_dum_data(self,main_key,data:list):
        return {main_key:data}
    
    def __extract_inv_data(self,main_key:str, data:list):            
        return {main_key: ' '.join(data)}
    
    def __extract_aum_data(self,main_key:str, data:list):
        pattern = r'(AUM|AAUM)\s*\(.*\):?\s*(-?[\d,.]+)'
        final_dict = {}
        nav_data = data
        for text in nav_data:
            text = re.sub(r"[\^#*\$]", "", text.strip())
            if matches := re.findall(pattern, text, re.IGNORECASE):
                for key, value in matches:
                    final_dict[key] = value
        return {main_key: final_dict}
    
    def __extract_nav_data(self,main_key:str, data:list):
        pattern = r'(Growth|IDCW)\s*(-?[\d,.]+)\s*(-?[\d,.]+)'
        final_dict = {}
        nav_data = data
        for text in nav_data:
            text = re.sub(r"[\^#*\$:]", "", text.strip())
            if matches := re.findall(pattern, text, re.IGNORECASE):
                for key, regular, direct in matches:
                    final_dict[f'Regular {key}'] = regular
                    final_dict[f'Direct {key}'] = direct
        return {main_key: final_dict}
    
    def __extract_metric_data(self,main_key:str, data:list):
        pattern = r'(Average P/E|Average P/B|Standard Deviation|Beta|Sharpe Ratio|Average Maturity|Modified Duration|Yield to Maturity|Macaulay Duration|Portfolio Turnover Ratio)\s*(-?[\d\.,]+)'
        final_dict = {}
        metric_data = data
        for text in metric_data:
            text = re.sub(r"[:\^#*\$,]", "", text.strip())
            if matches := re.findall(pattern, text, re.IGNORECASE):
                for key, value in matches:
                    final_dict[key] = value
        
        return {main_key: final_dict}
    
    def __extract_scheme_data(self, main_key:str, data:list):
        # Define start and end markers
        mention_start = [
            "Inception Date",
            "Benchmark",
            "Minimum Application",
            'Load Structure',
            "Entry Load",
            "Exit Load",
            "Total Expense Ratio",
        ]
        
        mention_end = mention_start[1:] + [" End_of_Data"]

        # Generate regex patterns dynamically
        patterns = [r"({start}\s*)(.+?)({end}|$)".format(start=start, end=end)
            for start, end in zip(mention_start, mention_end)]
        final_dict = {}
        scheme_data = " ".join(data) + " End_of_Data"
        scheme_data = re.sub(r"[\^#*\$:;]", "", scheme_data)
        
        for pattern in patterns:
            if matches:= re.findall(pattern, scheme_data, re.DOTALL|re.IGNORECASE): #not used ignorecase
                for match in matches:
                    key, value, dummy = match
                    final_dict[key.strip()] = value
                
        return {main_key:final_dict}
    
     #MAPPING
    
    def match_regex_to_content(self, string:str, data:list):
        check_header = string
        if re.match(r"^investment.*", check_header, re.IGNORECASE):
            return self.__extract_inv_data(string,data)
        elif re.match(r"^aum.*", check_header, re.IGNORECASE):
            return self.__extract_aum_data(string, data)
        elif re.match(r"^nav.*", check_header, re.IGNORECASE):
            return self.__extract_nav_data(string, data)
        elif re.match(r"^metrics.*", check_header, re.IGNORECASE):
            return self.__extract_metric_data(string, data)
        elif re.match(r"^scheme.*", check_header, re.IGNORECASE):
            return self.__extract_scheme_data(string, data)
        return self.__extract_dum_data(string,data) 
       
class JMMF(Reader):
    
    PARAMS = {
        'fund': [[20,16], r'^(JM|Bharat).*Fund$',[14,24],[-10987173]],
        'clip_bbox': [(390,105,596,812)],
        'line_x': 390.0,
        'data': [[6,9], [-1], 30.0, ['MyriadPro-BoldCond']]
    }
    
    def __init__(self, path: str,dry:str,fin:str, rep:str):
        super().__init__(path,dry,fin,rep, self.PARAMS)
        
    #REGEX
    def __extract_dum_data(self,main_key,data:list):
        return {main_key:data}
    
    def __extract_inv_data(self,main_key:str, data:list):            
        return {main_key: ' '.join(data)}
    
    def __extract_nav_data(self, main_key:str, data:list):
        nav_data = data
        final_dict = {}
        pattern = r'\((Regular|Direct)\)\s*-\s*(Growth Option|IDCW \(Payout\))\s*:\s*([\d.]+)'
        for text in nav_data:
            text = text.strip()
            if matches := re.findall(pattern, text, re.IGNORECASE):
                for regular, option, value in matches:
                    final_dict[f'{regular} {option}'] = value 
                    
        return {main_key:final_dict}
    
    def __extract_aum_data(self, main_key:str, data:list):
        aum_data = data
        final_dict = {}
        pattern = r'^(Month End AUM|Monthly AAUM)\s*:.*([\d,]+\.\d+).*'
        for text in aum_data:
            text = text.strip()
            if matches := re.findall(pattern, text, re.IGNORECASE):
                for key, value in matches:
                    final_dict[key] = value 
                    
        return {main_key:final_dict}
    
    def __extract_expense_data(self, main_key:str, data:list):
        expense_data = data
        final_dict = {}
        pattern = r'^(Regular Plan|Direct Plan)\s*([\d.,]+)%'
        for text in expense_data:
            text = text.strip()
            if matches := re.findall(pattern, text, re.IGNORECASE):
                for key, value in matches:
                    final_dict[key] = value 
                    
        return {main_key:final_dict}
    
    def __extract_metric_data(self, main_key:str, data:list):
        metric_data = data
        final_dict = {}
        pattern = r'(Beta|Sharpe Ratio|Std\. Dev\.|Standard Deviation|Portfolio Beta|Portfolio Turnover Ratio|Tracking Error|Annualised .* YTM|Modified Duration|Average Maturity|Macaulay Duration)\s*[:~-]?\s*([\d.,]+)\s*(?:years|days|%)?'
        for text in metric_data:
            text = text.strip()
            if matches := re.findall(pattern, text, re.IGNORECASE):
                for key, value in matches:
                    final_dict[key] = value 
                    
        return {main_key:final_dict}
    
      
    #MAPPING
    def match_regex_to_content(self, string:str, data:list):
        check_header = string
        if re.match(r"^(investment|exit_load).*", check_header, re.IGNORECASE):
            return self.__extract_inv_data(string,data)
        elif re.match(r"^aum.*", check_header, re.IGNORECASE):
            return self.__extract_aum_data(string, data)
        elif re.match(r"^expen.*", check_header, re.IGNORECASE):
            return self.__extract_expense_data(string, data)
        elif re.match(r"^metric.*", check_header, re.IGNORECASE):
            return self.__extract_metric_data(string, data)
        elif re.match(r"^nav.*", check_header, re.IGNORECASE):
            return self.__extract_nav_data(string, data)
        return self.__extract_dum_data(string,data) 

class DSP(Reader):
    
    PARAMS = {
        'fund': [[20,16], r'^(DSP|Bharat).*(Fund|ETF|FTF|FOF)$|^(DSP|Bharat)',[14,24],[-1]],
        'clip_bbox': [(0,5,120,812),[480,5,596,812]],
        'line_x': 120.0,
        'data': [[7,10], [-16777216], 30.0, ['TrebuchetMS-Bold']]
    }
    
    
    def __init__(self, path: str,dry:str,fin:str, rep:str):
        super().__init__(path,dry,fin,rep, self.PARAMS)
        
    #REGEX
    def __extract_dum_data(self,main_key,data:list):
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
        return self.__extract_dum_data(string,data) 
        
class BankOfIndia(Reader):
    
    PARAMS = {
        'fund': [[20,16], r'^Bank of India',[14,24],[-65784]],
        'clip_bbox': [(0,480,290,812)],
        'line_x': 290.0,
        'data': [[6,9], [-13948375], 30.0, ['Calibri-Bold']]}
    
    def __init__(self, path: str,dry:str,fin:str, rep:str):
        super().__init__(path,dry,fin,rep, self.PARAMS)
        
    #REGEX
    def __extract_dum_data(self,main_key,data:list):
        return {main_key:data}
    
    def __extract_inv_data(self,main_key:str, data:list):            
        return {main_key: ' '.join(data).strip()}

    #MAPPING
    def match_regex_to_content(self, string:str, data:list):
        check_header = string
        if re.match(r"^(investment|benchmark|date|average|latest|minimum_application|additional_).*", check_header, re.IGNORECASE):
            return self.__extract_inv_data(string,data)
        # elif re.match(r"^total.*", check_header, re.IGNORECASE):
        #     return self.__extract_ter_data(string, data)
        return self.__extract_dum_data(string,data) 
    
        class Kotak(Reader):
    
    PARAMS = {
        'fund': [[20,16], r'^(Kotak|Bharat).*(Fund|ETF|FTF|FOF)$|^Kotak',[12,20],[-15319437]],
        'clip_bbox': [(0,80,150,812),],
        'line_x': 150.0,
        'data': [[6,8], [-15445130,-14590595], 30.0, ['Frutiger-Bold']]}
    
    def __init__(self, path: str,dry:str,fin:str, rep:str):
        super().__init__(path,dry,fin,rep, self.PARAMS)
        
    #REGEX
    def __extract_dum_data(self,main_key,data:list):
        return {main_key:data}
    
    def __extract_inv_data(self,main_key:str, data:list):            
        return {main_key: ' '.join(data).strip()}
    
    def __extract_metric_data(self,main_key:str, data:list):
        metric_data = data
        final_dict = {}
        pattern = r'(?i)(?:(Portfolio Turnover|Beta|Sharpe|Standard Deviation|P\/E|P\/BV|Tracking Error|Average Maturity|Modified Duration|Macaulay Duration|Annualised YTM)\s*:?[\s]*)?([\d,]+\.\d+|\d+\.?\d*\s*(?:yrs|years|days|%))'           
        for text in metric_data:
            text = re.sub(r"[\^#*\$]", "", text.strip())
            if matches:= re.findall(pattern, text, re.IGNORECASE):
                for key, value in matches:
                    final_dict[key] = value
        return {main_key: final_dict}
    
    def __extract_ter_data(self, main_key:str, data:list):
        ter_data = data
        final_dict = {}
        pattern = r'(Regular Plan|Direct Plan):\s*([\d.]+)%'
        for text in ter_data:
            text = text.strip()
            if matches:= re.findall(pattern, text, re.IGNORECASE):
                for key, value in matches:
                    final_dict[key] = value
        return{main_key:final_dict}
    
    def __extract_nav_data(self,main_key:str, data:list):
        pattern = r'(Growth|IDCW)\s*([\d.]+)\s*([\d.]+)'
        final_dict = {}
        nav_data = data
        for text in nav_data:
            text = text.strip()
            if matches := re.findall(pattern, text, re.IGNORECASE):
                for index, reg, direct in matches:
                    final_dict[f'Regular {index}'] = reg
                    final_dict[f'Direct {index}'] = direct
        
        return {main_key: final_dict}
    
    #MAPPING
    def match_regex_to_content(self, string:str, data:list):
        check_header = string
        if re.match(r"^(sip|aaum|aum|allotment|folio_count|entry|exit|initial|systemic|ideal).*", check_header, re.IGNORECASE):
            return self.__extract_inv_data(string,data)
        elif re.match(r"^total.*", check_header, re.IGNORECASE):
            return self.__extract_ter_data(string, data)
        elif re.match(r"^fund_mana.*", check_header, re.IGNORECASE):
            return self.__extract_inv_data(string, data)
        elif re.match(r"^nav.*", check_header, re.IGNORECASE):
            return self.__extract_nav_data(string, data)
        elif re.match(r"^metrics.*", check_header, re.IGNORECASE):
            return self.__extract_metric_data(string, data)
        return self.__extract_dum_data(string,data) 

class LIC(Reader):
    
    PARAMS = {
        'fund': [[20,16], r'^(LIC|Bharat).*(Fund|ETF|FTF|FOF)$',[12,20],[-15319437]],
        'clip_bbox': [(0,5,150,812),],
        'line_x': 150.0,
        'data': [[5,8], [-15445130,-14590595], 30.0, ['Frutiger-Bold']]}
    
    def __init__(self, path: str,dry:str,fin:str, rep:str):
        super().__init__(path,dry,fin,rep, self.PARAMS)          

class MahindraManu(Reader):
    PARAMS = {
        'fund': [[20,16], r'',[12,20],[-15319437]],
        'clip_bbox': [(0,65,200,812)],
        'line_x': 200.0,
        'data': [[7,10], [-7392877,-16749906,-7953091,-7767504,-12402502,-945627,], 30.0, ['QuantumRise-Bold','QuantumRise','QuantumRise-Semibold']]}
    
    def __init__(self, path: str,dry:str,fin:str, rep:str):
        super().__init__(path,dry,fin,rep, self.PARAMS)
    
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

    #REGEX
    def __extract_dum_data(self,main_key,data:list):
        return {main_key:data}
    
    def __extract_inv_data(self,main_key:str, data:list):            
        return {main_key: ' '.join(data).strip()}
    
    def __extract_nav_data(self,main_key:str, data:list):
        pattern = r'(Growth|IDCW)\s*([\d.]+)\s*([\d.]+)'
        final_dict = {}
        nav_data = data
        for text in nav_data:
            text = re.sub(r"[\^#*\$]", "", text.strip())
            if matches := re.findall(pattern, text, re.IGNORECASE):
                for index, reg, direct in matches:
                    final_dict[f'Regular {index}'] = reg
                    final_dict[f'Direct {index}'] = direct
        
        return {main_key: final_dict}
    
    def __extract_metric_data(self,main_key:str, data:list):
        pattern = r'(Portfolio Turnover Ratio|Standard Deviation|Beta|Sharpe|Jensons).*\s(-?\d+\.\d+)'
        final_dict = {}
        metric_data = data
        for text in metric_data:
            text = re.sub(r"[\^#*\$]", "", text.strip())
            if matches := re.findall(pattern, text, re.IGNORECASE):
                for key, value in matches:
                    final_dict[key] = value
        
        return {main_key: final_dict}
    
    def __extract_manager_data(self,main_key:str, data:list):
        pattern = r'([\w\s]+)\s+Total Experience:?\s*(\d+\s+years(?:\s+and\s+\d+\s+months)?)\s+Experience in managing this fund:\s*([\w\s]+?)\s*\(Managing since\s*([A-Za-z0-9 ,]+)\)'
        final_list = []
        manager_data = " ".join(data)
        manager_data = re.sub(r"[\^#*\$]", "", manager_data.strip())
        matches = re.findall(pattern, manager_data, re.IGNORECASE)
        for match in matches:
            name,exp,temp,since = match
            final_list.append({
                "name":name.strip(),
                "designation": "",
                "experience": exp,
                "managing_since": since
            })
        return {main_key:final_list}
    
    def __extract_scheme_data(self, main_key:str, data:list):
        # Define start and end markers
        mention_start = [
            "Date of allotment",
            "Benchmark",
            "Option",
            "Minimum Application Amount",
            "Minimum Additional Purchase Amount",
            "Minimum Repurchase Amount",
            "Minimum Redemption / Switch-outs",
            "Monthly AAUM",
            "Quarterly AAUM",
            "Monthly AUM",
            "Total Expense Ratio",
            "Load Structure",
            "Entry Load",
            "Exit Load"
        ]

        #sub regex
        decimal_pattern = r'(\d{1,3}(?:,\d{3})*\.\d+)'
        ter_pattern = r'(\d{1,3}(?:,\d{3})*\.\d+).*(\d{1,3}(?:,\d{3})*\.\d+)'
        
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
                    #since decimal to be extracted from here
                    if re.match(r'^(Monthly AAUM|Quarterly AAUM|Monthly AUM)', key, re.IGNORECASE):
                        decimals = re.findall(decimal_pattern, value, re.IGNORECASE)
                        value = decimals[0]
                    elif re.match(r'^Total.*', key, re.IGNORECASE):
                        decimals = re.findall(ter_pattern, value, re.IGNORECASE)
                        value = {
                            "Regular Plan": decimals[0][0],
                            "Direct Plan": decimals[0][1]
                        }
                    final_dict[key.strip()] = value

        return {main_key:final_dict}
    
    #MAPPING
    def match_regex_to_content(self, string:str, data:list):
        check_header = string
        if re.match(r"^(investment).*", check_header, re.IGNORECASE):
            return self.__extract_inv_data(string,data)
        elif re.match(r"^fund_mana.*", check_header, re.IGNORECASE):
            return self.__extract_manager_data(string, data)
        elif re.match(r"^metric.*", check_header, re.IGNORECASE):
            return self.__extract_metric_data(string, data)
        elif re.match(r"^scheme.*", check_header, re.IGNORECASE):
            return self.__extract_scheme_data(string, data)
        elif re.match(r"^nav.*", check_header, re.IGNORECASE):
            return self.__extract_nav_data(string, data)
        return self.__extract_dum_data(string,data) 

class MotilalOswal(Reader):
    PARAMS = {
        'fund': [[20,16], r'^(Motilal|Oswal).*(Fund|ETF|EOF|FOF|FTF|Path)$',[20,28],[-13616547]],
        'clip_bbox': [(0,65,170,812)],
        'line_x': 170.0,
        'data': [[7,14], [-13948375], 30.0, ['Calibri-Bold']]}
    
    def __init__(self, path: str,dry:str,fin:str, rep:str):
        super().__init__(path,dry,fin,rep, self.PARAMS)   

    #REGEX
    def __extract_dum_data(self,main_key,data:list):
        return {main_key:data}
    
    def __extract_inv_data(self,main_key:str, data:list):            
        return {main_key: ' '.join(data).strip()}
    
    def __extract_nav_data(self,main_key:str, data:list):
        pattern = r'(.+?Option|.+?Plan)\s([\d.]+)'
        final_dict = {}
        nav_data = data
        for text in nav_data:
            text = re.sub(r"[\^#*\$]", "", text.strip())
            if matches := re.findall(pattern, text, re.IGNORECASE):
                for key, value in matches:
                    final_dict[key] = value
        
        return {main_key: final_dict}
    
    def __extract_metric_data(self,main_key:str, data:list):
        pattern =  r'(Monthly AAUM|Latest AUM\s\(.*\)|Beta|Portfolio Turnover Ratio|Standard Deviation|Sharpe Ratio|Average Maturity|YTM|Macaulay Duration|Modified Duration)\s*([\d,.]+)'
        final_dict = {}
        metric_data = data
        for text in metric_data:
            text = re.sub(r"[\^#*\$]", "", text.strip())
            if matches := re.findall(pattern, text, re.IGNORECASE):
                for key, value in matches:
                    final_dict[key] = value
        
        return {main_key: final_dict}
    
    def __extract_manager_data(self,main_key:str, data:list):
        pattern = r''
        final_list = []
        manager_data = " ".join(data)
        manager_data = re.sub(r"[\^#*\$]", "", manager_data.strip())
        matches = re.findall(pattern, manager_data, re.IGNORECASE)
        for match in matches:
            name,exp,temp,since = match
            final_list.append({
                "name":name.strip(),
                "designation": "",
                "experience": exp,
                "managing_since": since
            })
        return {main_key:final_list}
    
    def __extract_min_data(self,main_key:str,data:list):
        pattern = r'Minimum Application Amount\s*(.*)\.\s*Additional Application Amount\s*(.*)'
        min_data = " ".join(data)
        final_dict = {}
        if matches:= re.findall(pattern, min_data, re.IGNORECASE):
            for min,add in matches:
                final_dict['Minimum Application Amount'] = min
                final_dict['Additional Application Amount'] = add
        
        return {main_key:final_dict}
    
    def __extract_ter_data(self,main_key:str,data:list):
        pattern = r'(Regular|Direct)\s*([\d,.]+)%?'
        ter_data = data
        final_dict = {}
        for text in ter_data:
            text =  re.sub(r"[\^#*\$]", "", text.strip())
            if matches:= re.findall(pattern, text, re.IGNORECASE):
                for key, value in matches:
                    final_dict[key] = value
        
        return {main_key:final_dict}
    
    def __extract_load_data(self,main_key:str, data:list):
        
        load_data = " ".join(data)
        final_dict = {}
        entry_pattern = r"Entry Load\s*:\s*(.+)"
        exit_pattern = r"Exit Load\s*:\s*(.+?)(?=Entry Load|$)"

        # Extract Entry Load and Exit Load from each string
       
        entry_load = re.search(entry_pattern, load_data, re.IGNORECASE)
        exit_load = re.search(exit_pattern, load_data, re.IGNORECASE)

        entry_load_text = entry_load.group(1) if entry_load else "Not Found"
        exit_load_text = exit_load.group(1) if exit_load else "Not Found"
        final_dict['Entry Load'] = entry_load_text
        final_dict['Exit Load'] = exit_load_text
        
        return {main_key:final_dict}
        
         
    #MAPPING
    def match_regex_to_content(self, string:str, data:list):
        check_header = string
        if re.match(r"^(investment|benchmark|redemption|inception|category).*", check_header, re.IGNORECASE):
            return self.__extract_inv_data(string,data)
        elif re.match(r"^nav.*", check_header, re.IGNORECASE):
            return self.__extract_nav_data(string,data)
        elif re.match(r"^metric.*", check_header, re.IGNORECASE):
            return self.__extract_metric_data(string,data)
        elif re.match(r"^minimum.*", check_header, re.IGNORECASE):
            return self.__extract_min_data(string,data)
        elif re.match(r"^total.*", check_header, re.IGNORECASE):
            return self.__extract_ter_data(string,data)
        elif re.match(r"^load.*", check_header, re.IGNORECASE):
            return self.__extract_load_data(string,data)
        return self.__extract_dum_data(string,data) 
    
class NJMF(Reader):
    PARAMS = {
        'fund': [[20,16,0], r'^(NJ).*(Fund|ETF|EOF|FOF|FTF|Path|Scheme)$',[16,24],[-13604430]],
        'clip_bbox': [(0,5,250,812)],
        'line_x': 250.0,
        'data': [[6,11], [-14475488], 30.0, ['Swiss721BT-Medium']]}
    
    def __init__(self, path: str,dry:str,fin:str, rep:str):
        super().__init__(path,dry,fin,rep, self.PARAMS)
        
    #REGEX
    def __extract_dum_data(self,main_key,data:list):
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
    def match_regex_to_content(self, string:str, data:list):
        check_header = string
        if re.match(r"^(exit|entry|investment|date_of|options|plans|benchmark|additional_bench|monthly_average|closing_aum|type_of).*", check_header, re.IGNORECASE):
            return self.__extract_inv_data(string,data)
        elif re.match(r"^nav.*", check_header, re.IGNORECASE):
            return self.__extract_nav_data(string,data)
        elif re.match(r"^total.*", check_header, re.IGNORECASE):
            return self.__extract_ter_data(string,data)
        elif re.match(r"^metric.*", check_header, re.IGNORECASE):
            return self.__extract_metric_data(string,data)
        return self.__extract_dum_data(string,data)

               
class QuantMF(Reader):
    PARAMS = {
        'fund': [[16,0], r'^(quant).*(Fund|ETF|EOF|FOF|FTF|Path)$',[16,24],[-13604430]],
        'clip_bbox': [(0,5,180,812)],
        'line_x': 180.0,
        'data': [[6,11], [-16777216], 30.0, ['Calibri,Bold',]]}
    
    def __init__(self, path: str,dry:str,fin:str, rep:str):
        super().__init__(path,dry,fin,rep,self.PARAMS)

class Sundaram(Reader):
    PARAMS = {
        'fund': [[4,0], r'^(Sundaram).*(Fund|ETF|EOF|FOF|FTF|Path|Fund*|Fund -)$|^Sundaram',[14,18],[-16625248]],
        'clip_bbox': [(0,5,220,812)],
        'line_x': 220.0,
        'data': [[6,13], [-1], 30.0, ['UniversNextforMORNW02-Cn',]]}
    
    def __init__(self, path: str,dry:str,fin:str, rep:str):
        super().__init__(path,dry,fin,rep, self.PARAMS)
        
        
    #REGEX
    def __extract_dum_data(self,main_key,data:list):
        return {main_key:data}
    
    def __extract_inv_data(self,main_key:str, data:list):            
        return {main_key: ' '.join(data).strip()}
    
    def __extract_nav_data(self,main_key:str, data:list):
        pattern = r'(Growth|IDCW)\s*(-?[\d,.]+)\s*(-?[\d,.]+)'
        final_dict = {}
        nav_data = data
        for text in nav_data:
            text = re.sub(r"[\^#*\$]", "", text.strip())
            if matches := re.findall(pattern, text, re.IGNORECASE):
                for key, regular, direct in matches:
                    final_dict[f'Regular {key}'] = regular
                    final_dict[f'Direct {key}'] = direct
        return {main_key: final_dict}
    
    def __extract_metric_data(self,main_key:str, data:list):
        pattern = r'(Information Ratio|Turnover Ratio|Standard Deviation|Beta|Sharpe Ratio|Average Maturity|Modified Duration|Yield to Maturity|Macaulay Duration)\s*(-?[\d\.,]+)'
        final_dict = {}
        metric_data = data
        for text in metric_data:
            text = re.sub(r"[\^#*\$,]", "", text.strip())
            if matches := re.findall(pattern, text, re.IGNORECASE):
                for key, value in matches:
                    final_dict[key] = value
        
        return {main_key: final_dict}
    
    def __extract_scheme_data(self, main_key:str, data:list):
        # Define start and end markers
        mention_start = [
            "Category",
            "Fund Managers",
            "Month End AUM",
            "Avg. AUM",
            "Inception Date",
            "Benchmark",
            "Additional Benchmark",
            "Plans",
            "Options",
            "Minimum Amount",
            r"SIP\s*/\s*STP\s*/\s*SWP",
            "Exit Load"
        ]
        
        mention_end = mention_start[1:] + ["End_of_Data"]

        # Generate regex patterns dynamically
        patterns = [r"({start}\s*)(.+?)({end}|$)".format(start=start, end=end)
            for start, end in zip(mention_start, mention_end)]
        final_dict = {}
        scheme_data = " ".join(data)
        scheme_data = re.sub(r"[\^#*\$:;]", "", scheme_data)
        
        for pattern in patterns:
            if matches:= re.findall(pattern, scheme_data, re.DOTALL|re.IGNORECASE): #not used ignorecase
                for match in matches:
                    key, value, dummy = match
                    value = value.strip()
                    final_dict[key.strip()] = value

        return {main_key:final_dict}
    
    #MAPPING
    def match_regex_to_content(self, string:str, data:list):
        check_header = string
        if re.match(r"^(exit|entry|investment).*", check_header, re.IGNORECASE):
            return self.__extract_inv_data(string,data)
        elif re.match(r"^nav.*", check_header, re.IGNORECASE):
            return self.__extract_nav_data(string,data)
        elif re.match(r"^metric.*", check_header, re.IGNORECASE):
            return self.__extract_metric_data(string,data)
        elif re.match(r"^scheme.*", check_header, re.IGNORECASE):
            return self.__extract_scheme_data(string,data)
        return self.__extract_dum_data(string,data)

class Taurus(Reader):
    PARAMS = {
        'fund': [[4,20], r'^(Taurus).*(Fund|ETF|EOF|FOF|FTF|Path|Fund*)$',[13,24],[-9754846]],
        'clip_bbox': [(0,65,210,812)],
        'line_x': 210.0,
        'data': [[6,12], [-9754846], 30.0, ['Calibri-Bold']]}
    
    def __init__(self, path: str,dry:str,fin:str, rep:str):
        super().__init__(path,dry,fin,rep, self.PARAMS)

    #REGEX
    def __extract_dum_data(self,main_key,data:list):
        return {main_key:data}
    
    def __extract_inv_data(self,main_key:str, data:list):            
        return {main_key: ' '.join(data).strip()}
    
     #MAPPING
    def match_regex_to_content(self, string:str, data:list):
        check_header = string
        if re.match(r"^(minimum_appl|benchmark|date|investment).*", check_header, re.IGNORECASE):
            return self.__extract_inv_data(string,data)
        return self.__extract_dum_data(string,data)
 
 
class Trust(Reader):
    
    PARAMS = {
        'fund': [[4,20], r'^(Trust).*(Fund|ETF|EOF|FOF|FTF|Path|Fund*)$',[16,22],[-1]],
        'clip_bbox': [(0,65,180,812)],
        'line_x': 180.0,
        'data': [[7,12], [-1, -14475488], 30.0, ['Roboto-Bold']]}
    
    def __init__(self, path: str,dry:str,fin:str, rep:str):
        super().__init__(path,dry,fin,rep, self.PARAMS)

class UTI(Reader):
    PARAMS = {
        'fund': [[20], r'^(UTI).*(Fund|ETF|EOF|FOF|FTF|Path|Fund\*|Plan\*|Duration)$',[14,24],[-65794]],
        'clip_bbox': [(0,65,200,812)],
        'line_x': 200.0,
        'data': [[7,10], [-65794,-1], 30.0, ['Calibri-Bold']]}
    
    def __init__(self, path: str,dry:str,fin:str, rep:str):
        super().__init__(path,dry,fin,rep, self.PARAMS)
        
    #REGEX
    def __return_dummy_data(self,main_key:str,data:list):
        return{main_key:data}
    def __extract_invest_data(self,main_key:str,data:list):
        return {main_key: " ".join(data)}
    def __extract_manager_data(self,main_key:str,data:list):
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
    
    def __extract_nav_data(self,main_key:str, data:list):
        nav_data = data
        final_dict = {}
        pattern = r'^(Regular|Direct)[\s:]+([\d]+\.\d+)'
        for text in nav_data:
            text = text.strip()
            matches = re.findall(pattern, text, re.IGNORECASE)
            for key, value in matches:
                final_dict[key] = value  # Example: {"Regular": "1.75", "Direct": "0.94"}
    
        return {main_key: final_dict}
    
    #MAPPING FUNCTION
    def match_regex_to_content(self,string:str, data:list):
        check_header = string
        if re.match(r"^(benchmark|scheme_launch|additional).*", check_header, re.IGNORECASE):
            return self.__extract_invest_data(string,data)
        elif re.match(r"^investment.*", check_header, re.IGNORECASE):
            return self.__extract_invest_data(string, data) #since its a comment
        elif re.match(r"^fund_mana.*", check_header, re.IGNORECASE):
            return self.__extract_manager_data(string, data)
        elif re.match(r"^total.*", check_header, re.IGNORECASE):
            return self.__extract_total_exp_data(string, data)
        elif re.match(r"^nav.*", check_header, re.IGNORECASE):
            return self.__extract_nav_data(string, data)
        else:
            return self.__return_dummy_data(string,data)

class WhiteOak(Reader):
    PARAMS = {
        'fund': [[20], r'^(whiteOak).*(Fund|ETF|EOF|FOF|FTF|Path|Fund\*|Plan\*|Duration)$',[16,24],[-13159371]],
        'clip_bbox': [(0, 85, 240, 812)],
        'line_x': 240.0,
        'data': [[7,11], [-65794,-1], 30.0, ['MyriadPro-Bold']]}
    
    def __init__(self, path: str,dry:str,fin:str, rep:str):
        super().__init__(path,dry,fin,rep, self.PARAMS)
    
    #Fund Regex  
    def __return_dummy_data(self,main_key:str,data:list):
        return{main_key:data}
    def __extract_invest_data(self,main_key:str,data:list):
        return {main_key: " ".join(data)}

    def __extract_aum_data(self,main_key:str, data:list):
        aum_data = data
        aum_pattern = r'(Monthly Average AUM|Month End AUM)\s*([\d.]+)\s*Crore'
        final_dict = {}
        for text in aum_data:
            text = text.lower()
            if matches:= re.findall(aum_pattern, text, re.IGNORECASE):
                for key, value in matches:
                    final_dict[key] = value
        return {main_key:final_dict}

    
    #MAPPING FUNCTION
    def match_regex_to_content(self,string:str, data:list):
        check_header = string
        if re.match(r"^(benchmark|scheme_launch|additional).*", check_header, re.IGNORECASE):
            return self.__extract_invest_data(string,data)
        elif re.match(r"^aum.*", check_header, re.IGNORECASE):
            return self.__extract_aum_data(string, data)
        elif re.match(r"^aum.*", check_header, re.IGNORECASE):
            return self.__extract_aum_data(string, data)
        elif re.match(r"^metric.*", check_header, re.IGNORECASE):
            return self.__extract_invest_data(string, data) #since its a comment
        else:
            return self.__return_dummy_data(string,data)

     
class BajajFinServ(Reader):
    
    PARAMS = {
        'fund': [[20],r'Bajaj.*(Fund|Path|ETF|FOF|EOF)$',[14,24],[-16753236]], #FUND NAME DETAILS order-> flag, regex_fund_name, font_size, font_color
        'clip_bbox': [(360,5,612,812)],
        'line_x': 180.0,
        'data': [[6,12],[-1,-15376468],30.0,['Rubik-SemiBold']] #sizes, color, set_size
    }
    
    def __init__(self, path: str,dry:str,fin:str, rep:str):
        super().__init__(path,dry,fin,rep, self.PARAMS)
    
    #Fund Regex  
    def __return_dummy_data(self,main_key:str,data:list):
        return{main_key:data}
    def __extract_fund_data(self,main_key:str, data:list):
        return {main_key:data}
    def __return_invest_data(self,main_key:str,data:list):
        return {main_key: " ".join(data)}

    def __extract_nav_data(self,main_key:str, data:list):
        nav_data = data
        final_dict = {}
        pattern = r'^(Direct Growth|Direct IDCW|Regular Growth|Regular IDCW)[\s]+([\d]+\.\d+)'
        
        final_dict = {}
        for text in nav_data:
            text = text.lower()
            matches = re.findall(pattern, text, re.IGNORECASE)
            for key, value in matches:
                final_dict[key] = value
        return {main_key:final_dict}
    
    
    #MAPPING FUNCTION
    def match_regex_to_content(self,string:str, data:list):
        check_header = string
        if re.match(r"^(investment|minimum|entry|exit|load|plans|scheme_launch|benchmark).*", check_header, re.IGNORECASE):
            return self.__return_invest_data(string,data)
        elif re.match(r"^fund_mana.*", check_header, re.IGNORECASE):
            return self.__extract_fund_data(string, data)
        elif re.match(r"^nav.*", check_header, re.IGNORECASE):
            return self.__extract_nav_data(string, data)
        else:
            return self.__return_dummy_data(string,data)
        
class ThreeSixtyOne(Reader):
    
    PARAMS = {
        'fund': [[20],r'360 ONE.*(Fund|Path|ETF|FOF|EOF)$',[18,24],[-16777216]], #FUND NAME DETAILS order-> flag, regex_fund_name, font_size, font_color
        'clip_bbox': [(0,5,160,812)],
        'line_x': 160.0,
        'data': [[6,10],[-10791002],30.0,['SpaceGrotesk-SemiBold']] #sizes, color, set_size
    }
    
    def __init__(self, path: str,dry:str,fin:str, rep:str):
        super().__init__(path,dry,fin,rep, self.PARAMS)
        
    #Fund Regex
    def __return_dummy_data(self,main_key:str,data:list):
        return{main_key:data}
    
    def __extract_aum_data(self,main_key:str, data:list):
        aum_data = data
        final_dict = {}
        pattern = r'^(Net AUM|Monthly Average AUM)\s([\d,?]+\.\d+)'
        for text in aum_data:
            text = text.strip()
            matches = re.findall(pattern, text, re.IGNORECASE)
            for key, value in matches:
                final_dict[key] = value
        return {main_key:final_dict}

    def __extract_metrics_data(self, main_key: str, data: list):
        metrics_data = data
        final_dict = {}
        pattern = r'^(Std\. Dev|Sharpe Ratio|Portfolio Beta|R Squared|Treynor)\s+(NA|\d+\.\d+)\s+(NA|\d+\.\d+)'

        for text in metrics_data:
            text = text.strip()
            matches = re.findall(pattern, text, re.IGNORECASE)
            for key, fund_value, benchmark_value in matches:
                final_dict[key] = {"fund": fund_value, "benchmark": benchmark_value}

        return {main_key: final_dict}


    def __extract_total_expense_data(self, main_key:str, data:list):
        total_data = data
        final_dict = {}
        pattern = r'^(Regular Plan|Direct Plan)\s?(NA|\d+\.\d+)'
        for text in total_data:
            text = text.strip()
            matches = re.findall(pattern, text, re.IGNORECASE)
            for key, value in matches:
                final_dict[key] = value
                
        return {main_key:final_dict}
    def __extract_nav_data(self,main_key:str, data:list):
        nav_data = data
        final_dict = {}
        pattern = r'^(Regular(?: Plan)?(?: -)?(?: Growth| IDCW| Bonus| Weekly IDCW| Quarterly IDCW| Half Yearly IDCW| Monthly IDCW| Daily IDCW)|Direct(?: Plan)?(?: -)?(?: Growth| IDCW| Weekly IDCW| Quarterly IDCW| Monthly IDCW| Daily IDCW))\s*([\d.]+)'
        
        final_dict = {}
        for text in nav_data:
            text = text.lower()
            matches = re.findall(pattern, text, re.IGNORECASE)
            for key, value in matches:
                final_dict[key] = value
        return {main_key:final_dict}

    def __extract_scheme_data(self, main_key: str, data: list):
        scheme_data = data
        final_dict = {}
        # Regex patterns
        pattern = r'^(Dematerialization|Portfolio Turnover|Options Offered|Bloomberg Code|Benchmark Index|Date of Allotment|Plans Offered)\s*[:]?[\s]*(.*)'
        load_pattern = r'Entry Load\s*:\s*(.*?)\s*Exit Load\s*:\s*(.*?)\s*(?=Dematerialization|Dematerialisation|Portfolio Turnover|Tracking Error|Asset Allocation|Investor exit upon Exit load|$)'

        final_dict = {}
        min_app, add_pur = "", ""
        rest_data = []
        for count,text in enumerate(scheme_data):
            text = text.strip()
            if matches := re.findall(pattern, text, re.IGNORECASE):
                for key, value in matches:
                    final_dict[key] = value
            elif re.match(r'^(New Purchase|Minimum Application).*', text, re.IGNORECASE):
                 txt = text + scheme_data[count+1]
                 min_app+=f' {txt}'
            elif re.match(r'^Additional Purchase.*', text, re.IGNORECASE):
                 txt = text + scheme_data[count+1]
                 add_pur+=f' {txt}'
            else:
                rest_data.append(text)
        
        # Extract Entry Load and Exit Load
        text_data = " ".join(scheme_data)
        matches = re.search(load_pattern, text_data, re.IGNORECASE | re.DOTALL)
        if matches:
            final_dict["Entry Load"] = matches.group(1).strip()
            final_dict["Exit Load"] = matches.group(2).strip()

        # Store extracted data
        #final_dict['rest'] = rest_data
        final_dict['Minimum Application Amount'] = min_app.replace("Minimum Application", "").strip()
        final_dict['Additional Purchase Amount'] = add_pur.replace("Additional Purchase", "").strip()

        return {main_key: final_dict}
    
    def __extract_invest_data(self,main_key:str,data:list):
        return {main_key: " ".join(data)}
    
    def __extract_manager_data(self,main_key:str,data:list):
        return {main_key: " ".join(data)}
    
    #MAPPING FUNCTION
    def match_regex_to_content(self,string:str, data:list):
        check_header = string
        if re.match(r"^investment.*", check_header, re.IGNORECASE):
            return self.__extract_invest_data(string,data)
        elif re.match(r"^aum.*", check_header, re.IGNORECASE):
            return self.__extract_aum_data(string, data)
        elif re.match(r"^nav.*", check_header, re.IGNORECASE):
            return self.__extract_nav_data(string, data)
        elif re.match(r"^metrics.*", check_header, re.IGNORECASE):
            return self.__extract_metrics_data(string, data)
        elif re.match(r"^scheme.*", check_header, re.IGNORECASE):
            return self.__extract_scheme_data(string, data)
        elif re.match(r"^total.*", check_header, re.IGNORECASE):
            return self.__extract_total_expense_data(string, data)
        elif re.match(r"^(fund_mana|co_fund).*", check_header, re.IGNORECASE):
            return self.__extract_manager_data(string, data)
        else:
            return self.__return_dummy_data(string,data)
        
class BarodaBNP(Reader):
    PARAMS = {
        'fund': [[0],r'^Baroda BNP',[12,18],[-13619152]], #FUND NAME DETAILS order-> flag, regex_fund_name, font_size, font_color
        'clip_bbox': [(0,65,210, 700)],
        'line_x': 210.0,
        'data': [[7,10],[-12566464,],30.0,['Unnamed-T3']] #sizes, color, set_size
    }
    
    def __init__(self, path: str,dry:str,fin:str, rep:str):
        super().__init__(path,dry,fin,rep,self.PARAMS)
        
    #FundRegex
    def __return_dummy_data(self,main_key:str,data:list):
        return{main_key:data}
    def __extract_invest_data(self,main_key:str,data:list):
        return {main_key: " ".join(data)}
    
    def __extract_date_data(self,main_key:str, data:list):
        date_data = data
        final_txt = ""
        date_pattern = r'^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec).*'
        for text in date_data:
            if re.match(date_pattern, text, re.IGNORECASE):
                final_txt+= text
        return{main_key:final_txt}
    
    def __extract_metric_data(self, main_key:str, data:list):
        metric_data = data
        pattern = r'([\w\s-]+?)\s*(?:\([\w\s%-]*\)|\*)?\s*([\d.]+)%?'
        final_dict = {}
        for text in metric_data:
            text = text.lower()
            matches = re.findall(pattern, text, re.IGNORECASE)
            for key, value in matches:
                final_dict[key] = value
    
    def __extract_nav_data(self, main_key:str, data:list):
        nav_data = data
        pattern = r'([\w\s-]+?)\s*(?:\([\w\s%-]*\)|\*)?\s*([\d.]+)%?'
        final_dict = {}
        for text in nav_data:
            text = text.lower()
            matches = re.findall(pattern, text, re.IGNORECASE)
            for key, value in matches:
                final_dict[key] = value
        
        return{main_key:final_dict}
    def __extract_metric_data(self,main_key:str,data:list):
        nav_data = data
        pattern = r'^(TER - Regular Plan|TER - Direct Plan|Portfolio Turnover Ratio|Standard Deviation|Beta|Sharpe Ratio|Tracking Error Regular|Tracking Error Direct|Tracking Error|Average Maturity|Modified Duration|YTM|Macaulay Duration)\s*(?:\([\w\s%-]*\)|\*)?\s*([\d.]+)%?'
        final_dict = {}
        for text in nav_data:
            text = text.lower()
            matches = re.findall(pattern, text, re.IGNORECASE)
            for key, value in matches:
                final_dict[key] = value
        
        return{main_key:final_dict}
    
    def __extract_manager_data(self, main_key:str, data:list):
        manager_data = data
        final_list = []
        pattern = r'(Mr\.|Ms\.)\s([A-Za-z\s]+)\s(\d{2}-[A-Za-z]{3}-\d{2,4})\s(\d+)\syears'
        for text in manager_data:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for title, name, date, experience in matches:
                final_list.append({
                    'name': f"{title} {name.strip()}",
                    "designation": '',
                    'managing_since': date,
                    'experience': int(experience)
                })
        
        return {main_key:final_list}
    
    #FundRegex MAPPING FUNCTION
    def match_regex_to_content(self,string:str, data:list):
        
        check_header = string
        
        if re.match(r"^invest.*", check_header, re.IGNORECASE):
            return self.__extract_invest_data(string,data)
        elif re.match(r"^fund_mana.*", check_header, re.IGNORECASE):
            return self.__extract_manager_data(string, data)
        elif re.match(r"^nav.*", check_header, re.IGNORECASE):
            return self.__extract_nav_data(string, data)
        elif re.match(r"^scheme_launch.*", check_header, re.IGNORECASE):
            return self.__extract_date_data(string, data)
        elif re.match(r"^metric.*", check_header, re.IGNORECASE):
            return self.__extract_metric_data(string, data)
        elif re.match(r"^bench.*", check_header, re.IGNORECASE):
            return self.__extract_invest_data(string, data)
        else:
            return self.__return_dummy_data(string,data)
        
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
        
    #FundRegex
    def __return_dummy_data(self,main_key:str,data:list):
        return{main_key:data}
    def __extract_fund_data(self,main_key:str, data:list):
        return {main_key:data}
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
                final_dict[key] = FundRegex.extract_decimals(value)
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
                        final_dict[key] = FundRegex.extract_decimals(value)
        return {main_key:final_dict}
    
    def __extract_scheme_data(self,main_key:str, data:list):
        final_dict = {}
        pattern = r'^(Inception Date.*|Index|Minimum Application Amount|Portfolio Turnover Ratio.*)[\s:]+(.*)'    
        for text in data:
            text = text.lower()
            matches = re.findall(pattern, text, re.IGNORECASE)
            for key, value in matches:
                final_dict[key] = value
        return {main_key:final_dict}
    
    #FundRegex MAPPING FUNCTION
    def match_regex_to_content(self,string:str, data:list):
        
        check_header = string
        
        if re.match(r"^investment.*", check_header, re.IGNORECASE):
            return self.__return_invest_data(string,data)
        elif re.match(r"^nav.*", check_header, re.IGNORECASE):
            return self.__extract_nav_data(string, data)
        elif re.match(r"^aum.*", check_header, re.IGNORECASE):
            return self.__extract_aum_data(string, data)
        elif re.match(r"^scheme.*", check_header, re.IGNORECASE):
            return self.__extract_scheme_data(string, data)
        elif re.match(r"^fund_mana.*", check_header, re.IGNORECASE):
            return self.__extract_fund_data(string, data)
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
        pattern = r'(Month end AUM|Monthly average AUM|Quarterly average AUM)[\s?:]+([\d]+\.\d+)'
        for text in aum_data:
            text = text.lower()
            matches = re.findall(pattern, text, re.IGNORECASE)
            for key, value in matches:
                final_dict[key] = value
        return {main_key:final_dict}
    
    def __return_quant_data(self,main_key:str, data:list):
        quant_data = data
        final_dict = {}
        pattern = r'(Portfolio Turnover Ratio|Tracking Error|Average Maturity|Macaulay Duration)[\s?:]+([\d]+\.\d+)'
        for text in quant_data:
            text = text.lower()
            matches = re.findall(pattern, text, re.IGNORECASE)
            for key, value in matches:
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
    
    #FundRegex MAPPING FUNCTION
    def match_regex_to_content(self,string:str, data:list, *args):
        
        check_header = string
        
        if re.match(r"^investment.*", check_header, re.IGNORECASE):
            return self.__return_invest_data(string,data)
        elif re.match(r"^scheme.*", check_header, re.IGNORECASE):
            return self.__return_scheme_data(string, data)
        
        elif re.match(r"^(quant|metrics).*", check_header, re.IGNORECASE):
            return self.__return_quant_data(string, data)
        
        elif re.match(r".*(managers|manager)$", check_header, re.IGNORECASE):
            return self.__return_manager_data(string, data)
        
        elif re.match(r"^aum", check_header, re.IGNORECASE):
            return self.__return_aum_data(string, data)
        
        else:
            return self.__return_dummy_data(string,data)   
  
#something