import re, os, pprint
from app.pdfParse import Reader
from app.fundRegex import FundRegex
import fitz

class Nippon(Reader):
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
    def _extract_dum_data(self,main_key:str,data:list):
        return{main_key:data}
    
    def _extract_str_data(self,main_key:str,data:list):
        return {main_key: " ".join(data)}
    
    def _extract_generic_data(self, main_key: str, data: list, pattern: str):
        """Extracts data based on the given regex pattern."""
        final_dict = {}
        for text in data:
            text = re.sub(self.REGEX['escape'], "", text.strip())
            matches = re.findall(self.REGEX[pattern], text, re.IGNORECASE)
            for key, value in matches:
                final_dict[key] = value
        return {main_key: final_dict}
    
    def _extract_manager_data(self,main_key:str,data:list):
        manager_data = data
        final_list = []
        for idx in range(0,len(manager_data),2):
            df = " ".join(manager_data[idx:idx+2])
            if matches := re.findall(self.REGEX['manager'], df, re.IGNORECASE):
                name, desig, managing,exp = matches[0]
                final_list.append({
                    'name':name,
                    "designation":desig,
                    "managing_since": managing,
                    "experience": exp
                })
        return {main_key:final_list}
    
    def _extract_load_data(self,main_key:str,data:list):
        load_data = " ".join(data)
        load_data = re.sub(self.REGEX['escape'], "", load_data.strip())
        final_dict = {}
        if match:= re.findall(self.REGEX['load'],load_data.strip(), re.IGNORECASE):
            exit_,entry_ = match[0]
            final_dict['entry_load'] = entry_,
            final_dict['exit_load'] = exit_
        return {main_key:final_dict}

    #MAPPING FUNCTION
    def match_regex_to_content(self, string: str, data: list, *args):
        for pattern, (func_name, regex_key) in self.PATTERN_TO_FUNCTION.items():
            if re.match(pattern, string, re.IGNORECASE):
                func = getattr(self, func_name)  # Dynamically get the function
                if regex_key:
                    return func(string, data, regex_key)
                return func(string, data)

        return self._extract_dum_data(string, data)
# 27

