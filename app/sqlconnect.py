import os
import traceback
from datetime import datetime
import mysql.connector  # type: ignore
from mysql.connector import Error  # type: ignore

from app.logger import get_global_logger
from app.konstant import get_registry, load_json_as_string


# =====================================================
# Job State Machine (CONFIG-DRIVEN)
# =====================================================

def _load_job_config() -> dict:
    registry = get_registry()
    if "job_config" not in registry:
        raise RuntimeError("job_config missing from registry")
    return registry["job_config"]


JOB_CONFIG = _load_job_config()

JOB_STATES = set(JOB_CONFIG.get("states", []))
ALLOWED_TRANSITIONS = {
    k: set(v) for k, v in JOB_CONFIG.get("transitions", {}).items()
}
INITIAL_STATE = JOB_CONFIG.get("initial_state", "UPLOADED")
PUSHABLE_STATES = set(JOB_CONFIG.get("pushable_states", []))


# ---------- CONFIG SANITY CHECKS (FAIL FAST) ----------

if not JOB_STATES:
    raise RuntimeError("job_config.states cannot be empty")

if INITIAL_STATE not in JOB_STATES:
    raise RuntimeError(
        f"Invalid job_config: initial_state '{INITIAL_STATE}' not in states"
    )

unknown_transition_states = set(ALLOWED_TRANSITIONS.keys()) - JOB_STATES
if unknown_transition_states:
    raise RuntimeError(
        f"Invalid job_config: transitions defined for unknown states "
        f"{unknown_transition_states}"
    )


# ---------- Backward-compatible state namespace ----------

class JobState:
    """Dynamic namespace for job states (JobState.PARSED, etc.)"""
    pass


for state in JOB_STATES:
    setattr(JobState, state, state)


TABLE_REPORT = "mf_status_report"


# =====================================================
# DB CONNECTION
# =====================================================

def establish_connection(db_config: dict | None = None):
    logger = get_global_logger()
    try:
        conn = mysql.connector.connect(**db_config)
        logger.info(f"Database connected: {db_config.get('database', '')}")
        return conn
    except Error as e:
        logger.error(f"Database connection failed: {e}")
        logger.debug(traceback.format_exc())
        return None


# =====================================================
# JOB CREATION
# =====================================================

def create_job(data: dict, db_config: dict) -> int:
    """
    Create a new job using configured initial state.
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
            INITIAL_STATE,
            data["start_time"],
            data.get("created_by", ""),
            data.get("uploaded_by", ""),
        )
    )

    job_id = cur.lastrowid
    conn.commit()
    cur.close()
    conn.close()
    return job_id


# =====================================================
# JOB FETCHING
# =====================================================

def fetch_job_by_id(job_id: int, db_config: dict) -> dict:
    conn = establish_connection(db_config)
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
        (job_id,),
    )

    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        raise ValueError(f"Job {job_id} not found")

    return row


def fetch_job_by_name(file_name: str, db_config: dict) -> dict:
    conn = establish_connection(db_config)
    if not conn:
        raise RuntimeError("DB connection failed")

    cur = conn.cursor(dictionary=True)
    cur.execute(
        f"""
        SELECT id, file_name, status, json_path, error,
               created_by, uploaded_by, start_time, end_time
        FROM {TABLE_REPORT}
        WHERE file_name = %s
        """,
        (file_name,),
    )

    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        raise ValueError(f"Job {file_name} not found")

    return row


def fetch_latest_uploaded_job(file_name: str, db_config: dict) -> dict | None:
    conn = establish_connection(db_config)
    if not conn:
        return None

    cur = conn.cursor(dictionary=True)
    cur.execute(
        f"""
        SELECT id, status
        FROM {TABLE_REPORT}
        WHERE file_name = %s
          AND status = %s
        ORDER BY start_time DESC
        LIMIT 1
        """,
        (file_name, JobState.UPLOADED),
    )

    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


# =====================================================
# STATE TRANSITION (SINGLE SOURCE OF TRUTH)
# =====================================================

def transition_job_state(
    job_id: int,
    from_state: str,
    to_state: str,
    *,
    json_path: str | None = None,
    error: str | None = None,
    db_config: dict,
) -> None:
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
        (to_state, json_path, error, job_id, from_state),
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
# STATE HELPERS (FOR WEB / UI LAYERS)
# =====================================================

def is_valid_state(state: str) -> bool:
    return state in JOB_STATES


def can_transition(from_state: str, to_state: str) -> bool:
    return to_state in ALLOWED_TRANSITIONS.get(from_state, set())


def is_pushable_state(state: str) -> bool:
    return state in PUSHABLE_STATES


# =====================================================
# ADMIN PANEL PUBLISHING
# =====================================================

def json_to_cog_db(json_path: str, db_config: dict) -> bool:
    logger = get_global_logger()

    sp_map = {
        "kim": "mf_processjson_kim",
        "sid": "mf_processjson_sid",
        "fs": "mf_processjson_factsheet",
    }

    file_name = os.path.basename(json_path)
    json_string = load_json_as_string(json_path)

    sp_name = None
    lower = file_name.lower()
    if "_kim.json" in lower:
        sp_name = sp_map["kim"]
    elif "_sid.json" in lower:
        sp_name = sp_map["sid"]
    elif "_fs.json" in lower:
        sp_name = sp_map["fs"]

    if not sp_name:
        logger.error(f"No matching SP for JSON file: {file_name}")
        return False

    conn = establish_connection(db_config)
    if not conn:
        return False

    try:
        cur = conn.cursor()

        if "_fs.json" in lower:
            cur.callproc("mf_update_document_details_FS", [file_name])

        cur.callproc(sp_name, [json_string])
        conn.commit()
        return True

    except Error as e:
        conn.rollback()
        logger.error(f"SP execution failed: {e}")
        logger.debug(traceback.format_exc())
        return False

    finally:
        cur.close()
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
        (job_id,),
    )
    conn.commit()
    cur.close()
    conn.close()
