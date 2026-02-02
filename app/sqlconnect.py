import traceback
import mysql.connector #type: ignore
from mysql.connector import Error #type: ignore
from app.utils import Helper
from app.logger import get_global_logger


# =====================================================
# Job State Machine
# =====================================================

class JobState:
    UPLOADED = "UPLOADED"
    PARSED = "PARSED"
    PARSE_FAILED = "PARSE_FAILED"
    APPROVED = "APPROVED"
    PUSHED = "PUSHED"
    PUSH_FAILED = "PUSH_FAILED"
    INVALID_TYPE = "INVALID_TYPE"


ALLOWED_TRANSITIONS = {
    JobState.UPLOADED: {JobState.PARSED, JobState.PARSE_FAILED,JobState.INVALID_TYPE},
    JobState.PARSED: {JobState.PUSHED, JobState.PUSH_FAILED},
    JobState.PARSE_FAILED: {JobState.UPLOADED},
    JobState.PUSH_FAILED: {JobState.PARSED},
    JobState.INVALID_TYPE:{JobState.UPLOADED},
    JobState.PUSHED: {JobState.UPLOADED},   #  REQUIRED for reprocess
}

# REPROCESS_TARGET = {
#     JobState.UPLOADED: JobState.UPLOADED,
#     JobState.PARSED: JobState.UPLOADED,
#     JobState.PARSE_FAILED: JobState.UPLOADED,
#     JobState.PUSH_FAILED: JobState.UPLOADED,
#     JobState.PUSHED: JobState.UPLOADED,
# }

TABLE_REPORT = "mf_status_report"


# =====================================================
# Connection Handler
# =====================================================

def establish_connection(db_config=None):
    """Create and return a MySQL connection."""
    logger = get_global_logger()
    try:
        conn = mysql.connector.connect(**db_config)
        logger.info(f"Database connected: {db_config.get('database','')}")
        # print(db_config)
        return conn
    except Error as e:
        logger.error(f"Database connection failed: {e}")
        logger.debug(traceback.format_exc())
        return None


# =====================================================
# Job Creation
# =====================================================

def create_job(data: dict, db_config: dict) -> int:
    """
    Create a new job in UPLOADED state.
    Returns job_id.
    """
    conn = establish_connection(db_config)
    if not conn:
        raise RuntimeError("DB connection failed")

    cur = conn.cursor()
    cur.execute(
        f"""
        INSERT INTO {TABLE_REPORT}
        (file_name, status, start_time, created_by, uploaded_by)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (
            data["file_name"],
            JobState.UPLOADED,
            data["start_time"],
            data.get("created_by", ""),
            data.get("uploaded_by", "")
        )
    )

    job_id = cur.lastrowid
    conn.commit()
    cur.close()
    conn.close()

    return job_id


# =====================================================
# Job Fetching
# =====================================================

def fetch_job_by_id(job_id: int, db_config: dict) -> dict:
    """Fetch a job row by ID."""
    conn = establish_connection(db_config)
    # print(job_id)
    if not conn:
        raise RuntimeError("DB connection failed")

    cur = conn.cursor(dictionary=True)
    cur.execute(
        f"""
        SELECT id, file_name, status, json_path, error,
               created_by, uploaded_by, start_time, end_time
        FROM {TABLE_REPORT}
        WHERE id = %s
        """,
        (job_id,)
    )
    print(f"{job_id} is called.")

    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        raise ValueError(f"Job {job_id} not found")

    return row


def fetch_latest_uploaded_job(file_name: str, db_config: dict) -> dict | None:
    """Fetch the most recent UPLOADED job for a given file."""
    conn = establish_connection(db_config)
    if not conn:
        return None

    cur = conn.cursor(dictionary=True)
    cur.execute(
        f"""
        SELECT id, status
        FROM {TABLE_REPORT}
        WHERE file_name = %s AND status = %s
        ORDER BY start_time DESC
        LIMIT 1
        """,
        (file_name, JobState.UPLOADED)
    )

    row = cur.fetchone()
    cur.close()
    conn.close()

    return row


# =====================================================
# Job State Transition (SINGLE SOURCE OF TRUTH)
# =====================================================

def transition_job_state(
    job_id: int,
    from_state: str,
    to_state: str,
    *,
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
    if not conn:
        raise RuntimeError("DB connection failed")

    cur = conn.cursor()
    cur.execute(
        f"""
        UPDATE {TABLE_REPORT}
        SET status = %s,
            json_path = COALESCE(%s, json_path),
            error = %s,
            end_time = NOW()
        WHERE id = %s
          AND status = %s
        """,
        (
            to_state,
            json_path,
            error,
            job_id,
            from_state
        )
    )

    if cur.rowcount != 1:
        conn.rollback()
        cur.close()
        conn.close()
        raise RuntimeError(
            f"Job transition failed (job_id={job_id}, expected={from_state})"
        )

    conn.commit()
    cur.close()
    conn.close()


# =====================================================
# Publishing (Admin Panel Push)
# =====================================================

def json_to_cog_db(json_path: str, db_config: dict) -> bool:
    """
    Explicitly push JSON to admin panel via stored procedure.
    MUST be called only from /push_job endpoint.
    """
    logger = get_global_logger()

    sp_map = {
        "kim": "mf_processjson_kim",
        "sid": "mf_processjson_sid",
        "fs": "mf_processjson_factsheet",
    }

    file_name = json_path.split("\\")[-1]
    json_string = Helper.load_json_as_string(json_path)

    sp_name = None
    if "_kim.json" in file_name.lower():
        sp_name = sp_map["kim"]
    elif "_sid.json" in file_name.lower():
        sp_name = sp_map["sid"]
    elif "_fs.json" in file_name.lower():
        sp_name = sp_map["fs"]

    if not sp_name:
        logger.error("No matching SP for JSON file")
        return False

    conn = establish_connection(db_config)
    if not conn:
        return False

    try:
        cursor = conn.cursor()

        if "_fs.json" in file_name.lower():
            cursor.callproc("mf_update_document_details_FS", [file_name])

        cursor.callproc(sp_name, [json_string])
        conn.commit()
        return True

    except Error as e:
        conn.rollback()
        logger.error(f"SP execution failed: {e}")
        logger.debug(traceback.format_exc())
        return False

    finally:
        cursor.close()
        conn.close()

def increment_push_attempts(job_id: int, db_config: dict):
    conn = establish_connection(db_config)
    if not conn:
        raise RuntimeError("DB connection failed")

    cur = conn.cursor()
    cur.execute(
        """
        UPDATE mf_status_report
        SET push_attempts = push_attempts + 1
        WHERE id = %s
        """,
        (job_id,)
    )
    conn.commit()
    cur.close()
    conn.close()


