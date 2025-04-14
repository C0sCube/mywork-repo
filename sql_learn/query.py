import json, os

class Query:
    def __init__(self, conn):
        self.conn = conn
        self.cursor = conn.cursor()

    def get_json_paths(self, root_folder):
        json_paths = []
        for folder_name in os.listdir(root_folder):
            folder_path = os.path.join(root_folder, folder_name)
            if os.path.isfile(folder_path) and folder_path.endswith(".json"):
                json_paths.append(folder_path)
        return json_paths

    def load_all_records(self, json_paths):
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

    def get_or_create_amc(self, amc_name):
        self.cursor.execute("SELECT id FROM amcs WHERE amc_name = %s", (amc_name,))
        result = self.cursor.fetchone()
        if result:
            return result[0]
        self.cursor.execute("INSERT INTO amcs (amc_name) VALUES (%s)", (amc_name,))
        self.conn.commit()
        return self.cursor.lastrowid

    def insert_mutual_fund(self, amc_id, details, curr_time, amc_month, data_from):
        keys = ["amc_id", "entered_time", "amc_for_month", "data_from", "amc_name", "benchmark_index", "main_scheme_name",
                "mutual_fund_name", "monthly_aaum_date", "monthly_aaum_value", "scheme_launch_date",
                "min_addl_amt", "min_addl_amt_multiple", "min_amt", "min_amt_multiple"]
        query = f"INSERT INTO mutual_funds ({', '.join(keys)}) VALUES ({', '.join(['%s'] * len(keys))})"
        values = [amc_id, curr_time, amc_month, data_from] + [details.get(key, "") for key in keys[4:]]
        self.cursor.execute(query, values)
        self.conn.commit()
        return self.cursor.lastrowid

    def insert_fund_managers(self, amc_id, mutual_fund_id, details):
        keys = ["amc_id", "mutual_fund_id", "main_scheme_name", "name", "qualification", "managing_fund_since", "total_exp"]
        query = f"INSERT INTO fund_managers ({', '.join(keys)}) VALUES ({', '.join(['%s'] * len(keys))})"
        if isinstance(details.get("fund_manager"), list):
            for manager in details["fund_manager"]:
                values = [amc_id, mutual_fund_id, details["main_scheme_name"]] + [manager.get(col, "") for col in keys[3:]]
                self.cursor.execute(query, values)
            self.conn.commit()
        else:
            print(f"Error in Managers, {details.get('main_scheme_name', 'N/A')}")

    def insert_load(self, amc_id, mutual_fund_id, details):
        keys = ["amc_id", "mutual_fund_id", "main_scheme_name", "entry_load", "exit_load"]
        if isinstance(details.get("load"), dict):
            query = f"INSERT INTO transformed_loads ({', '.join(keys)}) VALUES ({', '.join(['%s'] * len(keys))})"
            values = [amc_id, mutual_fund_id, details["main_scheme_name"]] + [details["load"].get(col, "") for col in keys[3:]]
            self.cursor.execute(query, values)
            self.conn.commit()
        else:
            print(f"Error in Loads, {details.get('main_scheme_name', 'N/A')}")

    def insert_metrics(self, amc_id, mutual_fund_id, details):
        keys = ['amc_id', 'main_scheme_name', 'mutual_fund_id', "alpha", "arithmetic_mean_ratio", "average_div_yld", 
                "average_pb", "average_pe", "avg_maturity", "beta", "correlation_ratio", "downside_deviation", 
                "information_ratio", "macaulay", "mod_duration", "port_turnover_ratio", "r_squared_ratio", 
                "roe_ratio", "sharpe", "sortino_ratio", "std_dev", "tracking_error", "treynor_ratio", 
                "upside_deviation", "ytm"]
        if isinstance(details.get("metrics"), dict):
            query = f"INSERT INTO transformed_metrics ({', '.join(keys)}) VALUES ({', '.join(['%s'] * len(keys))})"
            values = [amc_id, details["main_scheme_name"], mutual_fund_id] + [details["metrics"].get(col, "") for col in keys[3:]]
            self.cursor.execute(query, values)
            self.conn.commit()
        else:
            print(f"Error in Metrics, {details.get('main_scheme_name', 'N/A')}")
