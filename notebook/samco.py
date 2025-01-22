import re
import os
import pandas as pd
import numpy as np


class Samco:
    
    def __init__(self):
        pass
    
    def replace_header_key(self,string:str):
        replace_key = string
        
        if re.match(r'^nav.*', string, re.IGNORECASE):
            replace_key = "nav"
        elif re.match(r"^market", string, re.IGNORECASE):
            replace_key = "dummy"  
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
            replace_key = "dummy" 
        elif re.match(r"^industry", string, re.IGNORECASE):
            replace_key = "dummy"
        else:
            replace_key = "dummy"      
        return replace_key
    
    #REGEX FUNCTIONS
    
    def return_invest_data(key:str,data:list):
        investment_objective = data
        values = " ".join(txt for txt in investment_objective)

        return {key:values}
    
    def return_fund_data(key:str,data:list):
        fund_manager = data
        main_key = key
        strucuted_data = {main_key:[]}
        current_entry = None
        name_pattern = r'^(Ms\.|Mr\.)'
        manage_pattern = r'^\(|\)$'
        date_pattern = r'\b\w+ \d{1,2}, \d{4}\b'
        experience_pattern = r'^Total Experience: (.+)$'

        for data in fund_manager:
            if re.match(name_pattern,data):
                if current_entry:
                    strucuted_data[main_key].append(current_entry)
                current_entry = {
                    'name': data.split(",")[0].strip().lower(),
                    'designation': "".join(data.split(",")[1:]).strip().lower()
                }
                #print(data.split(",")[0],"".join(data.split(",")[1:]))
            elif re.match(manage_pattern,data):
                if "inception" in data.lower():
                    current_entry['managing_since'] = 'inception'
                else:
                    date = re.search(date_pattern, data)
                    current_entry['managing_since'] = date.group() if date != None else None
            elif re.match(experience_pattern,data):
                current_entry['total_experience'] = data.split(":")[1].strip().lower()
                #print(data.split(":")[1])

            
        if current_entry:  # Append the last entry
            strucuted_data[main_key].append(current_entry)
                
        return strucuted_data
    
    def return_quant_data(key:str,data:list):
        qunatitative_data = data
        main_key = key

        strucuted_data = {main_key:{}}
        current_entry = None
        comment = ""

        ratio_pattern = r"\b(ratio|turnover)\b"
        annual_pattern = r'\b(annualised|YTM)\b'
        macaulay_pattern = r"\b(macaulay.*duration)\b"
        residual_pattern = r"\b(residual.*maturity)\b"
        modified_pattern = r"\b(modified.*duration)\b"

        for data in qunatitative_data:
            if re.search(ratio_pattern,data, re.IGNORECASE):
                key = data.split(":")[0].lower().strip()
                value = data.split(":")[1].lower().strip()
            elif re.search(annual_pattern,data, re.IGNORECASE):
                key = data.split(":")[0].lower().strip()
                value = data.split(":")[1].lower().strip()
            elif re.search(macaulay_pattern,data, re.IGNORECASE):
                key = data.split(":")[0].lower().strip()
                value = data.split(":")[1].lower().strip()
            elif re.search(residual_pattern,data, re.IGNORECASE):
                key = data.split(":")[0].lower().strip()
                value = data.split(":")[1].lower().strip()
            elif re.search(modified_pattern,data, re.IGNORECASE):
                key = data.split(":")[0].lower().strip()
                value = data.split(":")[1].lower().strip()
            else:
                comment+= data
            strucuted_data[main_key][key] = value
        
        strucuted_data[main_key]['comment'] = comment

        return strucuted_data
    
    def return_aum_data(key:str,data:list):
    
        aum = data
        main_key = key
        strucuted_data = {main_key:{}}

        pattern = r"\b\d{1,3}(?:,\d{3})*(?:\.\d+)? Crs\b"

        for data in aum:
            if re.search(r'average', data, re.IGNORECASE):
                match = re.search(pattern, data)
                key = 'avg_aum'
            elif re.search(pattern, data):
                match = re.search(pattern, data)
                key = "aum"
            else:
                continue
            
            if match:
                strucuted_data[main_key][key] = match.group()

        return strucuted_data
    
    def return_mar_data(key:str,data:list):
        return {
            key: {}
        }

    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    