import re, os, pprint, json, json5
from app.pdfParse import Reader
from app.fundRegex import FundRegex
import fitz

class GrandFundData:
    
    def __init__(self):
        pass
    
    def _extract_dummy_data(self,key:str,data):
        return {key:data}
    
    def _extract_scheme_data(self,main_key:str,data:list, pattern:str):
        regex_ = self.REGEX[pattern] #list
        mention_start = regex_[:-1]
        mention_end = regex_[1:]

        patterns = [r"({start})\s*(.+?)\s*({end}|$)".format(start=start, end=end)
            for start, end in zip(mention_start, mention_end)]
        
        final_dict = {}
        scheme_data = " ".join(data)
        scheme_data = re.sub(r'[^A-Za-z0-9\-,.\(\)\s]+',"", scheme_data).strip()
        for pattern in patterns:
            if matches:= re.findall(pattern, scheme_data, re.DOTALL|re.IGNORECASE):
                for match in matches:
                    key, value, dummy = match
                    value = value.strip()
                    final_dict[key] = value
        
        return {main_key:final_dict}
    
    def _extract_str_data(self, key: str, data: list):
        return {key: ' '.join(data)}
    
    def _extract_generic_data(self, main_key: str, data: list, pattern: str):
        final_dict = {}
        for text in data:
            text = re.sub(self.REGEX['escape'], "", text.strip())
            matches = re.findall(self.REGEX[pattern], text, re.IGNORECASE)
            for match in matches:
                if len(match) == 2:
                    key, value = match
                    final_dict[key.strip()] = value.strip()
                elif len(match) == 3:
                    key,v1,v2 = match
                    final_dict[key.strip()] = v1.strip()
                elif isinstance(match,str):
                    return {main_key:match}
                
        return {main_key:final_dict}

    def _extract_load_data(self,main_key:str,data:list, pattern:str):
        load_data = " ".join(data)
        load_data = re.sub(self.REGEX['escape'], "", load_data).strip()
        final_dict = {}
        if matches:= re.findall(self.REGEX[pattern],load_data.strip(), re.IGNORECASE):
            for match in matches:
                entry_,exit_ = match
            
            final_dict['entry_load'] = entry_,
            final_dict['exit_load'] = exit_
        return {main_key:final_dict}
     
    def _extract_amt_data(self,main_key:str, data, pattern:str):

        amt_data = " ".join(data) if isinstance(data,list) else data
        amt_data = re.sub(self.REGEX['escape'],"",amt_data).strip()
        matches = re.findall(self.REGEX[pattern],amt_data,re.IGNORECASE)
        final_dict = {}
        for match in matches:
            amt, thraftr = match
            final_dict['amt'], final_dict['thraftr'] = amt,thraftr
        return {main_key:final_dict}
    
    def match_regex_to_content(self, string: str, data: list,*args):
        for pattern, (func_name, regex_key) in self.__class__.PATTERN_TO_FUNCTION.items():
            if re.match(pattern, string, re.IGNORECASE):
                func = getattr(self, func_name) #dynamic function lookup
                if regex_key:
                    return func(string, data, regex_key)
                return func(string, data)
        return self._extract_dummy_data(string, data)
    
    def secondary_match_regex_to_content(self, string: str, data: list,*args):
        for pattern, (func_name, regex_key) in self.__class__.SECONDARY_PATTERN_TO_FUNCTION.items():
            if re.match(pattern, string, re.IGNORECASE):
                func = getattr(self, func_name) #dynamic function lookup
                if regex_key:
                    return func(string, data, regex_key)
                return func(string, data)
        return self._extract_dummy_data(string, data)

# 1 <>
class Samco(Reader, GrandFundData):
    CONFIG_PATH = os.path.join(os.getcwd(),"data\\config\\example.json5") 

    with open(CONFIG_PATH, "r") as file:
        config = json.load(file)

    PARAMS = config["PARAMS"]
    REGEX = config["REGEX"]
    PATTERN_TO_FUNCTION = config["PATTERN_TO_FUNCTION"]

    def __init__(self, paths_config: str):
        super().__init__(paths_config, self.PARAMS)

    def _extract_manager_data(self, main_key: str, data: list, pattern: str):
        final_list = []
        for i in range(0, len(data), 3):
            txt = " ".join(data[i:i+3])
            txt = re.sub(self.REGEX['escape'], "", txt).strip()
            if matches := re.findall(self.REGEX[pattern], txt, re.IGNORECASE):
                for match in matches:
                    name, desig, since, exp = match
                    final_list.append({
                        "name": name,
                        "designation": desig,
                        "managing_since": since,
                        "experience": exp
                    })
        return {main_key: final_list}
# 2
class Tata(Reader):
    
    PARAMS = {
        'fund': [[25,20,0,16],r"^tata.*(fund|etf|fof|eof|funds|plan|\))$",[10,20],[-1]], #[flag], regex_fund_name, range(font_size), [font_color]
        'clip_bbox': [(0,50,160,750)],
        'line_x': 160.0,
        'data': [[5,8],[-15570765],30.0,['Swiss721BT-BoldCondensed']], #sizes, color, set_size font_name
        'content_size':[30.0,10.0]
    }
    
    def __init__(self, paths_config:str):
        super().__init__(paths_config, self.PARAMS)
    
    #FundRegex FUNCTIONS
    def __extract_inv_data(self,key:str, data:list):
        return {key: ' '.join(data)}
    
    def __extract_manager_data(self,main_key:str, data:list):
        manager_data = " ".join(data)
        manager_data = re.sub(r'[\^\-,:]+'," ", manager_data.strip())
        pattern = r'([A-Za-z\s]+)\s*\(Managing Since\s*([A-Za-z0-9\s]+) and overall experience of ([a-z0-9\s]+)\)'

        final_list = []
        if matches:=re.findall(pattern,manager_data,re.IGNORECASE):
            for match in matches:
                name,since,exp = match
                final_list.append({
                    "name":name,
                    "designation": "",
                    "managing_since": since,
                    "experience": exp
                })
        
        return {main_key:final_list}  

    def __extract_metric_data(self, main_key:str, data:list): 
        metric_data = data
        pattern = r'(Std. Dev|Sharpe Ratio|Portfolio Beta|R Squared|Treynor|Jenson)\s+([\d.-]+|NA)\s+([\d.-]+|NA)'
        final_dict = {}
        for text in metric_data:
            text = re.sub(r"[\-\^*\$:;~]", "", text.strip())
            matches = re.findall(pattern, text, re.IGNORECASE)
            for key, value1, value2 in matches:
                final_dict[key] = value1
        return {main_key:final_dict}
    
    def __extract_nav_data(self, main_key:str, data:list): 
        nav_data = data
        pattern = r'((?:Regular|Direct|Reg)\s*(?:Growth|IDCW))\s*([\d,.]+)'
        final_dict = {}
        for text in nav_data:
            text = re.sub(r"[\-\^*\$:;~]", "", text.strip())
            matches = re.findall(pattern, text, re.IGNORECASE)
            for key, value in matches:
                final_dict[key] = value
        return {main_key:final_dict}
    
    def __extract_expense_data(self, main_key:str, data:list): 
        expense_data = data
        pattern = r'(Regular|Direct)\s*([\d,.]+)'
        final_dict = {}
        for text in expense_data:
            text = re.sub(r"[\-\^*\$:;~]", "", text.strip())
            matches = re.findall(pattern, text, re.IGNORECASE)
            for key, value in matches:
                final_dict[key] = value
        return {main_key:final_dict}
    
    def __extract_load_data(self, main_key:str, data:list): 
        load_data = " ".join(data)
        load_data = re.sub(r'[\^\-,:]+'," ", load_data.strip())
        entry_pattern = r"Entry Load\s*(NA|Not Applicable|\s*)\s*Exit Load"
        exit_pattern = r"Exit Load\s*(.*?)$" 

        entry_loads = re.findall(entry_pattern, load_data, re.IGNORECASE)
        exit_loads = re.findall(exit_pattern, load_data, re.IGNORECASE | re.DOTALL)

        final_dict = {
            "Entry Load": " ".join(entry_loads),
            "Exit Load": " ".join(exit_loads)
        }
        return {main_key:final_dict}
    
    def __extract_dec_data(self,main_key,data:list):
        pattern = r'([\d,]+\.\d+)'
        final_text = ''
        for text in data:
            if matches:= re.findall(pattern, text, re.IGNORECASE):
                for value in matches:
                    final_text+=value

        return{main_key:final_text}
    def match_regex_to_content(self, string: str, data: list):
        pattern_to_function = {
            r"^(date|investment|multiples|benchmark|scheme_launch).*": self.__extract_inv_data,
            r"^nav.*": self.__extract_nav_data,
            r"^(aum|monthly_average|portfolio_turnover).*": self.__extract_dec_data,
            r"^metrics.*": self.__extract_metric_data,
            # r"^load.*": self.__extract_load_data,
            r".*(manager|managers)$": self.__extract_manager_data,
            r"^expense.*": self.__extract_expense_data,
        }

        for pattern, func in pattern_to_function.items():
            if re.match(pattern, string, re.IGNORECASE):
                return func(string, data)

        return {string:data}

# 3 <>
class FranklinTempleton(Reader,GrandFundData):
    PARAMS = {
        'fund': [[25,20],r"^(Franklin|Templeton).*$",[16,24],[-65794]], #[flag], regex_fund_name, range(font_size), [font_color]
        'clip_bbox': [(0,100,180,812)],
        'line_x': 180.0,
        'data': [[6,9],[-16751720],30.0,['ZurichBT-BoldCondensed']], #sizes, color, set_size font_name
        'content_size':[30.0,10.0]
    }
    
    REGEX = {
        'nav': r'(Growth Plan|IDCW Plan|Direct Growth Plan|Direct IDCW Plan)\s*([\d\-,]+\.\d+)',
        'metric': r'(Sharpe Ratio|Standard Deviation|Beta|Annualised)[\s]+([\d\-,]+\.\d+)',
        'expense': r'(Regular|Direct)\s*([\d,.-]+)',
        'load': r'ENTRY LOA(.*?)\s*EXIT LOAD\s*(.*?)$',
        'aum': r'(Month End|Monthly Average)\s*([\d,.\-]+)',
        'ptr':r'^(Portfolio Turnover|Total Portfolio).*\s*([\d\-,]+\.\d+)',
        # 'manager': r'([A-Za-z\s]+)\s*\(Managing Since\s*([A-Za-z0-9\s]+) and overall experience of ([a-z0-9\s]+)\)',
        'escape': r'[^A-Za-z0-9\s\-\(\).,]+'
    }

    PATTERN_TO_FUNCTION = {
        r"^(date|benchmark|investment|type_of|scheme|multiples|minimum).*":("_extract_str_data", None),
        r"^nav.*":("_extract_generic_data", "nav"),
        # r"^fund_mana.*": self.__extract_manager_data,
        r"^aum.*": ("_extract_generic_data", 'aum'),
        r"^portfolio_turnover_ratio": ("_extract_generic_data", 'ptr'),
        r"^load": ("_extract_load_data", 'load'),
        r"^metrics": ("_extract_generic_data", "metric"),
    }
    
    SELECTKEYS = {
        "date_of_allotment",
        "fund_manager",
        "benchmark_index", 
        "aum", #2 without date 
        "multiples_for_new_investors", #2
        "multiples_for_existing_investors", #2
        "load",
        "metrics"
        
    }

    def __init__(self, paths_config: str):
        super().__init__(paths_config, self.PARAMS)
    
    
    def _extract_manager_data(self, main_key: str, data: list, pattern:str):
        manager_data = " ".join(data)
        manager_data = re.sub(self.REGEX[pattern], "", manager_data).strip()
        final_list = []
        if matches := re.findall(self.REGEX['manager'], manager_data, re.IGNORECASE):
            for match in matches:
                name, since, exp = match
                final_list.append({
                    "name": name.strip(),
                    "designation": "",
                    "managing_since": since.strip(),
                    "experience": exp.strip()
                })
        return {main_key: final_list}

# 4 <>
class Bandhan(Reader,GrandFundData):
    PARAMS = {
        'fund': [[20], r"^Bandhan.*(Fund|Funds|Plan|ETF)$", [13, 24], [-1361884]],
        'clip_bbox': [(0, 80, 200, 812)],
        'line_x': 200.0,
        'data': [[6, 8], [-14475488], 30.0, ['Ubuntu-Bold']],
        'content_size': [30.0, 10.0]
    }

    REGEX = {
        'ter': r'(Regular|Direct)[\s]+([\d]+(?:\.\d+)?|NA|Nil)',
        'nav': r'(Regular Plan Growth|Regular Plan IDCW|Direct Plan Growth|Direct Plan IDCW)[\s]+([\d]+(?:\.\d+)?|NA|Nil)',
        'metric': r'(Beta|R Squared|Standard Deviation|Sharpe\*|Modified Duration|Average Maturity|Macaulay Duration|Yield to Maturity)[\s]+([\d]+(?:\.\d+)?|NA|Nil)',
        'ptr':  r'(Equity|Aggregate|Tracking Error.*)[\s]+([\d]+(?:\.\d+)?|NA|Nil)',
        'escape': r"[^a-zA-Z0-9.,\s]+|\bAnnualized\b"
    }

    PATTERN_TO_FUNCTION = {
        r"^(category|scheme_launch|benchmark|month|about|investment|sip|option|minimum_inv|exit_load|inception_date).*": ("_extract_str_data", None),
        r"^nav.*": ("_extract_generic_data", "nav"),
        r"^fund_mana.*": ("_extract_str_data", None),
        r"^portfolio.*": ("_extract_generic_data", "ptr"),
        r"^metrics.*": ("_extract_generic_data", "metric"),
        r"^total.*": ("_extract_generic_data", "ter"),
    }
    
    SELECTKEYS = [
        "inception_date",
        "fund_manager",
        "metrics",
        "benchmark_index",
        "minimum_investment_amount",
        "exit_load",
        "monthly_avg_aum",
        "month_end_aum"
    ]

    def __init__(self, paths_config: str):
        super().__init__(paths_config, self.PARAMS)

# 5 <>
class Helios(Reader,GrandFundData):
    
    PARAMS = {
        'fund': [[20], r'^Helios.*Fund$',[16,24],[-1]],
        'clip_box': [(0,5,245,812)],
        'line_x': 245.0,
        'data': [[7,10], [-1,-2545112], 30.0, ['Poppins-SemiBold']],
        'content_size':[30.0,10.0]
    }
    REGEX = {
        'nav': r'(Regular Plan\s?-\s?Growth Option|Regular Plan\s?-\s?IDCW Option|Direct Plan\s?-\s?Growth Option|Direct Plan\s?-\s?IDCW Option)\s*([\d,\-]+(?:\.\d+)?|NA|Nil)',
        'metric':r'(Sharpe Ratio|Standard Deviation|Beta|Annualised|Average Maturity|Modi?f?ied Duration|Macaulay Duration|Yield to Maturity)\s*([\d\-,.]+\s*\w*?)',
        'ter': r'(Regular Plan|Direct Plan)\s*([\d\-,]+(?:\.\d+)?|NA|Nil)',
        'scheme': ["Scheme Category","Benchmark","Plans and Options","Inception Date","Minimum Investment Amount","Additional Investment Amount","Fund Manager","Entry Load","Exit Load","Face Value per Unit","EOL"],
        'aum': r'(Monthly Avg AUM|Month End AUM)\s*([\d,.\-]+)',
        'ptr':r'(Equity Turnover|Total Turnover)\s*([\d,.\-]+)',
        'manager': r'(?:Mr\.?|Ms\.?|Mrs\.?)?\s*([\w\s]+)(?:\([^)]+\))?\s*\(Since ([^)]+)  Overall (\d+ years)',
        'escape': r'[^A-Za-z0-9\s\-\(\).,]+|\(Annualised\)'
    }

    PATTERN_TO_FUNCTION = {
        r"^investment.*":("_extract_str_data", None),
        r"^total.*": ("_extract_generic_data", 'ter'),
        r"^aum.*":("_extract_generic_data", 'aum'),
        r"^nav.*":("_extract_generic_data", "nav"),
        r"^portfolio$":("_extract_scheme_data", "scheme"),
        r"^portfolio_turnover_ratio.*":("_extract_generic_data", 'ptr'),
        r"^metric": ("_extract_generic_data", 'metric')
        
        #secondary
    }
    
    SECONDARY_PATTERN_TO_FUNCTION ={
        r'^portfolio.fund_manager': ('_extract_manager_data','manager'),
        # r'.*(minimum_investment_amount|additional_investment_amount)$':('_extract_min_data','min_add')
    }

    def __init__(self, paths_config: str):
        super().__init__(paths_config, self.PARAMS)
        
    def _extract_manager_data(self, main_key:str, data, pattern:str):
        manager_data = re.sub(self.REGEX['escape'],"", data).strip()
        final_list = []
        if matches:= re.findall(self.REGEX[pattern],manager_data,re.IGNORECASE):
            for match in matches:
                name,since,exp = match
                final_list.append({
                    "name": name.strip(),
                    "designation":"",
                    "managing_since": since.strip(),
                    "experince": exp.strip()
                })
        
        return {main_key: final_list}
# 6  <>
class Edelweiss(Reader,GrandFundData):
    
    PARAMS = {
        'fund': [[20], r'^(Edelweiss|Bharat)',[12,20],[-16298334]],
        'clip_box': [(0,5,410,812)],
        'line_x': 410.0,
        'data': [[5,9], [-16298334,-6204255], 30.0, ['Roboto-Bold']],
        'content_size':[30.0,10.0]
    }
    
    REGEX = {
        'nav': r'(.+?)\s*(\d+\.\d+)', 
        'metric': r'(Sharpe Ratio|Standard Deviation|Beta|Annualised)\s*([\d\-,]+\.\d+)',
        'ter':r'(Regular Plan|Direct Plan)\s*([\d.,]+)',
        'date': r'.*(\d.+[a-zA-Z]{3}\d{2})$',
        'aum': r'Rs\.\s*([\d,]+\.\d+).*Rs\.\s*([\d,]+\.\d+).*',
        'manager': r"(?:Mr\.|Ms\.)\s*([A-Za-z\s]+)\s*(\d{1,2}\s*years)\s*(.*)",
        'escape': r'[^A-Za-z0-9\s\-\(\).,]+'
    }

    PATTERN_TO_FUNCTION = {
        r"^(minimum|additional|benchmark|exit).*": ("_extract_str_data", None),
        r"^nav.*": ("_extract_generic_data", "nav"),
        r"^aum.*":("_extract_aum_data", 'aum'),
        r"^total.*": ("_extract_generic_data", 'ter'),
        r"^fund.*": ("_extract_manager_data", 'manager'),
        r'.*\d{1,2}[a-zA-Z]{3,4}\d{2,4}$':("_extract_date_data", 'date')
    }
    
    SELECTKEYS = [
        "inception_date",
        "fund_manager",
        "benchmark_index",
        "aum",
        "minimum_investment_amount",
        "additional_investment",
        "exit_load",
        "metrics"
    ]

    def __init__(self, paths_config: str):
        super().__init__(paths_config, self.PARAMS)
    
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
                    name,exp,date = match
                    final_list.append({
                        "name":name,
                        "designation":"",
                        "managing_since": date,
                        "experience": exp
                    })
                
        return {main_key:final_list}
    
    def _extract_aum_data(self,main_key:str, data:list,pattern:str):
        final_dict = {}
        for text in data:
            text = re.sub(self.REGEX['escape'],"",text).strip()
            if matches:= re.findall(self.REGEX[pattern],text, re.IGNORECASE):
                for value1, value2 in matches:
                    final_dict['Month End Aum'], final_dict['Monthly Average Aum'] = value1, value2

        return {main_key:final_dict}

# 7
class Invesco(Reader,GrandFundData): #Lupsum issues
    
    PARAMS = {
        'fund': [[20,16], r'^(Invesco|Bharat).*Fund$',[12,20],[-16777216]],
        'clip_bbox': [(0,135,185,812)],
        'line_x': 180.0,
        'data': [[7,9], [-16777216], 30.0, ['Graphik-Semibold']],
        'content_size':[30.0,10.0]
    }
    
    REGEX = {
        # 'nav':r'([\w\s-]+?)\s*(?:\([\w\s%-]*\)|\*)?\s*([\d.]+)%?',
        'metric':r'^(TER - Regular Plan|TER - Direct Plan|Portfolio Turnover Ratio|Fund PB|Fund PE\s*-\s*[A-Z0-9]+|Standard Deviation|Beta|Sharpe Ratio|Tracking Error Regular|Tracking Error Direct|Tracking Error|Average Maturity|Modified Duration|YTM|Macaulay Duration)\s*(?:\([\w\s%-]*\)|\*)?\s*([\d.]+)%?',
        'manager': r'([A-Z][a-zA-Z ]+?) Total Experience (\d+ years) Experience in managing this fund\s+Since ([A-Za-z ]+[0-9, ]+)',
        'escape': r'[^A-Za-z0-9\s\-\(\).,]+|\(cid:3\)',
        'aum': r'([\d,]+\.?\d+) crores',
        'load': r'(.*?)Exit Load(.*)$',
        'min_amt':r'([\d,]+).*?([\d,]+)'
    }
    
    PATTERN_TO_FUNCTION = {
        r"^(date_of|investment|scheme_launch|benchmark).*": ("_extract_str_data", None),
        r"^fund_mana.*": ("_extract_manager_data", 'manager'),
        # r"^nav.*": ("_extract_generic_data", 'nav'),
        r"^load.*": ("_extract_load_data", 'load'),
        # r"^total.*": ("_extract_generic_data", 'ter'),
        # r"^portfolio.*": ("_extract_generic_data", 'ptr'),
        r"^(minimum_investment|additional_purchase).*":('_extract_amt_data','min_amt'),
        r"^(aum|aaum).*": ("_extract_generic_data", 'aum'),
        r"^metric.*": ("_extract_generic_data", 'metric'),
    }
    
    def __init__(self,paths_config:str):
        super().__init__(paths_config,self.PARAMS)
    
    
    def _extract_manager_data(self, main_key:str, data:list,pattern:str):
        manager_data = " ".join(data)
        manager_data = re.sub(self.REGEX['escape'],"",manager_data).strip()
        final_list = []
        matches = re.findall(self.REGEX[pattern], manager_data, re.IGNORECASE)
        for match in matches:
            name,exp,since = match
            final_list.append({
                'name': name.strip(),
                "designation": '',
                'managing_since': since,
                'experience': exp
                })
        
        return {main_key:final_list}

# 8 <>
class MIRAE(Reader,GrandFundData):
    
    PARAMS = {
        'fund': [[20,16],r'^MIRAE.*',[26,36],[-687584]],
        'clip_bbox': [(0,190,270,812)],
        'line_x': 270.0,
        'data': [[8,12], [-14991759], 30.0, ['SpoqaHanSans-Bold']],
        'content_size':[30.0,10.0]
    }
    
    REGEX = {
        'nav': r'(.*?)\s*(\d+\.\d+)', 
        'metric': r'^(Average Maturity|Modified Duration|Macaulay Duration|Annualized Portfolio YTM|Beta|Sharpe Ratio|YTM|Jensons .*|Treynor .*)\s*([\d,.]+)',
        'ter':r'^(Regular Plan|Direct Plan)\s*([\d,.]+)',
        'scheme':["Fund Managers","Allotment Date","Benchmark",'Net AUM',"Tracking Error Value","Exit Load","Plan Available","EOL"],
        'escape': r'[^A-Za-z0-9\s\-\(\).,]+'
    }

    PATTERN_TO_FUNCTION = {
        r"^(scheme).*": ("_extract_scheme_data", 'scheme'),
        r"^investment.*":("_extract_str_data", None),  # Fixed typo
        r"^nav.*":("_extract_generic_data", "nav"),
        r"^metric.*": ("_extract_generic_data", "metric"),
        r"^total.*":("_extract_generic_data", 'ter'),
    }

    def __init__(self, paths_config: str):
        super().__init__(paths_config, self.PARAMS)
     
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

# 9 <>
class ITI(Reader,GrandFundData):
    
    PARAMS = {
        'fund': [[20,16], r'^(ITI|Bharat).*Fund$',[14,24],[-1]],
        'clip_bbox': [(0,105,180,812)],
        'line_x': 180.0,
        'data': [[5,8], [-1688818,-1165277], 30.0, ['Calibri-Bold']],
        'content_size':[30.0,10.0]
    }
    
    REGEX = {
        'aum': r'(AUM|AAUM).*?([\d,\-]+\.?\d+)', 
        'nav': r'(Growth|IDCW)\s*([\-\d,.]+)\s*([\-\d,]+\.?\d+)', 
        'metric':r'(Average PE|Average PB|Standard Deviation|Beta|Sharpe Ratio|Average Maturity|Modified Duration|Yield to Maturity|Macaulay Duration|Portfolio Turnover Ratio)\s*([\-\d,]+\.\d+)',
        'ter':r'^(Regular Plan|Direct Plan)\s*([\d,]+\.?\d+)',
        'manager':r'(?:Mr\.?|Mrs\.?|Ms\.?)\s*([\w\s]+)\(Since ([\w\-\s]+)\)\s*Total Experience\s*(\d+ years)',
        'scheme':["Inception Date","Benchmark","Minimum Application",'Load Structure',"Entry Load","Exit Load","Total Expense Ratio","EOL"],
        'min_amt': r'([\d,]+).*?([\d,]+)',
        'escape': r'[^A-Za-z0-9\-\(\).,\s]+'
    }

    PATTERN_TO_FUNCTION = {
  
        r"^investment.*": ("_extract_str_data", None),
        r"^portfolio_details.*":("_extract_generic_data", "aum"),
        # r"^nav.*": ("_extract_nav_data", 'nav'),
        r"^metrics.*":("_extract_generic_data", "metric"),
        r"^scheme.*": ("_extract_scheme_data", 'scheme'),
        r'^fund_manager': ('_extract_manager_data','manager')
    }
    
    SECONDARY_PATTERN_TO_FUNCTION = {
        r'.*minimum_application$':("_extract_amt_data", "min_amt"),
    }

    def __init__(self, paths_config: str):
        super().__init__(paths_config, self.PARAMS)
     
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
            final_list.append({
                "name":name,
                "designation":"",
                "managing_since": since,
                "experience": exp
            })
                
        return {main_key:final_list}
    
# 10 <>
class JMMF(Reader,GrandFundData):
    PARAMS = {
        'fund': [[20,16], r'^(JM|Bharat).*Fund$',[14,24],[-10987173]],
        'clip_bbox': [(390,105,596,812)],
        'line_x': 390.0,
        'data': [[6,9], [-1], 30.0, ['MyriadPro-BoldCond']],
        'content_size':[30.0,10.0]
    }
    
    REGEX = {
        # 'aum':r'(.+\s*AUM).*?([\d,]+\.?\d+)', 
        # 'nav': r'(.*(?:Option|IDCW)).*?([\d,]+\.?\d+)', 
        # 'metric': r'(.* YTM|Average PE|Average PB|Standard Deviation|Beta|Sharpe Ratio|Average Maturity|Modified Duration|Yield to Maturity|Macaulay Duration|Portfolio Turnover Ratio)\s*([\-\d,]+\.?\d+)',
        # 'ter':r'^(Regular Plan|Direct Plan)\s*([\d,.]+)',
        # 'manager':r'(?:Mr|Mrs|Ms)\s*([\w\s]+)\(Since\s*([\d\w-]+)\)\s*Total experience\s*([0-9]+ years)',
        # 'scheme':["Inception Date","Benchmark","Minimum Application",'Load Structure',"Entry Load","Exit Load","Total Expense Ratio","EOL"],
        # 'escape': r'[^A-Za-z0-9\s\-\(\)\.,]+'
    }

    PATTERN_TO_FUNCTION = {
  
        r"^(investment|exit_load).*": ("_extract_str_data", None),
        # r"^portfolio_details.*":("_extract_generic_data", "aum"),
        # r"^nav.*": ("_extract_nav_data", 'nav'),
        # r"^metrics.*":("_extract_generic_data", "metric"),
        # r"^scheme.*": ("_extract_scheme_data", 'scheme'),
    }

    def __init__(self, paths_config: str):
        super().__init__(paths_config, self.PARAMS)
    
# 11
class Kotak(Reader):
    
    PARAMS = {
        'fund': [[20,16], r'^(Kotak|Bharat).*(Fund|ETF|FTF|FOF)$|^Kotak',[12,20],[-15319437]],
        'clip_bbox': [(0,80,150,812),],
        'line_x': 150.0,
        'data': [[6,8], [-15445130,-14590595], 30.0, ['Frutiger-Bold']],
        'content_size':[30.0,10.0]
        }
    
    def __init__(self, paths_config:str):
        super().__init__(paths_config, self.PARAMS)
        
    #REGEX
    def __return_all_data(self,main_key,data:list):
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
    def match_regex_to_content(self, string: str, data: list):
        pattern_to_function = {
            r"^(sip|aaum|aum|allotment|folio_count|entry|exit|initial|systemic|ideal).*": self.__extract_inv_data,
            r"^total.*": self.__extract_ter_data,
            r"^fund_mana.*": self.__extract_inv_data,
            r"^nav.*": self.__extract_nav_data,
            r"^metrics.*": self.__extract_metric_data,
        }

        for pattern, func in pattern_to_function.items():
            if re.match(pattern, string, re.IGNORECASE):
                return func(string, data)

        return self.__return_all_data(string, data)

# 12 <>
class MahindraManu(Reader,GrandFundData):
    
    PARAMS = {
        'fund': [[20,16], r'',[12,20],[-15319437]],
        'clip_bbox': [(0,65,200,812)],
        'line_x': 200.0,
        'data': [[7,10], [-7392877,-16749906,-7953091,-7767504,-12402502,-945627,], 30.0, ['QuantumRise-Bold','QuantumRise','QuantumRise-Semibold']],
        'content_size':[30.0,10.0]
        }
    
    REGEX = {
        'manager': r'Fund Manager(?:\s*\(.*?\))?\s+(?:Ms\.?|Mrs\.?|Mr\.?)?\s*([\w\s]+?)(?:\s*\(.*?\))?\s+Total Experience\s+([0-9]+(?:\s+years)?)?.*?\(.*?Managing since\s+([^)]+)\)',
        'scheme': ["Date of allotment","Benchmark","Option","Minimum Application Amount","Minimum Additional Purchase Amount","Minimum Repurchase Amount","Minimum Redemption / Switch-outs","Monthly AAUM","Quarterly AAUM","Monthly AUM","Total Expense Ratio","Load Structure","Entry Load","Exit Load","EOL"],
        'nav':r'(IDCW|Growth)\s*([\-\d,.]+)\s*([\-\d,.]+)',
        'aum':r'.*?([\d,]+\.?\d{2}+)$',
        'ter':r'',
        'min_amt': r'([\d,]+).*?([\d,]+)',
        'metrics': r'(Portfolio Turnover Ratio\s*\(.*\)|Standard Deviation|Treynor|Beta|Sharpe|Jensons).*?(-?[\d,\.]+)',
        'escape': r'[^A-Za-z0-9\s\(\),\-\.\/]+'
    }
    PATTERN_TO_FUNCTION = {
        r"^investment.*": ("_extract_str_data", None),
        r"^fund_mana.*": ("_extract_manager_data", "manager"),
        r"^metric.*": ("_extract_generic_data", "metrics"),
        r"^scheme.*": ("_extract_scheme_data", "scheme"),
        r"^nav.*": ("_extract_nav_data", "nav"),
    }
    
    SECONDARY_PATTERN_TO_FUNCTION = {
        r'.*(application_amount|purchase_amount)$':('_extract_amt_data','min_amt'),
        # r'.*(monthly_aaum|quarterly_aaum|monthly_aum)':("_extract_generic_data","aum")
    }
    
    def __init__(self, paths_config:str):
        super().__init__(paths_config, self.PARAMS)
        
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
            final_list.append({
                "name":name.strip(),
                "designation": "",
                "experience": exp,
                "managing_since": since
            })
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

# 13
class MotilalOswal(Reader): #regex of minimum application
    PARAMS = {
        'fund': [[20,16], r'^(Motilal|Oswal).*(Fund|ETF|EOF|FOF|FTF|Path)$',[20,28],[-13616547]],
        'clip_bbox': [(0,65,170,812)],
        'line_x': 170.0,
        'data': [[7,14], [-13948375], 30.0, ['Calibri-Bold']],
        'content_size':[30.0,10.0]
        }
    
    def __init__(self, paths_config:str):
        super().__init__(paths_config, self.PARAMS)   

    #REGEX
    def __return_all_data(self,main_key,data:list):
        return {main_key:data}
    
    def __extract_inv_data(self,main_key:str, data:list):            
        return {main_key: ' '.join(data).strip()}
    
    def __extract_nav_data(self,main_key:str, data:list):
        pattern = r'(.+?Option)\s*([\d.,]+)'
        final_dict = {}
        nav_data = data
        for text in nav_data:
            text = re.sub(r"[\^*\$\*\(\):]", "", text.strip())
            if matches := re.findall(pattern, text, re.IGNORECASE):
                for key, value in matches:
                    final_dict[key] = value
        
        return {main_key: final_dict}
    
    def __extract_metric_data(self,main_key:str, data:list):
        pattern =  r'(Monthly AAUM|Latest AUM|Beta|Portfolio Turnover Ratio|Standard Deviation|Sharpe Ratio|Average Maturity|YTM|Macaulay Duration|Modified Duration)\s*([\d,.]+)'
        final_dict = {}
        metric_data = data
        for text in metric_data:
            text = re.sub(r"[\^*\$\*\(\)]", "", text.strip())
            if matches := re.findall(pattern, text, re.IGNORECASE):
                for key, value in matches:
                    final_dict[key] = value
        
        return {main_key: final_dict}
    
    def __extract_manager_data(self,main_key:str, data:list):
        pattern = r'\b(?:Mr|Mrs|Ms)\s*([A-Za-z]+\s*[A-Za-z]+)\s*Managing this fund since\s*([0-9]+\-[A-Za-z]+\-[0-9]+)\s*He has a rich experience of more than ([0-9]+ years)'
        final_list = []
        manager_data = " ".join(data)
        manager_data = re.sub(r"[\^*\$\*\(\):\.]", "", manager_data.strip())
        if matches := re.findall(pattern, manager_data, re.IGNORECASE):
            for match in matches:
                name,since,exp = match
                final_list.append({
                    "name":name,
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
            text =  re.sub(r"[\^*\$]", "", text.strip())
            if matches:= re.findall(pattern, text, re.IGNORECASE):
                for key, value in matches:
                    final_dict[key] = value
        
        return {main_key:final_dict}
    
    def __extract_load_data(self,main_key:str, data:list):
        
        load_data = " ".join(data)
        load_data = re.sub(r'[\*\#\^,.:]+', "", load_data)
        entry_pattern = r"Entry Load\s*(Not Applicable|Nil)\s*Exit Load"
        exit_pattern = r"Exit Load\s*(.*?)$"  # Capture until next "Entry Load" or end of text

        # Extract matches
        entry_loads = re.findall(entry_pattern, load_data, re.IGNORECASE)
        exit_loads = re.findall(exit_pattern, load_data, re.IGNORECASE | re.DOTALL)

        final_dict = {
            "Entry Load": " ".join(entry_loads),
            "Exit Load": " ".join(exit_loads)
        }
        
        return {main_key:final_dict}
        
         
    #MAPPING
    def match_regex_to_content(self, string: str, data: list):
        pattern_to_function = {
            r"^(investment|benchmark|redemption|inception|category).*": self.__extract_inv_data,
            r"^nav.*": self.__extract_nav_data,
            r"^metric.*": self.__extract_metric_data,
            # r"^minimum.*": self.__extract_min_data,
            r"^fund_manager.*": self.__extract_manager_data,
            r"^total.*": self.__extract_ter_data,
            r"^load.*": self.__extract_load_data,
        }

        for pattern, func in pattern_to_function.items():
            if re.match(pattern, string, re.IGNORECASE):
                return func(string, data)

        return self.__return_all_data(string, data)
# 14
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
# 15 <>
class ThreeSixtyOne(Reader,GrandFundData):
    
    PARAMS = {
        'fund': [[20],r'360 ONE.*(Fund|Path|ETF|FOF|EOF)$',[18,24],[-16777216]], #FUND NAME DETAILS order-> flag, regex_fund_name, font_size, font_color
        'clip_bbox': [(0,5,160,812)],
        'line_x': 160.0,
        'data': [[6,10],[-10791002],30.0,['SpaceGrotesk-SemiBold']], #sizes, color, set_size
        'content_size':[30.0,8.0]
    }
    
    REGEX = {
        'manager':r'(?:Mr|Mrs|Ms)\.?\s*([A-Za-z\s]+)has.*?([0-9\.]+ years)',
        'nav':r'(.+(?:Growth|IDCW))\s*([\d,\-]+\.?\d+)',
        'ter':r'(.+Plan)\s*([\d,\-]+\.?\d+)',
        'aum':r'(.+ AUM)\s*([\d\-,]+\.?\d+)',
        'scheme':['Date of Allotment','BloomBerg Code','Benchmark Index','Plans Offered','Options Offered','Minimum Application','Additional Purchase','Weekly SIP Option','Monthly SIP Option','Quarterly SIP Option','Entry Load','Exit Load','Dematerialization','Portfolio Turnover','EOL'],
        'metrics':r'^(Std\.? Dev|Sharpe Ratio|Portfolio Beta|R Squared|Treynor|Jenson|Residual Maturity|Macaulay Duration|Annualised Portfolio)\s+([\d,\-]+\.?\d+|NA)\s+([\d,\-]+\.?\d+|NA)',
        'escape': r'[^A-Za-z0-9\s\.,\-\(\)]+'
    }
    PATTERN_TO_FUNCTION = {
        r"^investment.*": ("_extract_str_data", None),
        r"^aum.*": ("_extract_generic_data", "aum"),
        r"^nav.*": ("_extract_generic_data", "nav"),
        r"^metrics.*": ("_extract_generic_data", "metrics"),
        r"^scheme.*": ("_extract_scheme_data", "scheme"),
        r"^total.*": ("_extract_generic_data", "ter"),
        r"^(fund_mana|co_fund).*": ("_extract_manager_data", "manager"),
    }
    
    def __init__(self, paths_config:str):
        super().__init__(paths_config, self.PARAMS)
    
    def _extract_manager_data(self, main_key: str, data: list, pattern:str):
        final_list = []
        manager_data = " ".join(data)
        manager_data = re.sub(self.REGEX['escape'], "", manager_data).strip()
        if matches := re.findall(self.REGEX[pattern], manager_data, re.IGNORECASE):
            for match in matches:
                name, exp = match
                final_list.append({
                    "name": name,
                    "designation": "",
                    "managing_since": "",
                    "experience": exp
                })
        return {main_key: final_list}
    
# 16 <>
class BarodaBNP(Reader,GrandFundData): #Lupsum issues
    PARAMS = {
        'fund': [[0],r'^Baroda BNP',[12,18],[-13619152]], #FUND NAME DETAILS order-> flag, regex_fund_name, font_size, font_color
        'clip_bbox': [(0,65,210, 700)],
        'line_x': 210.0,
        'data': [[7,10],[-12566464,],30.0,['Unnamed-T3']], #sizes, color, set_size
        'content_size':[30.0,8.0]
    }
    
    REGEX = {
        'date': r'(^(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec).*)',
        'nav':r'([\w\s-]+?)\s*(?:\([\w\s%-]*\)|\*)?\s*([\d.]+)%?',
        'aum':r'^(Monthly AAUM|AUM).*?([\d,\-]+\.?\d{2}+) Crores',
        'metric':r'^(TER - Regular Plan|TER - Direct Plan|Portfolio Turnover Ratio|Standard Deviation|Beta|Sharpe Ratio|Tracking Error Regular|Tracking Error Direct|Tracking Error|Average Maturity|Modified Duration|YTM|Macaulay Duration)\s*(?:\([\w\s%-]*\)|\*)?\s*([\d.]+)%?',
        'manager': r'(?:Mr\.|Ms\.|Mrs\.)\s([A-Za-z\s]+)\s(\d{2}-[A-Za-z]{3}-\d{2,4})\s(\d+ years)',
        'escape': r'[^A-Za-z0-9\s\-\(\).,]+',
        'load':r"(?:Entry Load)?(.*?)Exit Load\s*(.*)$",
        'lumpsum':r'^(.*?|Minimum Application Amount|Minimum Additional Application Amount)([\d,]+ .*? thereafter)'

    }
    
    PATTERN_TO_FUNCTION = {
        r"^invest.*": ("_extract_str_data", None),
        r"^fund_mana.*": ("_extract_manager_data", 'manager'),
        r"^nav.*": ("_extract_generic_data", 'nav'),
        r"^load": ("_extract_load_data", 'load'),
        r"^metric.*": ("_extract_generic_data", 'metric'),
        r"^date_of_allot":('_extract_aum_data','aum'),
        r"^bench.*": ("_extract_str_data", None),
        # r'^(lumpsum|minimum_application_amount|minimum_additional_application_amount)': ("_extract_lumpsum_data", 'lumpsum'), #|minimum_application_amount|minimum_additional_application_amount
    }
    
    SELECTKEYS = [
        "benchmark_index",
        "aum",
        "fund_manager",
        "load",
        "metrics",
        "lumpsum_details",
        "minimum_application_amount",
        "minimum_additional_application_amount"
    ]
    
    def __init__(self,paths_config:str):
        super().__init__(paths_config,self.PARAMS)
    
    def _extract_manager_data(self, main_key:str, data:list,pattern:str):
        final_list = []
        manager_data = " ".join(data)
        manager_data = re.sub(self.REGEX['escape'],"",manager_data).strip()
        matches = re.findall(self.REGEX[pattern], manager_data, re.IGNORECASE)
        for match in matches:
            name, date, exp = match
            final_list.append({
                'name': name.strip(),
                "designation": '',
                'managing_since': date,
                'experience': exp})

        
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

# 17   
class NAVI(Reader): #complete scheme regex
    PARAMS = {
        'fund': [[20],r'^NAVI.*',[23,33],[-19456]], #FUND NAME DETAILS order-> flag, regex_fund_name, font_size, font_color
        'clip_bbox': [(0,75,320, 700)],
        'line_x': 320.0,
        'data': [[14,20],[-12844976],30.0,['NaviHeadline-Bold']], #sizes, color, set_size
        'content_size':[30.0,9.0]
    }
    
    def __init__(self, paths_config:str):
        super().__init__(paths_config,self.PARAMS)
        
    #FundRegex
    def __return_all_data(self,main_key:str,data:list):
        return{main_key:data}
    def __extract_manager_data(self,main_key:str, data:list):
        manager_data = " ".join(data)
        manager_data = re.sub(r'[\^\-,:\.]+',"", manager_data.strip())
        pattern = r'((?=Mr|Mrs|Ms)\s*[A-Za-z\s]+)\s*(?=a co fund manager is|\s*)\s*managing this fund wef\s*([0-9a-z]+\s*[A-Za-z]+\s*[0-9]+)'
        final_list = []
        if matches:= re.findall(pattern, manager_data, re.IGNORECASE):
            for match in matches:
                name, since = match
                final_list.append({
                    "name":name,
                    "designation":"",
                    "managing_since": since,
                    "experience":""
                })
        
        return {main_key:final_list}
    def __extract_invest_data(self,main_key:str,data:list):
        return {main_key: " ".join(data)}
    def __extract_nav_data(self,main_key:str, data:list):
        nav_data = data
        final_dict = {}
        pattern = r'(.+option)\s*([\d,.]+)'
        for text in nav_data:
            text = text.lower()
            matches = re.findall(pattern, text, re.IGNORECASE)
            for key, value in matches:
                final_dict[key] = value
        return {main_key:final_dict}
    
    def __extract_aum_data(self,main_key:str, data:list):
        aum_data = data
        final_dict = {}
        pattern = r'(AUM|Monthly Average AUM)\s*([\d,.]+)'
        for text in aum_data:
            text = re.sub(r'[\^\-,:\|]+'," ", text.strip())
            if matches := re.findall(pattern, text, re.IGNORECASE):
                for key, value in matches:
                    final_dict[key] = value
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
    
    def match_regex_to_content(self, string: str, data: list):
        pattern_to_function = {
            r"^investment.*": self.__extract_invest_data,
            r"^aum.*": self.__extract_aum_data,
            r"^nav.*": self.__extract_nav_data,
            # r"^metrics.*": self.__extract_metrics_data,
            # r"^scheme.*": self.__extract_scheme_data,
            r"^fund_mana.*": self.__extract_manager_data,
        }

        for pattern, func in pattern_to_function.items():
            if re.match(pattern, string, re.IGNORECASE):
                return func(string, data)

        return self.__return_all_data(string, data)
# 18
class Zerodha(Reader):
    
    PARAMS = {
        'fund': [[20,0],r'^Zerodha.*',[20,30],[-16777216]], #FUND NAME DETAILS order-> flag, regex_fund_name, font_size, font_color
        'clip_bbox': [(0,5,340, 700)],
        'line_x': 340.0,
        'data': [[14,20],[-16777216],30.0,['Unnamed-T3']], #sizes, color, set_size
        'content_size':[30.0,14.0]
    }
    
    def __init__(self,paths_config:str):
        super().__init__(paths_config, self.PARAMS)
        
        
    def __extract_invest_data(self,main_key:str,data:list):
        return {main_key: " ".join(data)}

    def __extract_aum_data(self,main_key:str, data:list):
        aum_data = data
        final_dict = {}
        pattern = r'(Month end AUM|Monthly average AUM|Quarterly average AUM)[\s?:]+([\d]+\.\d+)'
        for text in aum_data:
            text = text.lower()
            matches = re.findall(pattern, text, re.IGNORECASE)
            for key, value in matches:
                final_dict[key] = value
        return {main_key:final_dict}
    
    def __extract_metric_data(self,main_key:str, data:list):
        quant_data = data
        final_dict = {}
        pattern = r'(Portfolio Turnover Ratio|Tracking Error|Average Maturity|Macaulay Duration)[\s?:]+([\d]+\.\d+)'
        for text in quant_data:
            text = text.lower()
            matches = re.findall(pattern, text, re.IGNORECASE)
            for key, value in matches:
                final_dict[key] = value
        return {main_key:final_dict}
    
    def __extract_scheme_data (self, main_key:str,data:list):
        
        mention_start = [
        'Allotment Date',
        'Also manages',
        'Benchmark',
        'Creation Unit Size',
        'Exit Load',
        'Expense Ratio',
        'Launched',
        'Lock-in period',
        'Min. Investment',
        'NAV'
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

    def __return_all_data(self,main_key:str,data:list):
        return{main_key:data}
    
    def __extract_manager_data(self, main_key:str, data:list):
        manager_data = " ".join(data)
        manager_data = re.sub(r'[\^\-,:\.]+',"", manager_data.strip())
        
        final_list = []
        pattern = r'([A-Za-z\s]+)\s*Total Experience\s*([0-9]+ years)\s*Managing this fund since\s*([A-Za-z]+\s*[0-9]+)'
        if matches := re.findall(pattern, manager_data, re.IGNORECASE):
            for match in matches:
                name,exp,since = match
                final_list.append({
                    'name': name,
                    "designation": '',
                    'managing_since': since,
                    'experience': exp
                })
        
        return {main_key:final_list}
    
    #MAPPING FUNCTION
    def match_regex_to_content(self, string: str, data: list, *args):
        pattern_to_function = {
            r"^investment.*": self.__extract_invest_data,
            r"^scheme.*": self.__extract_scheme_data,
            r"^(quant|metrics).*": self.__extract_metric_data,
            r"^fund_manager$": self.__extract_manager_data,
            r"^aum.*": self.__extract_aum_data,
        }

        for pattern, func in pattern_to_function.items():
            if re.match(pattern, string, re.IGNORECASE):
                return func(string, data)

        return self.__return_all_data(string, data) 
# 19
class BankOfIndia(Reader):
    
    PARAMS = {
        'fund': [[20,16], r'^Bank of India',[14,24],[-65784]],
        'clip_bbox': [(0,480,290,812)],
        'line_x': 290.0,
        'data': [[6,9], [-13948375], 30.0, ['Calibri-Bold']],
        'content_size':[30.0,10.0]
        }
    
    def __init__(self,paths_config:str):
        super().__init__(paths_config, self.PARAMS)
        
    #REGEX
    def __return_all_data(self,main_key,data:list):
        return {main_key:data}
    
    def __extract_inv_data(self,main_key:str, data:list):            
        return {main_key: ' '.join(data).strip()}
    
    def __extract_ptr_data(self,main_key:str, data:list):
        ptr_data = data
        pattern = r'^([\d,.]+)'
        for text in ptr_data:
            text = re.sub(r"[\^\#*\$]", "", text.strip())
            matches = re.findall(pattern, text, re.IGNORECASE)
            for value in matches:
                return {main_key:value}
        

    def __extract_nav_data(self,main_key:str, data:list):
        nav_data = data
        final_dict = {}
        pattern = r'(Growth|IDCW)\s*([\d,.]+)'
        for text in nav_data:
            text = re.sub(r"[\^#*\$]", "", text.strip())
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                key, value =  match
                final_dict[key] = value
        return {main_key:final_dict}
    
    def __extract_expense_data(self,main_key:str, data:list):
        expense_data = data
        final_dict = {}
        pattern = r'(Regular Plan|Direct Plan)\s*([\d,.]+)'
        for text in expense_data:
            text = re.sub(r"[\^*,:]", "", text.strip())
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                key, value =  match
                final_dict[key] = value
        return {main_key:final_dict}
    
    def __extract_metric_data(self,main_key:str, data:list):
        expense_data = data
        final_dict = {}
        pattern = r'^(Standard Deviation|Modified Duration|Annualised Yield|Average\s*/\s*Residual Maturity|Macaulay Duration|Tracking Error|Sharpe Ratio|Beta|R Squared|Treynor)\s*(-?[\d,.]+)'
        for text in expense_data:
            text = re.sub(r'[\*,:\^;]+|\(Annualized\)', "", text)
            matches = re.findall(pattern, text, re.IGNORECASE)
            for key,value in matches:
                final_dict[key] = value
        return {main_key:final_dict}
    
    def __extract_load_data(self, main_key:str, data:list):
        load_data = " ".join(data)
        load_data = re.sub(r'[\*,:\^;]+', "", load_data.strip())
        entry_pattern = r"Entry Load\s*(NIL|.*)\s*(?=Exit Load)"
        exit_pattern = r"Exit Load\s*(.*?)(?=\n\s*Entry Load|\Z)"  # Capture until next "Entry Load" or end of text

        # Extract matches
        entry_loads = re.findall(entry_pattern, load_data, re.IGNORECASE)
        exit_loads = re.findall(exit_pattern, load_data, re.IGNORECASE | re.DOTALL)
        exit_loads = [re.sub(r"\s+", " ", load.strip()) for load in exit_loads]
        
        final_dict = {
            "entry_load": "".join(entry_loads),
            "exit_load": "".join(exit_loads)
        }
        return{main_key: final_dict}
    
    
    def __extract_manager_data(self,main_key:str, data:list):
        manager_data = " ".join(data)
        manager_data = re.sub(r'[^0-9A-Za-z\s]+','',manager_data.strip())
        manager_data = re.split(r'(?=(?:Mr|Mrs|Ms)\s)', manager_data)
        
        final_list = []
        
        pattern = r'(?:Mr|Mrs|Ms)\s+(?P<actual_name>[A-Za-z]+\s[A-Za-z]+)(?:\s+wef\s+(?P<wef>[A-Za-z]+\s+\d{1,2}\s+\d{4}))?.*?(?P<experience>\d{1,2}\s+years).*?\bin\s+(?P<designation>.+)'

        for text in manager_data:
            if match:= re.findall(pattern, text, re.IGNORECASE):
                name,since,exp,desig = match[0]
                final_list.append({
                    "name":name,
                    "designation": desig,
                    "experience": exp,
                    "managing_since":since
                })
        
        return {main_key:final_list}
                
    #MAPPING
    def match_regex_to_content(self, string: str, data: list, *args):
        pattern_to_function = {
            r"^investment.*": self.__extract_inv_data,
            r"^metrics": self.__extract_metric_data,
            r'^fund_mana.*': self.__extract_manager_data,
            r"^(benchmark|date|average|latest|minimum|additional)": self.__extract_inv_data,
            r'^portfolio_turnover':self.__extract_ptr_data,
            r'^nav':self.__extract_nav_data,
            r'^expense_ratio': self.__extract_expense_data,
            r'^load': self.__extract_load_data
        }

        for pattern, func in pattern_to_function.items():
            if re.match(pattern, string, re.IGNORECASE):
                return func(string, data)

        return self.__return_all_data(string, data) 
# 20
class Sundaram(Reader):
    PARAMS = {
        'fund': [[4,0], r'^(Sundaram).*(Fund|ETF|EOF|FOF|FTF|Path|Fund*|Fund -)$|^Sundaram',[14,18],[-16625248]],
        'clip_bbox': [(0,5,220,812)],
        'line_x': 220.0,
        'data': [[6,13], [-1], 30.0, ['UniversNextforMORNW02-Cn',]],
        'content_size':[30.0,10.0]
        }
    
    def __init__(self, paths_config:str):
        super().__init__(paths_config, self.PARAMS)
        
        
    #REGEX
    def __return_all_data(self,main_key,data:list):
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
    def match_regex_to_content(self, string: str, data: list):
        pattern_to_function = {
            r"^(exit|entry|investment).*": self.__extract_inv_data,
            r"^nav.*": self.__extract_nav_data,
            r"^metric.*": self.__extract_metric_data,
            r"^scheme.*": self.__extract_scheme_data,
        }

        for pattern, func in pattern_to_function.items():
            if re.match(pattern, string, re.IGNORECASE):
                return func(string, data)

        return self.__return_all_data(string, data)
# 21
class Taurus(Reader):
    PARAMS = {
        'fund': [[4,20], r'^(Taurus).*(Fund|ETF|EOF|FOF|FTF|Path|Fund*)$',[13,24],[-9754846]],
        'clip_bbox': [(0,65,210,812)],
        'line_x': 210.0,
        'data': [[6,12], [-9754846], 30.0, ['Calibri-Bold']],
        'content_size':[30.0,10.0]
        }
    
    def __init__(self, paths_config:str):
        super().__init__(paths_config, self.PARAMS)

    #REGEX
    def __return_all_data(self,main_key,data:list):
        return {main_key:data}
    
    def __extract_inv_data(self,main_key:str, data:list):            
        return {main_key: ' '.join(data).strip()}
    
    def __extract_nav_data(self,main_key:str, data:list):
        nav_data = data
        final_dict = {}
        pattern = r'(Regular Plan|Direct Plan)\s*([\d,.]+)\s*([\d,.]+)'
        for text in nav_data:
            text = re.sub(r"[\^\#*\$]", "", text.strip())
            matches = re.findall(pattern, text, re.IGNORECASE)
            for key,v1,v2 in matches:
                final_dict[f"{key} IDCW"] = v1
                final_dict[f"{key} (G)"] = v2
                
        return {main_key:final_dict}
    
    def __extract_ter_data(self,main_key:str, data:list):
        ter_data = data
        final_dict = {}
        pattern = r'(Regular Plan|Direct Plan)\s*([\d,.]+)'
        for text in ter_data:
            text = re.sub(r"[\^\#:*\$]", "", text.strip())
            matches = re.findall(pattern, text, re.IGNORECASE)
            for key, value in matches:
                final_dict[key] = value
        return {main_key:final_dict}
   
    def __extract_metric_data(self,main_key:str, data:list):
        aum_data = data
        final_dict = {}
        pattern = r'^(Port?olio Turnover|Standard Devia[ti]?on|Modified Duration|Annualised Yield|Macaulay Duration|Tracking Error|Sharpe Ra[ti]?o|Beta|R Squared|Treynor)\s*(-?[\d,.]+)'
        for text in aum_data:
            text = re.sub(r"[\^\#:*\$]", "", text.strip())
            matches = re.findall(pattern, text, re.IGNORECASE)
            for key, value in matches:
                final_dict[key] = value
        return {main_key:final_dict}
    
    def __extract_aum_data(self,main_key:str, data:list):
        aum_data = data
        final_dict = {}
        pattern = r'(.+ AUM)\s*([\d,.]+)'
        for text in aum_data:
            text = re.sub(r"[\^\#:*\$]", "", text.strip())
            matches = re.findall(pattern, text, re.IGNORECASE)
            for key, value in matches:
                final_dict[key] = value
        return {main_key:final_dict}
    
    def __extract_load_data(self, main_key:str, data:list):
        load_data = " ".join(data)
        load_data = re.sub(r'[\*,:\-;]+', "", load_data.strip())
        entry_pattern = r'Entry Load\s*(NIL|.*)\s*Exit Load'
        exit_pattern = r'Exit Load\s*(.*)$'

        # Extract matches
        entry_loads = re.findall(entry_pattern, load_data, re.IGNORECASE)
        exit_loads = re.findall(exit_pattern, load_data, re.IGNORECASE | re.DOTALL)
        exit_loads = [re.sub(r"\s+", " ", load.strip()) for load in exit_loads]
        
        final_dict = {
            "entry_load": "".join(entry_loads),
            "exit_load": "".join(exit_loads)
        }
        return{main_key: final_dict}
    
     #MAPPING
    def match_regex_to_content(self, string: str, data: list):
        pattern_to_function = {
            r"^(minimum_appl|benchmark|date|investment).*": self.__extract_inv_data,
            r"^metric.*": self.__extract_metric_data,
            r"^nav.*": self.__extract_nav_data,
            r"^aum.*": self.__extract_aum_data,
            r"^load.*": self.__extract_load_data,
            r"^total_expense.*": self.__extract_ter_data
        }

        for pattern, func in pattern_to_function.items():
            if re.match(pattern, string, re.IGNORECASE):
                return func(string, data)

        return self.__return_all_data(string, data)
# 22
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
# 23
class Canara(Reader):
    
    PARAMS = {
        'fund': [[16,4], r'^Canara.*',[12,20],[-12371562,-14475488]],
        'clip_bbox': [(0,115,220,812)],
        'line_x': 180.0,
        'data': [[8,11], [-12371562], 30.0, ['Taz-SemiLight']],
        'content_size':[30.0,10.0]
        }
    
    def __init__(self,paths_config:str):
        super().__init__(paths_config,self.PARAMS)
        
    #REGEX
    def __return_all_data(self,main_key,data:list):
        return {main_key:data}
    
    def __extract_inv_data(self,main_key:str, data:list):            
        return {main_key: ' '.join(data)}
    
    def __extract_scheme_data(self, main_key:str, data:list):
        mention_start = [
        "CATEGORY/TYPE",
        "SCHEME OBJECTIVE",
        "Monthend AUM",
        "Monthly AVG AUM",
        "NAV",
        "DATE OF ALLOTMENT",
        "ASSET ALLOCATION",
        "MINIMUM INVESTMENT",
        "PLANS / OPTIONS",
        "ENTRY LOAD",
        "EXIT LOAD",
        "EXPENSE RATIO",
        "BENCHMARK",
        "FUND MANAGER",
        "TOTAL EXPERIENCE",
        "MANAGING THIS FUND"]
        
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
    
    def __extract_metric_data(self, main_key:str, data:list):
        metric_data = data
        pattern = r'^(Yield|Average Maturity|Portfolio Turnover Ratio|Standard Deviation|Residual Maturity|Modified Duration|Annualised Yield|Macaulay Duration|Tracking Error|Sharpe Ratio|Portfolio Beta|Annualised Portfolio YTM|RSquared|Treynor)\s*(-?[\d,.]+)'
        final_data = {}
        
        for text in metric_data:
            text = re.sub(r'[;:\*\-]+',"", text)
            if matches:= re.findall(pattern, text, re.IGNORECASE):
                for key, value in matches:
                    final_data[key] = value

        return {main_key:final_data}
    #MAPPING
    def match_regex_to_content(self, string: str, data: list):
        pattern_to_function = {
            r"^investment.*": self.__extract_inv_data,
            r"^scheme.*": self.__extract_scheme_data,
            r"^metrics.*": self.__extract_metric_data,
        }

        for pattern, func in pattern_to_function.items():
            if re.match(pattern, string, re.IGNORECASE):
                return func(string, data)

        return self.__return_all_data(string, data)
# 24 <>
class WhiteOak(Reader,GrandFundData):
    
    PARAMS = {
        'fund': [[20], r'^(whiteOak).*(Fund|ETF|EOF|FOF|FTF|Path|Fund\*|Plan\*|Duration)$',[16,24],[-13159371]],
        'clip_bbox': [(0, 85, 240, 812)],
        'line_x': 240.0,
        'data': [[7,11], [-65794,-1], 30.0, ['MyriadPro-Bold']],
        'content_size':[30.0,8.0]
        }
    
    REGEX = {
        'manager': r'(?:Mr|Mrs|Ms)\s*([A-Za-z\s]+)\s*(?:\(([A-Za-z\s]+)\))?\s*Managing this Scheme from\s*([\w\s,]+)\s*Total Work Experience\s*([\w\s]+)(?=Mr|Ms|Mrs|$)',
        'nav':r'(Growth)\s*([\d,.]+)\s*(Growth)\s*([\d,.]+)',
        'aum':r'(Monthly Average AUM|Month End AUM)\s*(-?[\d,.]+)',
        'ter':r'(.+? Plan)\s*([\d,.]+)',
        'load':r'Entry Load\s*(.*?)\s*Exit Load\s*(.*?)$',
        'metrics': r'(Portfolio Turnover Ratio|Standard Deviation|Beta|Sharpe|Jensons).*\s(-?[\d,]+\.?\d+)',
        'escape': r'[^A-Za-z0-9\s\(\),\-\.]+'
    }
    PATTERN_TO_FUNCTION = {
        r"^aum.*": ("_extract_generic_data", "aum"),
        r"^expense_ratio.*": ("_extract_generic_data", "ter"),
        r"^(benchmark|scheme_launch|additional|inception|metrics).*": ("_extract_str_data", None),
        # r"^fund_mana.*": ("_extract_manager_data", "manager"),
        # r"^metric.*": ("_extract_generic_data", "metrics"),
        r"^load.*": ("_extract_load_data", "load"),
        r"^nav.*": ("_extract_nav_data", "nav"),
    }
    
    def __init__(self, paths_config:str):
        super().__init__(paths_config, self.PARAMS)
        
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
                final_list.append({
                    "name":name,
                    "designation": desig,
                    "managing_since":since,
                    "experience": exp
                })
        return {main_key:final_list}
# 25
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

# 26 <>
class Nippon(Reader,GrandFundData):
    PARAMS = {
        'fund': [[0,4,20],r'^(Nippon|CPSE).*(?=Plan|Sensex|Fund|Path|ETF|FOF|EOF|Funds|$)',[5,12],[-1]], #FUND NAME DETAILS order-> flag, regex_fund_name, font_size, font_color
        'clip_bbox': [(0,25,220,812)],
        'line_x': 180.0,
        'data': [[6,12],[-16777216],30.0,['HelveticaNeueCondensed-C','HelveticaNeueLTPro-BdCn']], #sizes, color, set_size
        'content_size':[30.0,8.0]
    }
    
    REGEX = {
        'aum': r'(Month End|Monthly Average).*?([\d,]+\.\d{2})',
        'nav': r'(Growth Plan|IDCW Plan|Direct\s+Growth Plan|Direct\s+IDCW Plan|Bonus Option)\s*([\d,.]+)',
        'metric': r'(Standard Deviation|Portfolio Turnover Ratio|Annualised Portfolio YTM|Macaulay Duration|Residual Maturity|Modified Duration|Residual Maturity|Beta|Treynor [A-Za-z]+|Sharpe [A-Za-z]+)\s*([\d,.]+)',
        'ter': r'(Regular|Direct).*\s*([\d,]+\.\d{2})',
        'manager':  r'([A-Za-z\s]+)\s*\(?(.*?)\)?\s*\(Managing Since (.*)\)\s*Total Experience of more than\s*(.* years)',
        'load':r'Entry Load(.*?)\s*Exit Load(.*)$',
        'escape': r"[^a-zA-Z0-9.,\s]+"
    }

    PATTERN_TO_FUNCTION = {
        r"^(investment|type_of|current_investment|date|benchmark|portfolio_turn).*": ("_extract_str_data", None),
        r"^nav.*": ("_extract_generic_data", "nav"),
        r"^fund_mana.*": ("_extract_manager_data", "manager"),
        r"^aum.*": ("_extract_generic_data", "aum"),
        r"^metric.*": ("_extract_generic_data", "metric"),
        r"^total.*": ("_extract_generic_data", "ter"),
        r'load.*': ('_extract_load_data',"load")
    }
    
    def __init__(self, paths_config:str):
        super().__init__(paths_config, self.PARAMS)
    
    #Fund Regex  
    def _extract_manager_data(self,main_key:str,data:list, pattern:str):
        manager_data = data
        final_list = []
        for idx in range(0,len(manager_data),2):
            df = " ".join(manager_data[idx:idx+2])
            if matches := re.findall(self.REGEX[pattern], df, re.IGNORECASE):
                name, desig, managing,exp = matches[0]
                final_list.append({
                    'name':name,
                    "designation":desig,
                    "managing_since": managing,
                    "experience": exp
                })
        return {main_key:final_list}
# 27

class BajajFinServ(Reader):
    
    PARAMS = {
        'fund': [[20],r'Bajaj.*(Fund|Path|ETF|FOF|EOF)$',[14,24],[-16753236]], #FUND NAME DETAILS order-> flag, regex_fund_name, font_size, font_color
        'clip_bbox': [(360,5,612,812)],
        'line_x': 180.0,
        'data': [[6,12],[-1,-15376468],30.0,['Rubik-SemiBold']], #sizes, color, set_size
        'content_size':[30.0,10.0]
    }
    
    def __init__(self,paths_config:str):
        super().__init__(paths_config, self.PARAMS)
    
    #Fund Regex  
    def __return_all_data(self,main_key:str,data:list):
        return{main_key:data}
    def __extract_fund_data(self,main_key:str, data:list):
        return {main_key:data}
    def __extract_invest_data(self,main_key:str,data:list):
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
    def match_regex_to_content(self, string: str, data: list):
        pattern_to_function = {
            r"^(investment|minimum|entry|exit|load|plans|scheme_launch|benchmark).*": self.__extract_invest_data,
            r"^fund_mana.*": self.__extract_fund_data,
            r"^nav.*": self.__extract_nav_data
        }

        for pattern, func in pattern_to_function.items():
            if re.match(pattern, string, re.IGNORECASE):
                return func(string, data)

        return self.__return_all_data(string, data)

#28
class Quantum(Reader):
    
    PARAMS = {
        'fund': [[20,0], r'^(Quantum).*(Fund|ETF|EOF|FOF|FTF|Path|ELSS|Funds)$',[12,20],[-1]],
        'clip_bbox': [(0,95,220,812)],
        'line_x': 180.0,
        'data': [[6,11], [-1], 30.0, ['Prompt-SemiBold',]],
        'content_size':[30.0,8.0]
        }
    
    def __init__(self,paths_config:str):
        super().__init__(paths_config,self.PARAMS)
        
    #Fund Regex  
    def __return_all_data(self,main_key:str,data:list):
        return{main_key:data}
    def __extract_invest_data(self,main_key:str,data:list):
        return {main_key: " ".join(data)}
    
    def __extract_scheme_data(self,main_key:str,data:list):
        mention_start = [
            "Category of Scheme",
            "Investment Objective",
            "Inception Date",
            "Benchmark Index",
            "NAV",
            "AUM",
            "Fund Manager",
            "Entry Load",
            "Exit Load",
            "Total Expense Ratio",
            "Minimum Application Amount",
            "Portfolio Turnover Ratio",
            "Redemption Proceeds",]
            
        mention_end = mention_start[1:] + ["End_of_Data"]

        # Generate regex patterns dynamically
        patterns = [r"({start}\s*)(.+?)({end}|$)".format(start=start, end=end)
            for start, end in zip(mention_start, mention_end)]
        final_dict = {}

        scheme_data = " ".join(data)
        scheme_data = re.sub(r'[\-\*:,;]+',"", scheme_data.strip())
        for pattern in patterns:
            if matches:= re.findall(pattern, scheme_data, re.DOTALL|re.IGNORECASE): #not used ignorecase
                for match in matches:
                    key, value, dummy = match
                    key = key.strip()
                    value = value.strip()
                    final_dict[key] = value
        return {main_key:final_dict}
    
     #MAPPING FUNCTION
    def match_regex_to_content(self, string: str, data: list):
        pattern_to_function = {
            r"^(investment|type_of|current_investment|date|benchmark|portfolio_turn).*": self.__extract_invest_data,
            r'scheme': self.__extract_scheme_data
        }

        for pattern, func in pattern_to_function.items():
            if re.match(pattern, string, re.IGNORECASE):
                return func(string, data)

        return self.__return_all_data(string, data)

#29  
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
        "Co-Fund Managers",
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
