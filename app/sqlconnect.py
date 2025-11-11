import traceback
from app.konstant import DB_CONFIG
from app.logger import get_global_logger
import mysql.connector
from mysql.connector import Error

def establish_connection(db_config = DB_CONFIG):
    try:
        logger = get_global_logger()
        conn = mysql.connector.connect(**db_config)
        return conn
      
    except Error as e:
        logger.warning(f"establish_connection error: {type(e).__name__}: {e}")
        logger.debug(traceback.format_exc())
        return None


def update_table(data):
    cur = None # Initialize cur to None
    conn = establish_connection()
    logger = get_global_logger()
    try:
        keys = ["start_time", "end_time", "file_name", "json_path", "status", "error"]
        columns = ", ".join(keys)  # Convert list to comma-separated string

        query = f"""
            INSERT INTO holy_sheet ({columns})
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                status = VALUES(status),
                end_time = VALUES(end_time),
                error = VALUES(error),
                json_path = VALUES(json_path)
        """

        values = [data.get(i, None) for i in keys]

        cur = conn.cursor()
        cur.execute(query, values)
        conn.commit()
        logger.info("✅ Entry updated successfully!")
    except Error as e:
        logger.error(f"❌ Error: {e}")
        # Optionally, roll back the transaction in case of error
        if conn and conn.is_connected():
            conn.rollback()

            
def update_holy_sheet_standard(conn, data):
    pass



