
# class Canara(Reader,GrandFundData):
    
#     def __init__(self, paths_config: str,fund_name:str):
#         GrandFundData.__init__(self,fund_name) #load from Grand first
#         Reader.__init__(self,paths_config, self.PARAMS) #Pass params
        
    
#     PARAMS = {
#         "fund":{
#             "flag":[4,16],
#             "regex":"'^Canara.*",
#             "size":[12,20],
#             "color":[-12371562,-14475488],
#         },
#         "clip_bbox":[
#             [0,115,220,812],
#             [220,115,400,812],
#         ],
#         "data":{
#             "size":[8,11],
#             "update_size":30.0,
#             "font":['Taz-SemiLight'],
#             "color":[-12371562]
#         },
#         "content_size":[
#             30.0,
#             10.0
#         ],
#         "countmax_header_check": 15,
#         "line_x":180.0,
#         "method":"clip",
#         "line_side":""
#     }
    
#     REGEX = {
#         "metric":"^(Yield|Average Maturity|Portfolio Turnover Ratio|Standard Deviation|Residual Maturity|Modified Duration|Annualised Yield|Macaulay Duration|Tracking Error|Sharpe Ratio|Portfolio Beta|Annualised Portfolio YTM|RSquared|Treynor)\\s*(-?[\\d,.]+)",
#         "scheme":[
#             "CATEGORY/TYPE",
#             "SCHEME OBJECTIVE",
#             "Monthend AUM",
#             "Monthly AVG AUM",
#             "NAV",
#             "DATE OF ALLOTMENT",
#             "ASSET ALLOCATION",
#             "MINIMUM INVESTMENT",
#             "PLANS / OPTIONS",
#             "ENTRY LOAD",
#             "EXIT LOAD",
#             "EXPENSE RATIO",
#             "BENCHMARK",
#             "FUND MANAGER",
#             "TOTAL EXPERIENCE",
#             "MANAGING THIS FUND",
#             "EOL"
#             ],
#         "escape":"[^a-zA-Z0-9.,\\s\\-\\(\\)]+"
#     }
    
#     PATTERN_TO_FUNCTION = {
#         "^investment.*":[
#             "_extract_str_data", None
#         ],
#         "^scheme":[
#             "_extract_scheme_data",'scheme'
#         ]
#     }