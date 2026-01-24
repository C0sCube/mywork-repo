import traceback
import mysql.connector
from mysql.connector import Error
from app.utils import Helper
from app.logger import get_global_logger


table_report = "mf_status_report"

# ------------------ CONNECTION HANDLER ------------------
def establish_connection(db_config=None):
    """Create and return a MySQL connection."""
    logger = get_global_logger()
    try:
        # print("DB CONFIG:", db_config, type(db_config))
        conn = mysql.connector.connect(**db_config)
        logger.info(f"Database - {db_config.get("database","")} is connected.")
        return conn
    except Error as e:
        logger.error(f"Database connection failed: {e}")
        logger.debug(traceback.format_exc())
        return None


# ------------------ QUERY HELPERS ------------------
# def fetch_existing_record(conn, file_name: str) -> bool:
#     """Check if a file_name already exists in the table."""
#     cur = conn.cursor(dictionary=True)
#     cur.execute(f"SELECT COUNT(*) AS cnt FROM {table_report} WHERE file_name = %s", (file_name,))
#     exists = cur.fetchone()["cnt"] > 0
#     cur.close()
#     return exists
def fetch_existing_record(conn, file_name: str, user_name: str) -> bool:
    """Check if a file_name already exists in the table for a given user."""
    cur = conn.cursor(dictionary=True)
    query = f"""
        SELECT COUNT(*) AS cnt
        FROM {table_report}
        WHERE file_name = %s AND uploaded_by = %s
    """
    cur.execute(query, (file_name, user_name))
    exists = cur.fetchone()["cnt"] > 0
    cur.close()
    return exists

def update_existing(conn, data: dict):
    """Update the row for an existing file_name and user."""
    cur = conn.cursor()
    query = f"""
        UPDATE {table_report}
        SET start_time=%s, end_time=%s, json_path=%s, status=%s, error=%s, uploaded_by=%s, to_admin_panel=%s
        WHERE file_name=%s AND uploaded_by=%s
    """
    cur.execute(
        query,
        (
            data.get("start_time"),
            data.get("end_time"),
            data.get("json_path"),
            data.get("status"),
            data.get("error"),
            data.get("uploaded_by", ""),
            data.get("to_admin_panel", 0),
            data.get("file_name"),
            data.get("uploaded_by", ""),
        ),
    )
    conn.commit()
    cur.close()

def insert_new(conn, data: dict):
    """Insert a new record for a file_name that doesn't exist."""
    cur = conn.cursor()
    query = f"""
        INSERT INTO {table_report} (start_time, end_time, file_name, json_path, status, error,created_by,uploaded_by,to_admin_panel)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
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
            data.get("created_by",""),
            data.get("uploaded_by",""),
            data.get("to_admin_panel")
        ),
    )
    conn.commit()
    cur.close()


# ------------------ MAIN HANDLER ------------------
def update_report_table(data: dict, db_config:dict):
    """
    Insert or update a record in holy_sheet.
    Handles connection, check, and upsert logic.
    """
    logger = get_global_logger()
    conn = establish_connection(db_config)
    if not conn:
        logger.error("Cannot connect to database.")
        return False

    try:
        file_name = data.get("file_name")
        user_name = data.get("uploaded_by")
        if not file_name:
            logger.warning("No file_name provided — skipping update.")
            return False

        if fetch_existing_record(conn, file_name,user_name):
            update_existing(conn, data)
            logger.info(f"Updated existing record for {file_name}")
        else:
            insert_new(conn, data)
            logger.info(f"Inserted new record for {file_name}")
        return True

    except Error as e:
        logger.error(f"Database operation failed: {e}")
        logger.debug(traceback.format_exc())
        if conn.is_connected():
            conn.rollback()
        return False

    finally:
        if conn and conn.is_connected():
            conn.close()

 
def json_to_cog_db(json_path, db_config = None):
    
    logger = get_global_logger()
    sp_list= {
        "kim": "mf_processjson_kim",
        "sid": "mf_processjson_sid",
        "fs": "mf_processjson_factsheet"
    },
    
    file_name = json_path.split("\\")[-1]
    json_string = Helper.load_json_as_string(json_path)
    logger.notice(f"File Name: {file_name}, Json String: {json_string[:10]}")    
    flag = False
   

    try:
        sp_name = None
        if "_kim.json" in file_name.lower(): sp_name = sp_list.get("kim","")
        elif "_sid.json" in file_name.lower(): sp_name = sp_list.get("sid","")
        elif "_fs.json" in file_name.lower(): sp_name = sp_list.get("fs","")
 
        # print(sp_name)
        conn = establish_connection(db_config)
        if not conn:
            logger.error("Cannot connect to database.")
            return False

        try:
            cursor = conn.cursor()
            if "_FS.json" in file_name:
                cursor.callproc("mf_update_document_details_FS", [file_name])
                logger.debug("primary sp successfully ran.")
 
            logger.notice(f"SP RUNNING: {sp_name}")
            cursor.callproc(sp_name, [json_string])
            conn.commit()
            logger.debug("secondary sp successfully ran.")
            flag = True
            
        except Error as e:
            conn.rollback() #rollback -> if error
            logger.error(f"{type(e).__name__}: {e}")
            logger.debug(traceback.format_exc())

        finally:
            cursor.close()
            conn.close()
            logger.info("Connection closed.")

    except Exception as e:
        logger.error("Unknown Error while running Either primary or secondary SP.")
        logger.error(f"{type(e).__name__}: {e}")
        logger.debug(traceback.format_exc())
    
    return flag




class JobState:
    UPLOADED = "UPLOADED"
    PARSED = "PARSED"
    PARSE_FAILED = "PARSE_FAILED"
    APPROVED = "APPROVED"
    PUSHED = "PUSHED"
    PUSH_FAILED = "PUSH_FAILED"


ALLOWED_TRANSITIONS = {
    JobState.UPLOADED: {JobState.PARSED, JobState.PARSE_FAILED},
    JobState.PARSED: {JobState.UPLOADED, JobState.APPROVED},
    JobState.PARSE_FAILED: {JobState.UPLOADED},
    JobState.APPROVED: {JobState.PUSHED, JobState.PUSH_FAILED},
    JobState.PUSH_FAILED: {JobState.APPROVED},
}


def transition_job(conn, job_id, from_state, to_state, extra=None):
    if to_state not in ALLOWED_TRANSITIONS.get(from_state, set()):
        raise ValueError(f"Illegal transition {from_state} → {to_state}")

    cur = conn.cursor()
    cur.execute("""
        UPDATE mf_status_report
        SET status=%s,
            end_time = IF(%s IN ('PARSED','PARSE_FAILED','PUSHED','PUSH_FAILED'), NOW(), end_time),
            error = %s
        WHERE id=%s AND status=%s
    """, (
        to_state,
        to_state,
        (extra or {}).get("error"),
        job_id,
        from_state
    ))

    if cur.rowcount != 1:
        raise RuntimeError("Transition failed (stale state or invalid job_id)")

    conn.commit()
    cur.close()

def create_job(data: dict, db_config: dict) -> int:
    """
    Insert a new job with state=UPLOADED.
    Returns job_id.
    """
    conn = establish_connection(db_config)
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO mf_status_report
        (file_name, status, start_time, created_by, uploaded_by)
        VALUES (%s, %s, %s, %s, %s)
    """, (
        data["file_name"],
        JobState.UPLOADED,
        data["start_time"],
        data.get("created_by", ""),
        data.get("uploaded_by", "")
    ))

    job_id = cur.lastrowid
    conn.commit()
    cur.close()
    conn.close()

    return job_id

def fetch_latest_uploaded_job(file_name: str, db_config: dict) -> dict | None:
    """
    Fetch the most recent UPLOADED job for a file.
    """
    conn = establish_connection(db_config)
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT id, status
        FROM mf_status_report
        WHERE file_name=%s AND status=%s
        ORDER BY start_time DESC
        LIMIT 1
    """, (file_name, JobState.UPLOADED))

    row = cur.fetchone()
    cur.close()
    conn.close()

    return row

def transition_job_state(job_id: int, from_state: str, to_state: str, *,
    json_path: str | None = None,
    error: str | None = None,
    db_config: dict
) -> None:
    """
    Perform a guarded job state transition.
    """

    if to_state not in ALLOWED_TRANSITIONS.get(from_state, set()):
        raise ValueError(f"Illegal transition {from_state} → {to_state}")

    conn = establish_connection(db_config)
    cur = conn.cursor()

    cur.execute("""
        UPDATE mf_status_report
        SET status=%s,
            json_path = COALESCE(%s, json_path),
            error = %s,
            end_time = NOW()
        WHERE id=%s AND status=%s
    """, (
        to_state,
        json_path,
        error,
        job_id,
        from_state
    ))

    if cur.rowcount != 1:
        conn.rollback()
        raise RuntimeError(
            f"Job transition failed (job_id={job_id}, expected={from_state})"
        )

    conn.commit()
    cur.close()
    conn.close()
