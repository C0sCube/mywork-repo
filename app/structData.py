import re

class DataStruct:
    
    def __init__(self):
        pass
    
    #first
    final_dic = {
        "metadata": [],
        "records": []
    }
    
    #second
    meta_data = {
        "document_name": "",
        "file_type": "",
        "process_date": ""
    }
    record = {
                "amc_name": "",
                "benchmark_index":[],
                "field_location": [],
                "fund_manager": [],
                "load": [],
                "main_scheme_name": "",
                "metrics": [],
                "min_addl_amt": "",
                "min_addl_multiple":"",
                "min_amt":"",
                "monthly_aaum_date":"",
                "monthly_aaum_value":"",
                "mutual_fund_name": "",
                "scheme_launch_date":""
                
            }
    
    #third  
    fund_manager = {
        "managing_fund_since":"",
        "name": "",
        "qualification": "",
        "total_exp": ""
    }
    load = {
        "type": "",
        "comment": ""
    }   
    metrics= {
        "name":"",
        "value":""
    }    
    field_location = {
      "amc_name": "",
      "benchmark_index": "",
      "count": 0,
      "fund_manager_managing_fund_since": "",
      "fund_manager_name": "",
      "fund_manager_total_exp": "",
      "load_entry": "",
      "load_exit": "",
      "main_scheme_name": "",
      "metrics_beta": "",
      "metrics_port_turnover_ratio": "",
      "metrics_r_squared_ratio": "",
      "metrics_sharpe": "",
      "metrics_std_dev": "",
      "metrics_treynor_ratio": "",
      "min_addl_amt": "",
      "min_addl_amt_multiple": "",
      "min_amt": "",
      "min_amt_multiple": "",
      "monthly_aaum_date": "",
      "monthly_aaum_value": "",
      "mutual_fund_name": "",
      "scheme_launch_date": ""
     }