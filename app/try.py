import re, os, pprint
from app.pdfParse import Reader
from app.fundRegex import FundRegex
import fitz

class MahindraManu(Reader,GrandFundData):
    
    PARAMS = {
        'fund': [[20,16], r'',[12,20],[-15319437]],
        'clip_bbox': [(0,65,200,812)],
        'line_x': 200.0,
        'data': [[7,10], [-7392877,-16749906,-7953091,-7767504,-12402502,-945627,], 30.0, ['QuantumRise-Bold','QuantumRise','QuantumRise-Semibold']],
        'content_size':[30.0,10.0]
        }
    
    REGEX = {
        'manager': r'',
        'scheme':[],
        'nav':r'',
        'aum':r'',
        'ter':r'',
        'metrics': r''
    }
    PATTERN_TO_FUNCTION = {
        r"^investment.*": ("_extract_str_data", None),
        r"^fund_mana.*": ("_extract_manager_data", "manager"),
        r"^metric.*": ("_extract_generic_data", "metrics"),
        r"^scheme.*": ("_extract_scheme_data", "scheme"),
        # r"^nav.*": ("_extract_nav_data", "nav"),
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
