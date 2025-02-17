import re , os
from dateutil import parser

class FundRegex():
    

    HEADER_PATTERNS = {
            r"^(nav|net_asset).*": "nav",
            r"^market": "market_capital",
            r'^catagory':'category',
            r"^(\*aum|assets|AUM|monthly_aum|fund_aum|aum|funds_ize|aum_detail|fund_size).*": "aum",
            r"^(fund_mana|fund_and_co|name_of_the).*": "fund_manager",
            r'co-_fund_manager.*': "co_fund_manager",
            r"^(scheme_features|fund_infor|scheme_det|fund_details|fund_snapshot|fund_feat).*": "scheme_details",
            r"^(current_investment|objective|investment|about_the|data_as)": "investment_objective",
            r"^(expense_ratio__quantitative_data|portfolio_parameters|portfolio_statistics|scheme_statistics|portfolio_stats|risk|ratio|maturity|qualitative|quantitative|volatility|debt_quant|other_parameter|performance_attri|quantave_data).*": "metrics",
            r"^expense_ratio$": "expense_ratio",
            r'^(entry__exit|load).*': "load",
            r"^(total_exp|weighted_average|month_end_ter).*": "total_expense_ratio",
            r'^(portfolio_turnover|turn_over|turnover).*': "portfolio_turnover_ratio",
            # r'^(date|allotment|inception).*': 'scheme_launch_date',
            r'^additional_investment.*':'additional_investment',
            r'^(benchmark|amfi_tier_1_bench).*': "benchmark_index",
            r'^composition.*': "compositon_by_industry",
            r'^minimum_investment': "minimum_investment",
            r'^minimum_additional_application_amount': 'minimum_additional_application_amount',
            r'systematic_investment_plan_': "sip",
            r'^exit_load':"exit_load",
            r'plans/option_': 'plans/options',
            r'(minimum_application|minimum_applicaon_amount)': "minimum_application_amount"
        }
    
    
    STOP_WORDS = [
        "folio count data as on 30th november", "2024.", "*", "Note:", "Note :",
        "Mutual Fund investments are subject to market risks, read all scheme related documents carefully.",
        "SCHEME FEATURES", "2.", "Experience", "and Experience", "otherwise specified.",
        "Data as on 31st December, 2024 unles", "Ratio", "DECEMBER 31, 2024",
        "(Last 12 months):", "FOR INVESTORS WHO ARE SEEKING^", "Amount:", "(Date of Allotment):",
        "Rating Profile", "p", "P", "Key Facts", "seeking*:", "This product is suitable for investors who are",
        "product is suitable for them.", "advisers if in doubt about whether the",
        "*Investors should consult their financial", "are seeking*:",
        "This product is suitable for investors who", "(Annualized)", "(1 year)", "Purchase",
        "Amount", "thereafter", ".", ". ", ",", ":", "st", ";", "-", "st ", " ", "th", "th ",
        "rd", "rd ", "nd", "nd ", "", "`", "(Date of Allotment)"
    ]
    
    def __init__(self):
        pass
    
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