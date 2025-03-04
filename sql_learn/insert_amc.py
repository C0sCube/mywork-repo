import mysql.connector
import json5


DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "1234",
    "database": "fundhousedb"
}

with open(r"C:\Users\Kaustubh.keny\OneDrive - Cogencis Information Services Ltd\Documents\mywork-repo\data\config\params.json5", "r", encoding="utf-8") as file:
    json_data = json5.load(file)

try:
    conn = mysql.connector.connect(**DB_CONFIG)
    if conn.is_connected():
        print("Connection successful!")
    # conn.close()
    
except mysql.connector.Error as err:
    print(f"Error: {err}")
    
cursor = conn.cursor()


fund_house_mapping = {}

# Insert fund houses
for fund_name in json_data.keys():
    cursor.execute("INSERT INTO fund_houses (name) VALUES (%s) ON DUPLICATE KEY UPDATE id=LAST_INSERT_ID(id)", (fund_name,))
    fund_house_id = cursor.lastrowid
    fund_house_mapping[fund_name] = fund_house_id

    # Insert parameters
    params = json_data[fund_name].get("PARAMS", {})
    cursor.execute("""
        INSERT INTO params (fund_house_id, line_x, method, line_side, max_financial_index_highlight)
        VALUES (%s, %s, %s, %s, %s)
    """, (fund_house_id, params.get("line_x", None), params.get("method", ""), params.get("line_side", ""), params.get("max_financial_index_highlight", 0)))

    # Insert regex patterns
    regex_patterns = json_data[fund_name].get("REGEX", {})
    for key, pattern in regex_patterns.items():
        cursor.execute("""
            INSERT INTO regex_patterns (fund_house_id, key_name, pattern)
            VALUES (%s, %s, %s)
        """, (fund_house_id, key, json5.dumps(pattern) if isinstance(pattern, list) else pattern))

    # Insert pattern-to-function mappings
    pattern_to_function = json_data[fund_name].get("PATTERN_TO_FUNCTION", {})
    for pattern, func_data in pattern_to_function.items():
        cursor.execute("""
            INSERT INTO pattern_to_function (fund_house_id, pattern, function_name, param)
            VALUES (%s, %s, %s, %s)
        """, (fund_house_id, pattern, func_data[0], func_data[1]))

    # Insert secondary pattern mappings
    secondary_pattern = json_data[fund_name].get("SECONDARY_PATTERN_TO_FUNCTION", {})
    for pattern, func_data in secondary_pattern.items():
        cursor.execute("""
            INSERT INTO secondary_pattern_to_function (fund_house_id, pattern, function_name, param)
            VALUES (%s, %s, %s, %s)
        """, (fund_house_id, pattern, func_data[0], func_data[1]))

    # Insert select keys
    select_keys = json_data[fund_name].get("SELECTKEYS", [])
    for key in select_keys:
        cursor.execute("INSERT INTO select_keys (fund_house_id, key_value) VALUES (%s, %s)", (fund_house_id, key))

    # Insert merge keys
    merge_keys = json_data[fund_name].get("MERGEKEYS", {})
    for merge_key, merge_values in merge_keys.items():
        for value in merge_values:
            cursor.execute("INSERT INTO merge_keys (fund_house_id, key_value) VALUES (%s, %s)", (fund_house_id, value))

    # Insert comments
    comments = json_data[fund_name].get("COMMENTS", [])
    for comment in comments:
        cursor.execute("INSERT INTO comments (fund_house_id, comment) VALUES (%s, %s)", (fund_house_id, comment))

# Commit & Close Connection
conn.commit()
cursor.close()
conn.close()

print("Data inserted successfully!")
