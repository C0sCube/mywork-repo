import re, os, pprint
from app.pdfParse import Reader
from app.fundRegex import FundRegex
import fitz

class Invesco(Reader,GrandFundData): #Lupsum issues
    
    PARAMS = {
        'fund': [[20,16], r'^(Invesco|Bharat).*Fund$',[12,20],[-16777216]],
        'clip_bbox': [(0,135,185,812)],
        'line_x': 180.0,
        'data': [[7,9], [-16777216], 30.0, ['Graphik-Semibold']],
        'content_size':[30.0,10.0]
    }
    
    REGEX = {
        'date': r'^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec).*',
        'metric':r'([\w\s-]+?)\s*(?:\([\w\s%-]*\)|\*)?\s*([\d.]+)%?',
        'nav':r'([\w\s-]+?)\s*(?:\([\w\s%-]*\)|\*)?\s*([\d.]+)%?',
        'metrics':r'^(TER - Regular Plan|TER - Direct Plan|Portfolio Turnover Ratio|Standard Deviation|Beta|Sharpe Ratio|Tracking Error Regular|Tracking Error Direct|Tracking Error|Average Maturity|Modified Duration|YTM|Macaulay Duration)\s*(?:\([\w\s%-]*\)|\*)?\s*([\d.]+)%?',
        'manager': r'(Mr\.|Ms\.)\s([A-Za-z\s]+)\s(\d{2}-[A-Za-z]{3}-\d{2,4})\s(\d+)\syears',
        'escape': r'[^A-Za-z0-9\s\-\(\).,]+'
    }
    
    PATTERN_TO_FUNCTION = {
        r"^(load|investment|scheme_launch|benchmark|minimum|additional).*": ("_extract_str_data", None),
        # r"^fund_mana.*": ("_extract_manager_data", 'manager'),
        # r"^nav.*": ("_extract_generic_data", 'nav'),
        # r"^total.*": ("_extract_generic_data", 'ter'),
        # r"^portfolio.*": ("_extract_generic_data", 'ptr'),
        # r"^(aum|aaum).*": ("_extract_generic_data", 'aum'),
        # r"^metric.*": ("_extract_generic_data", 'metric'),
    }
    
    def __init__(self,paths_config:str):
        super().__init__(paths_config,self.PARAMS)
    
    def _extract_manager_data(self, main_key:str, data:list,pattern:str):
        final_list = []
        for text in data:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for title, name, date, exp in matches:
                final_list.append({
                    'name': name.strip(),
                    "designation": '',
                    'managing_since': date,
                    'experience': exp
                })
        
        return {main_key:final_list}
