import re, os, pprint
from app.pdfParse import Reader
from app.fundRegex import FundRegex
import fitz

class Tata(Reader,GrandFundData): #Lupsum issues
    
    PARAMS = {
        'fund': [[25,20,0,16],r"^tata.*(fund|etf|fof|eof|funds|plan|\))$",[10,20],[-1]], #[flag], regex_fund_name, range(font_size), [font_color]
        'clip_bbox': [(0,50,160,750)],
        'line_x': 160.0,
        'data': [[5,8],[-15570765],30.0,['Swiss721BT-BoldCondensed']], #sizes, color, set_size font_name
        'content_size':[30.0,10.0]
    }
    
    
    REGEX = {
        'nav':r'((?:Regular|Direct|Reg)\s*(?:Growth|IDCW))\s*([\d,.]+)',
        'aum': r'(AUM|Monthly Average AUM)\s*([\d,.]+)',
        'decimal':r'([\d,]+\.\d+)',
        'ter':r'(Regular|Direct)\s*([\d,.]+)',
        'metric':r'(Std. Dev|Sharpe Ratio|Portfolio Beta|R Squared|Treynor|Jenson)\s+([\d.-]+|NA)\s+([\d.-]+|NA)',
        'manager': r'([A-Za-z\s]+)\s*\(Managing Since\s*([A-Za-z0-9\s]+) and overall experience of ([a-z0-9\s]+)\)',
        'load':r'',
        'escape': r'[^A-Za-z0-9\s\-\(\).,]+'
    }
    
    PATTERN_TO_FUNCTION = {
        r"^(date|investment|multiples|benchmark|scheme_launch).*": ("_extract_str_data", None),
        # r"^nav.*":("_extract_generic_data", 'aum'),
        # r"^(aum|monthly_average|portfolio_turnover).*": self.__extract_dec_data,
        # r"^metrics.*": ("_extract_generic_data", 'metric'),
        # r"^load.*": ("_extract_load_data", 'load'),
        # r".*(manager|managers)$": ("_extract_manager_data", 'manager'),
        # r"^expense.*": ("_extract_generic_data", 'ter'),
    }
    
    def __init__(self,paths_config:str):
        super().__init__(paths_config,self.PARAMS)
    
    def _extract_manager_data(self, main_key:str, data:list,pattern:str):
        final_list = []
        manager_data = " ".join(data)
        manager_data = re.sub(self.REGEX['escape'], "", manager_data.strip())
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
    

