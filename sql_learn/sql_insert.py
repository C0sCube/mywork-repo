import mysql.connector
import json, os, re
from datetime import datetime

base_dir = os.path.join(os.path.dirname(os.getcwd()) + r"\final_json")


def get_json_paths(root_folder):
    json_paths = {}
    for folder_name in os.listdir(root_folder):
        folder_path = os.path.join(root_folder, folder_name)
        name = re.findall(r".*dump_(.+).json", folder_path, re.IGNORECASE)[0].split("_")[0].title()
        json_paths[name] = folder_path
    return json_paths


def get_or_create_amc(cursor, conn, amc_name):
    cursor.execute("SELECT id FROM amcs WHERE amc_name = %s", (amc_name,))
    result = cursor.fetchone()
    if result:
        return result[0]
    cursor.execute("INSERT INTO amcs (amc_name) VALUES (%s)", (amc_name,))
    conn.commit()
    return cursor.lastrowid


def insert_mutual_fund(cursor, amc_id, details, curr_time, amc_month):
    mutual_fund_keys = ["amc_id", "entered_time", "amc_for_month", "amc_name", "benchmark_index", "main_scheme_name",
                        "mutual_fund_name", "monthly_aaum_date", "monthly_aaum_value", "scheme_launch_date",
                        "min_addl_amt", "min_addl_amt_multiple", "min_amt", "min_amt_multiple"]
    mutual_fund_query = f"INSERT INTO mutual_funds ({', '.join(mutual_fund_keys)}) VALUES ({', '.join(['%s'] * len(mutual_fund_keys))})"
    values = [amc_id, curr_time, amc_month] + [details.get(key, "") for key in mutual_fund_keys[3:]]
    cursor.execute(mutual_fund_query, values)
    return cursor.lastrowid


def insert_fund_managers(cursor, amc_id, mutual_fund_id, details):
    fund_manager_keys = ["amc_id", "mutual_fund_id", "main_scheme_name", "name", "qualification", "managing_fund_since", "total_exp"]
    fund_manager_query = f"INSERT INTO fund_managers ({', '.join(fund_manager_keys)}) VALUES ({', '.join(['%s'] * len(fund_manager_keys))})"
    for manager in details.get("fund_manager", []):
        values = [amc_id, mutual_fund_id, details["main_scheme_name"]] + [manager.get(col, '') for col in fund_manager_keys[3:]]
        cursor.execute(fund_manager_query, values)


def insert_load(cursor, amc_id, mutual_fund_id, details):
    load_keys = ['amc_id', 'mutual_fund_id', 'main_scheme_name', 'entry_load', 'exit_load']
    load_query = f"INSERT INTO transformed_loads ({', '.join(load_keys)}) VALUES ({', '.join(['%s'] * len(load_keys))})"
    values = [amc_id, mutual_fund_id, details["main_scheme_name"]] + [details.get("load", {}).get(col, '') for col in load_keys[3:]]
    cursor.execute(load_query, values)


def insert_metrics(cursor, amc_id, mutual_fund_id, details):
    metric_keys = ['amc_id', 'main_scheme_name', 'mutual_fund_id', "alpha", "arithmetic_mean_ratio", "average_div_yld",
                   "average_pb", "average_pe", "avg_maturity", "beta", "correlation_ratio", "downside_deviation",
                   "information_ratio", "macaulay", "mod_duration", "port_turnover_ratio", "r_squared_ratio",
                   "roe_ratio", "sharpe", "sortino_ratio", "std_dev", "tracking_error", "treynor_ratio", "upside_deviation", "ytm"]
    metric_query = f"INSERT INTO transformed_metrics ({', '.join(metric_keys)}) VALUES ({', '.join(['%s'] * len(metric_keys))})"
    values = [amc_id, details["main_scheme_name"], mutual_fund_id] + [details.get("metrics", {}).get(col, '') for col in metric_keys[3:]]
    cursor.execute(metric_query, values)


if __name__ == "__main__":
# '360', 'Aditya', 'Bajaj', 'Bandhan', 'Bank', 'Baroda', 'Canara', 'Dsp', 'Edelweiss', 'Groww', 'Hdfc', 'Helios', 'Invesco', 'Iti', 'Jm', 'Kotak', 'Lic', 
# 'Mahindra', 'Mirae', 'Navi', 'Nippon', 'Nj', 'Old', 'Pgim', 'Quantum', 'Quant', 'Samco', 'Sbi', 'Sundaram', 'Tata', 'Taurus', 'Trustmf', 'Whiteoak', 'Zerodha'
    json_paths = get_json_paths(base_dir)
    amc_path_name = "360"
    get_data = json_paths[amc_path_name]

    with open(get_data, "r", encoding="utf-8") as f:
        data = json.load(f)

    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="1234",
        database="updated_db"
    )
    cursor = conn.cursor()

    for scheme_name, details in data.items():
        amc_id = get_or_create_amc(cursor, conn, details["amc_name"])
        curr_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        amc_month = "JAN 25"

        mutual_fund_id = insert_mutual_fund(cursor, amc_id, details, curr_time, amc_month)
        insert_fund_managers(cursor, amc_id, mutual_fund_id, details)
        insert_load(cursor, amc_id, mutual_fund_id, details)
        insert_metrics(cursor, amc_id, mutual_fund_id, details)
    
    print(f"Success for {amc_path_name} !!")

    conn.commit()
    cursor.close()
    conn.close()
