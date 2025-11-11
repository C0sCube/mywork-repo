import traceback
import mysql.connector
from mysql.connector import Error
from app.konstant import DB_CONFIG
from app.logger import get_global_logger


# ------------------ CONNECTION HANDLER ------------------
def establish_connection(db_config=DB_CONFIG):
    """Create and return a MySQL connection."""
    logger = get_global_logger()
    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except Error as e:
        logger.error(f"DB connection failed: {e}")
        logger.debug(traceback.format_exc())
        return None


# ------------------ QUERY HELPERS ------------------
def fetch_existing_record(conn, file_name: str) -> bool:
    """Check if a file_name already exists in the table."""
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT COUNT(*) AS cnt FROM holy_sheet WHERE file_name = %s", (file_name,))
    exists = cur.fetchone()["cnt"] > 0
    cur.close()
    return exists


def update_existing(conn, data: dict):
    """Update the row for an existing file_name."""
    cur = conn.cursor()
    query = """
        UPDATE holy_sheet
        SET start_time=%s, end_time=%s, json_path=%s, status=%s, error=%s
        WHERE file_name=%s
    """
    cur.execute(
        query,
        (
            data.get("start_time"),
            data.get("end_time"),
            data.get("json_path"),
            data.get("status"),
            data.get("error"),
            data.get("file_name"),
        ),
    )
    conn.commit()
    cur.close()


def insert_new(conn, data: dict):
    """Insert a new record for a file_name that doesn't exist."""
    cur = conn.cursor()
    query = """
        INSERT INTO holy_sheet (start_time, end_time, file_name, json_path, status, error)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    cur.execute(
        query,
        (
            data.get("start_time"),
            data.get("end_time"),
            data.get("file_name"),
            data.get("json_path"),
            data.get("status"),
            data.get("error"),
        ),
    )
    conn.commit()
    cur.close()


# ------------------ MAIN HANDLER ------------------
def update_table(data: dict):
    """
    Insert or update a record in holy_sheet.
    Handles connection, check, and upsert logic.
    """
    logger = get_global_logger()
    conn = establish_connection()
    if not conn:
        logger.error("❌ Cannot connect to database.")
        return False

    try:
        file_name = data.get("file_name")
        if not file_name:
            logger.warning("No file_name provided — skipping update.")
            return False

        if fetch_existing_record(conn, file_name):
            update_existing(conn, data)
            logger.info(f"🟢 Updated existing record for {file_name}")
        else:
            insert_new(conn, data)
            logger.info(f"🆕 Inserted new record for {file_name}")
        return True

    except Error as e:
        logger.error(f"❌ Database operation failed: {e}")
        logger.debug(traceback.format_exc())
        if conn.is_connected():
            conn.rollback()
        return False

    finally:
        if conn and conn.is_connected():
            conn.close()
