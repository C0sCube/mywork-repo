import re , os
from dateutil import parser

class FundRegex():
    
    HEADER_PATTERNS = {
            r"^(nav|net_asset).*": "nav",
            r"^market": "market_capital",
            r"^(\*aum|assets|fund_aum|aum|fund_size|aum_detail|portfolio_details|fund_size).*": "aum",
            r"^fund_mana.*": "fund_manager",
            r'co-_fund_manager.*': "co_fund_manager",
            r"^(fund_infor|scheme|fund_details|fund_snapshot|fund_feat).*": "scheme_details",
            r"^(investment|about_the|data_as)": "investment_objective",
            r"^(portfolio_statistics|scheme_statistics|portfolio_stats|risk|ratio|maturity|qualitative|quantitative|volatility|debt_quant|other_parameter|performance_attri|performance).*": "metrics",
            r"^expense.*": "expense_ratio",
            r'^load.*': "load",
            r"^(total_exp|weighted_average).*": "total_expense_ratio",
            r'^portfolio_turnover.*': "portfolio_turover_ratio",
            # r'^(date|allotment|inception).*': 'scheme_launch_date',
            r'^benchmark.*': "benchmark_index",
            r'^composition.*': "compositon_by_industry",
            r'^minimum_investment': "minimum_investment"
        }
    
    DECIMAL_PATTERN = r'\b-?(?:\d{1,3}(?:,\d{3})*|\.\d+|\d+\.\d+)\b'
    
    def __init__(self):
        pass
    
    @staticmethod
    def extract_decimals(text:str):
        match = re.search(FundRegex.DECIMAL_PATTERN,text)
        return float(match.group()) if match else "NA"
    
    @staticmethod
    def extract_date(text:str):
        try:
            return parser.parse(text).strftime(r"%y%m%d")
        except Exception as e:
            print(f"\n{e}")
            return text
    @staticmethod
    def header_mapper(text:str):
        
        header_patterns = FundRegex.HEADER_PATTERNS
        for pattern, replacement in header_patterns.items():
            try:
                if re.match(pattern, text, re.IGNORECASE):
                    return replacement
            except Exception as e:
                print(f"\n{e}")         
        return text