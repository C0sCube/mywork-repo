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
