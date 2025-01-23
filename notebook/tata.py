import re, os
import pandas as pd
import numpy as np

class Tata:
    
    fund_data = [[25,20,0,16],r"^(samco|tata|canara).*",12,[-1]]
    content_bbox = [(0,50,160,750)]
    
    def __init__(self):
        pass
    
    def return_required_header(self,string: str):
            replace_key = string
            if re.match(r'^nav.*', string, re.IGNORECASE):
                replace_key = "nav"
            elif re.match(r"^market", string, re.IGNORECASE):
                replace_key = "market_capital"  
            elif re.match(r"^assets", string, re.IGNORECASE):
                replace_key = "assets_under_management"
            elif re.match(r"^fund", string, re.IGNORECASE):
                replace_key = "fund_manager" 
            elif re.match(r"^scheme", string, re.IGNORECASE):
                replace_key = "scheme_details" 
            elif re.match(r"^investment", string, re.IGNORECASE):
                replace_key = "investment_objective"
            elif re.match(r"^quanti", string, re.IGNORECASE):
                replace_key = "quantitative_data"
            elif re.match(r"^portfolio", string, re.IGNORECASE):
                replace_key = "portfilio" 
            elif re.match(r"^industry", string, re.IGNORECASE):
                replace_key = "industry_allocation_of_equity"       
            return replace_key
    
    
    #REGEX FUNCTIONS
    def __extract_inv_data(self,key:str, data:list):
        return
    
    def __extract_fund_data(self,key:str, data:list):
        return
    
    def __extract_nav_data(self,key:str, data:list):
        return
    
    def __extract_turn_data(self,key:str, data:list):
        return
    
    def __extract_bench_data(self,key:str, data:list):
        return
    
    def __extract_load_data(self,key:str, data:list):
        return
    
    def __extract_aum_data(self,key:str, data:list):
        return
    
    def __extract_trkerr_data(self,key:str, data:list):
        return
    
    def __extract_volat_data(self,key:str, data:list):
        return
    
    def __extract_dum_data(self,key,data:list):
        return


    def match_regex_to_content(self, string:str, data:list, *args):
        return 