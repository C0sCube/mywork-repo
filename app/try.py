import re, os, pprint
from app.pdfParse import Reader
from app.fundRegex import FundRegex
import fitz

class Quantum(Reader,GrandFundData): #Lupsum issues
    
    PARAMS = {
        'fund': [[20,0], r'^(Quantum).*(Fund|ETF|EOF|FOF|FTF|Path|ELSS|Funds)$',[12,20],[-1]],
        'clip_bbox': [(0,95,220,812)],
        'line_x': 180.0,
        'data': [[6,11], [-1], 30.0, ['Prompt-SemiBold',]],
        'content_size':[30.0,8.0]
    }
    
    
    REGEX = {
        'nav':r'(Regular Plan|Direct Plan)\s*([\d,.]+)\s*([\d,.]+)',
        'ter':r'(Regular Plan|Direct Plan)\s*([\d,.]+)',
        'aum': r'(.+ AUM)\s*([\d,.]+)',
        'load':r'',
        'scheme':["Category of Scheme","Investment Objective","Inception Date","Benchmark Index","NAV","AUM","Fund Manager", "Key Statistics","Entry Load","Exit Load","Total Expense Ratio","Minimum Application Amount","Portfolio Turnover Ratio","Redemption Proceeds","EOL"],
        'metric':r'^(Port?olio Turnover|Standard Devia[ti]?on|Modified Duration|Annualised Yield|Macaulay Duration|Tracking Error|Sharpe Ra[ti]?o|Beta|R Squared|Treynor)\s*(-?[\d,.]+)',
        'escape': r'[^A-Za-z0-9\s\-\(\).,]+'
    }
    
    PATTERN_TO_FUNCTION = {
        r"^(investment|type_of|current_investment|date|benchmark|portfolio_turn).*": ("_extract_str_data", None),
        r'scheme': ("_extract_scheme_data", 'scheme'),
    }
    
    def __init__(self,paths_config:str):
        super().__init__(paths_config,self.PARAMS)
    

    

