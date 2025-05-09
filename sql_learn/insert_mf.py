import mysql.connector
import json, os, re
from datetime import datetime
import pandas as pd
import re

fund_names = ["360 ONE Mutual Fund", "Aditya Birla Sun Life Mutual Fund", "Axis Mutual Fund", "Angel One Mutual Fund",
              "BajaJ Finserv Mutual Fund", "Bandhan Mutual Fund", "Bank of India Mutual Fund", 
              "Baroda BNP Paribas Mutual Fund", "Canara Robeco Mutual Fund", "DSP Mutual Fund", 
              "Edelweiss Mutual Fund", "Franklin Templeton Mutual Fund", "Groww Mutual Fund", 
              "HDFC Mutual Fund", "Helios Mutual Fund", "HSBC Mutual Fund", "ICICI Prudential Mutual Fund",
              "Invesco Mutual Fund", "ITI Mutual Fund", "JM Financial Mutual Fund", "Kotak Mahindra Mutual Fund",
              "PGIM India Mutual Fund", "LIC Mutual Fund", "Mahindra Manulife Mutual Fund", "Mirae Asset Mutual Fund", 
              "Motilal Oswal Mutual Fund", "Navi Mutual Fund", "Nippon India Mutual Fund", "NJ Mutual Fund", 
              "Old Bridge Mutual Fund", "PPFAS Mutual Fund", "Quantum Mutual Fund", "Quant Mutual Fund", 
              "Samco Mutual Fund", "SBI Mutual Fund", "Shriram Mutual fund", "Sundaram Mutual Fund", "Tata Mutual Fund", 
              "Taurus Mutual Fund", "Trust Mutual Fund", "Union Mutual Fund", "UTI Mutual Fund", "WhiteOak Mutual Fund", "Zerodha Mutual Fund"]

def get_json_paths(root_folder):
    json_paths = []
    for folder_name in os.listdir(root_folder):
        folder_path = os.path.join(root_folder, folder_name)
        if os.path.isfile(folder_path) and folder_path.endswith(".json"):
            json_paths.append(folder_path)
    return json_paths

def load_all_records(json_paths):
    all_records = {}
    for path in json_paths:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                records = data.get("records", [])
                name = " ".join(records[0].get("value", {}).get("amc_name", "").split(" ")[:2])
                if name not in all_records:
                    all_records[name] = records
                else:
                    name += " 2"
                    all_records[name] = records
        except Exception as e:
            print(f"Error reading {path}: {e}")
    return all_records

def load_all_records_mydata(json_paths):
    all_records = {}
    for path in json_paths:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)  # The whole dict is the data
                sample_scheme = next(iter(data.values()))
                amc_name = sample_scheme.get("amc_name", "").strip()
                name = " ".join(amc_name.split(" ")[:2])
                
                if name not in all_records:
                    all_records[name] = data
                else:
                    name += " 2"
                    all_records[name] = data
        except Exception as e:
            print(f"Error reading {path}: {e}")
    return all_records

def null_if_empty(value):
    if value in ("", None):
        return None
    return value

with open(os.path.join(os.getcwd(),"sql_learn","id_resolver_map.json"), "r", encoding="utf-8") as f:
    id_maps = json.load(f)

def resolve_id(name, id_map_type):
    if not name:
        return None
    name = name.lower()
    for pattern, id_value in id_maps.get(id_map_type, {}).items():
        if re.search(pattern, name):
            return id_value
    return None

def insert_mf_keny_alldata(cursor, details, curr_time, amc_month, monthly_aaum_date):
    amc_id = resolve_id(details.get("amc_name", ""), "amc_id_map")
    fund_id = resolve_id(details.get("mutual_fund_name", ""), "fund_id_map")
    metrics = details.get("metrics", {})
    # load = details.get("load",{})
    
    keys = [
        "amc_id", "amc_name","amc_for_month", "main_scheme_name", "fund_id", "fund_name", 
        "benchmark_index", "min_addl_amt", "min_addl_amt_multiple", "min_amt", "min_amt_multiple", 
        "monthly_aaum_date", "monthly_aaum_value", "scheme_launch_date","entered_time",
        "alpha", "arithmetic_mean_ratio", "average_div_yield", "average_pb", "average_pe", "avg_maturity",
        "beta", "correlation_ratio", "downside_deviation", "information_ratio", "macaulay",
        "mod_duration", "port_turnover_ratio", "r_squared_ratio", "roe_ratio", "sharpe", "sortino_ratio",
        "std_dev", "tracking_error", "treynor_ratio", "upside_deviation", "ytm"]
    
    values = [
        amc_id, #details.get("amc_id", None),
        details.get("amc_name", ""),
        amc_month,
        details.get("main_scheme_name", ""),
        fund_id, #details.get("fund_id", None),
        details.get("mutual_fund_name", ""),
        details.get("benchmark_index", ""),
        details.get("min_addl_amt", ""),
        details.get("min_addl_amt_multiple", ""),
        details.get("min_amt", ""),
        details.get("min_amt_multiple", ""),
        monthly_aaum_date,
        details.get("monthly_aaum_value", ""),
        details.get("scheme_launch_date", ""),
        curr_time #entered_time
    ]+[metrics.get(k, "") for k in keys[15:]]
    values = [null_if_empty(v) for v in values]
    query = f"""
        INSERT INTO mf_keny_alldata ({', '.join(keys)})
        VALUES ({', '.join(['%s'] * len(keys))})
    """
    
    try:
        cursor.execute(query, values)
        return cursor.lastrowid, amc_id, fund_id
    except Exception as e:
        print(f"Error inserting data into mf_keny_alldata: {e}")
        return None, None, None

def insert_mf_keny_fund_managers(cursor, details, curr_time, amc_month):
    keys = [
        "main_scheme_name", "name","managing_fund_since", 
        "qualification", "total_experience","amc_for_month", "entered_time"]
    
    values = [
        # details.get("document_detail_id"),
        details.get("main_scheme_name", ""),
        details.get("name", ""),
        details.get("managing_fund_since", ""),
        details.get("qualification", ""),
        details.get("total_experience", ""),
        amc_month,
        curr_time #entered_time
    ]
    
    values = [null_if_empty(v) for v in values]

    query = f"""
        INSERT INTO mf_keny_fund_manager ({', '.join(keys)})
        VALUES ({', '.join(['%s'] * len(keys))})
    """
    
    try:
        cursor.execute(query, values)
        return cursor.lastrowid
    except Exception as e:
        print(f"Error inserting data into mf_keny_fund_manager: {e}")
        return None


if __name__ == "__main__":
    
    conn = mysql.connector.connect(
        host="172.22.225.155",
        user="cog_mf",
        password="bnYwFChjLAV2Z%9E",
        database="cog_mf",
        port=3306,
        charset='utf8mb4'
    )
    
    # conn = mysql.connector.connect(
    #     host="localhost",   
    #     user="root",            
    #     password="1234", 
    #     database="cog_updated_db",  
    #     port=3306,               
    #     charset="utf8mb4"
    # )

    cursor = conn.cursor()

    base_dir = os.path.join(os.getcwd(), "sql_learn", "json", "mar25latest")
    json_paths = get_json_paths(base_dir)
    combined_records = load_all_records_mydata(json_paths)
    curr_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    amc_month = "MAR25"
    monthly_aaum_date = "20250331|March 2025|31032025"

    for amc_name, schemes in combined_records.items():
        print(f"Doing: {amc_name}")
        for scheme_name, details in schemes.items():
            try:
                mutual_fund_id, amc_id, fund_id = insert_mf_keny_alldata(cursor, details, curr_time, amc_month,monthly_aaum_date)
                if mutual_fund_id:
                    insert_mf_keny_fund_managers(cursor, details, curr_time, amc_month)
                else:
                    print(f"Skipped Insertion for Scheme: {scheme_name}")
            except Exception as e:
                print(f"Error inserting scheme '{scheme_name}' under AMC '{amc_name}': {e}")
        print(f"Done {amc_name}")

    conn.commit()
    cursor.close()
    conn.close()
    print("Working!!")

# def insert_mf_keny_loads(cursor, details, curr_time, amc_month, amc_id):
#     # load_type_id = resolve_id(details.get("load_type", ""), "load_type_map")
    
#     keys = [
#         "amc_id", "MainScheme_ID", "main_scheme_name", 
#         "comment", "type",
#         "amc_for_month", "entered_time"
#     ]
    
#     values = [
#         amc_id, 
#         # details.get("MainScheme_ID", None),  # Assuming this comes from other logic
#         details.get("main_scheme_name", ""),
#         details.get("comment", ""),
#         details.get("type", ""),
#         amc_month, 
#         curr_time
#     ]

#     values = [null_if_empty(v) for v in values]
    
#     query = f"""
#         INSERT INTO mf_keny_loads ({', '.join(keys)})
#         VALUES ({', '.join(['%s'] * len(keys))})
#     """
    
#     try:
#         cursor.execute(query, values)
#         return cursor.lastrowid, amc_id
#     except Exception as e:
#         print(f"Error inserting data into mf_keny_loads: {e}")
#         return None, None
