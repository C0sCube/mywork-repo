import re, os, pprint
from app.pdfParse import Reader
from app.fundRegex import FundRegex
import fitz

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
        'load':r'Entry Load\s*(.*?)\s*Exit Load\s*(.*)$',
        'metrics': r'(Portfolio Turnover Ratio|Standard Deviation|Beta|Sharpe|Jensons).*\s(-?[\d,]+\.?\d+)',
        'escape': r'[^A-Za-z0-9\s\(\),\-\.]+'
    }
    PATTERN_TO_FUNCTION = {
        # r"^aum.*": ("_extract_generic_data", "aum"),
        # r"^expense_ratio.*": ("_extract_generic_data", "ter"),
        r"^(benchmark|scheme_launch|additional|inception).*": ("_extract_str_data", None),
        r"^fund_mana.*": ("_extract_manager_data", "manager"),
        # r"^metric.*": ("_extract_generic_data", "metrics"),
        # r"^load.*": ("_extract_load_data", "load"),
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
    #something