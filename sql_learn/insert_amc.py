import mysql.connector #type:ignore
import json


# with open(r"C:\Users\rando\OneDrive\Documents\mywork-repo\data\output\dump_360_10_52.json", "r", encoding="utf-8") as file:
#     json_data = json.load(file)

# try:
#     conn = mysql.connector.connect(**DB_CONFIG)
#     if conn.is_connected():
#         print("Python: Connection successful!")

#         cursor = conn.cursor()
#         cursor.execute("SELECT name,salary FROM sample;") #action print
#         result = cursor.fetchall()
#         for row in result:
#             print(row)

#     conn.close()
    
# except mysql.connector.Error as err:
#     print(f"Error: {err}")
    


with open(r"C:\Users\rando\OneDrive\Documents\mywork-repo\data\output\dump_360_22_15.json", "r", encoding="utf-8") as f:
    data = json.load(f)


conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="1234",
    database="company_db"
)
cursor = conn.cursor()

def get_or_create_amc(amc_name):
    cursor.execute("SELECT id FROM amcs WHERE name = %s", (amc_name,))
    result = cursor.fetchone()
    if result:
        return result[0]
    cursor.execute("INSERT INTO amcs (name) VALUES (%s)", (amc_name,))
    conn.commit()
    return cursor.lastrowid


for scheme_name, details in data.items():
    amc_id = get_or_create_amc(details["amc_name"])

    
    cursor.execute("""
        INSERT INTO mutual_funds (amc_id, benchmark_index, main_scheme_name, mutual_fund_name, monthly_aaum_date, monthly_aaum_value, scheme_launch_date)
        VALUES (%s, %s, %s, %s, %s, %s, %s)""", 
        (amc_id, details["benchmark_index"], details["main_scheme_name"], details["mutual_fund_name"],details["monthly_aaum_date"], details["monthly_aaum_value"], details["scheme_launch_date"]))
    mutual_fund_id = cursor.lastrowid

    for manager in details.get("fund_manager", []):
        cursor.execute("""
            INSERT INTO fund_managers (mutual_fund_id,main_scheme_name ,manager_name, designation, managing_fund_since, total_exp)
            VALUES (%s, %s, %s, %s, %s)""", 
            (mutual_fund_id, manager["name"], "", manager.get("managing_fund_since", ""), manager["total_exp"]))

 
    for load_type, load_value in details.get("load", {}).items():
        cursor.execute("""
            INSERT INTO loads (mutual_fund_id, load_type, load_value)
            VALUES (%s, %s, %s)""", 
            (mutual_fund_id, load_type, load_value))

    for metric_name, metric_value in details.get("metrics", {}).items():
        cursor.execute("""
            INSERT INTO metrics (mutual_fund_id, name, value)
            VALUES (%s, %s, %s)""", 
            (mutual_fund_id, metric_name, metric_value))

    min_amt = details.get("min_amt", {})
    if min_amt:
        cursor.execute("""
            INSERT INTO fund_minimum_amounts (mutual_fund_id, amt, thraftr)
            VALUES (%s, %s, %s)""", 
            (mutual_fund_id, min_amt.get("amt", "0"), min_amt.get("thraftr", "0")))

    min_addl_amt = details.get("min_addl_amt", {})
    if min_addl_amt:
        cursor.execute("""
            INSERT INTO fund_additional_amounts (mutual_fund_id, amt, thraftr)
            VALUES (%s, %s, %s)""", 
            (mutual_fund_id, min_addl_amt.get("amt", "0"), min_addl_amt.get("thraftr", "0")))

conn.commit()
cursor.close()
conn.close()

print("Data inserted successfully!")
