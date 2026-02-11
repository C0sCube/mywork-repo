# =====================================================
# WEB APPLICATION — CSV ↔ JSON ↔ ADMIN PANEL
# =====================================================

import os, sys, json, json5, shutil, pytz, csv, ast
import uuid, shutil
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# ---------------- Project Root ----------------
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(root_dir)

from flask import (
    Flask, render_template, request,
    redirect, url_for, session,
    send_from_directory, jsonify, send_file,
    render_template_string,  abort
)

from ldap3 import Server, Connection, ALL #type:ignore
from werkzeug.utils import secure_filename

from app.utils import Helper
from app.sqlconnect import *
from app.konstant import (
    get_processed_dir, get_failed_dir,
    get_json_dir, get_report_dir
)

# =====================================================
# Flask App Setup
# =====================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    static_folder=os.path.join(BASE_DIR, "static"),
    template_folder=os.path.join(BASE_DIR, "templates"),
)

app.secret_key = "supersecretkey"
app.permanent_session_lifetime = timedelta(days=7)

# =====================================================
# Helpers
# =====================================================

def doc_subdir(filename: str) -> str:
    if filename.endswith("_SID.pdf"):
        return "sid"
    if filename.endswith("_KIM.pdf"):
        return "kim"
    if filename.endswith("_FS.pdf"):
        return "fs"
    return ""

def resolve_source_file(filename: str) -> str | None:
    sub = doc_subdir(filename)

    processed = os.path.join(DIRS["prcs_dir"](sub), filename)
    failed = os.path.join(DIRS["fail_dir"](), filename)

    if os.path.exists(processed):
        return DIRS["prcs_dir"](sub)
    if os.path.exists(failed):
        return DIRS["prcs_dir"](sub)
    return None

def backup_json(json_path, tz):
    ts = datetime.now(tz).strftime("%Y%m%d_%H%M%S")
    base = os.path.basename(json_path)
    backup_dir = os.path.join(os.path.dirname(json_path), "backup")
    os.makedirs(backup_dir, exist_ok=True)
    dst = os.path.join(backup_dir, f"{base}.{ts}.bak")
    shutil.copy(json_path, dst)
    return dst


def init_session_workspace():
    # reuse if already exists
    if session.get("ws_id"):
        return

    ws_id = uuid.uuid4().hex
    session["ws_id"] = ws_id

    base = os.path.join(WEB_DIR, "web_sessions", ws_id)
    for sub in ("conversion", "preview", "staging"):
        os.makedirs(os.path.join(base, sub), exist_ok=True)
        
def cleanup_session_workspace():
    ws_id = session.get("ws_id")
    if not ws_id:
        return

    base = os.path.join(WEB_DIR, "web_sessions", ws_id)
    shutil.rmtree(base, ignore_errors=True)
    session.pop("ws_id", None)


def ws_path(kind):
    return os.path.join(
        WEB_DIR,
        "web_sessions",
        session["ws_id"],
        kind
    )

# =====================================================
# Authentication
# =====================================================

def ldap_authenticate(ldap_conf,username, password):
    server = Server(ldap_conf["server"], get_info=ALL)
    user_dn = f"{username}@{ldap_conf["domain"]}"  # Try UPN format first
    print(f"Trying LDAP bind with DN: {user_dn}")
    try:
        conn = Connection(server, user=user_dn, password=password, auto_bind=True)
        print("LDAP bind successful.")
        return conn.bound
    except Exception as e:
        print(f"LDAP auth failed: {e}")
        return False

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        username = request.form["username"].strip().lower()
        password = request.form["password"]
        remember = "remember" in request.form

        if ldap_authenticate(LDAP_CONFIG,username, password):
        # if True:
            session["logged_in"] = True
            session["user"] = username
            session.permanent = remember
            session["role"] = "admin" if username in ADMIN_USERS else "user"
            
            init_session_workspace()
            
            return redirect(url_for("index"))
        else:
            return render_template("login.html", error="Invalid LDAP credentials.")

    return render_template("login.html")

@app.route("/logout")
def logout():
    
    cleanup_session_workspace()
    session.clear()
    return redirect(url_for("login"))

@app.route("/auth-check")
def auth_check():
    return jsonify(logged_in=bool(session.get("logged_in")))

# def require_admin():
#     if not session.get("logged_in") or session.get("role") != "admin":
#         abort(403)


# =====================================================
# Dashboard
# =====================================================

@app.route('/dashboard')
def dashboard():
    user = session.get("user","")
    role = session.get("role", "user")
    return render_template("dashboard.html", user=user, role=role)

@app.route("/")
def index():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    json_dir = DIRS["json_dir"]()
    files = sorted(os.listdir(json_dir), reverse=True) if os.path.exists(json_dir) else []

    return render_template(
        "dashboard.html",
        json_files=files,
        user=session.get("user", ""),
        role=session.get("role", "user"),
    )


@app.route('/status_data')
def status_data():
    """Return paginated entries from mf_status_report as JSON for dashboard polling."""
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    try:
        # Read query params (defaults: page=1, size=10)
        page = int(request.args.get("page", 1))
        size = int(request.args.get("size", 15))
        offset = (page - 1) * size

        conn = establish_connection(db_config=DB_CONFIG)
        cur = conn.cursor(dictionary=True)

        # Get total count for pagination metadata
        cur.execute("SELECT COUNT(*) AS total FROM mf_status_report")
        total = cur.fetchone()["total"]

        # Fetch paginated rows
        cur.execute("""
            SELECT id, file_name, start_time, end_time, status, json_path, error,
                created_by, uploaded_by, push_attempts
            FROM mf_status_report
            ORDER BY start_time DESC
            LIMIT %s OFFSET %s
        """, (size, offset))
        rows = cur.fetchall()

        cur.close()
        conn.close()

        return {
            "success": True,
            "rows": rows,
            "total": total,
            "page": page,
            "size": size,
            "totalPages": (total + size - 1) // size
        }
    except Exception as e:
        print("status_data error:", e)
        return {"success": False, "rows": []}
    
@app.route("/viewer/pdf/<filename>")
def view_pdf(filename):
    if not session.get("logged_in"):
        return jsonify(success=False, error="Not logged in"), 403

    filename = secure_filename(filename)
    pdf_dir = resolve_source_file(filename)
    if os.path.exists(pdf_dir):
        return send_from_directory(pdf_dir, filename)
    
    return jsonify(success=False, error="PDF not found"), 404

@app.route("/dash_csv", methods=["GET"])
def dash_csv():
    if not session.get("logged_in"):
        return jsonify(success=False, error="Not logged in"), 403

    json_path = request.args.get("path")
    if not json_path:
        return jsonify(success=False, error="Missing ?path"), 400

    if not os.path.exists(json_path):
        return jsonify(success=False, error="JSON not found"), 404

    if json_path.lower().endswith("_fs.json"):
        csv_path = json_to_csv(json_path, output_folder=ws_path("preview"))
    elif json_path.lower().endswith("_sid.json"):
        csv_path = sid_to_csv(json_path, output_folder=ws_path("preview"))
    elif json_path.lower().endswith("_kim.json"):
        csv_path = kim_to_csv(json_path, output_folder=ws_path("preview"))
    else:
        return jsonify(success=False, error="Unsupported JSON type"), 400

    return send_file(
        csv_path,
        as_attachment=True,
        download_name=os.path.basename(csv_path),
        mimetype="text/csv"
    )

@app.route("/apply_csv", methods=["POST"])
def apply_csv():
    if not session.get("logged_in"):
        return jsonify(success=False, error="Not logged in"), 403

    job_id = request.form.get("job_id")
    csv_file = request.files.get("csv")

    if not job_id or not csv_file:
        return jsonify(success=False, error="Missing job_id or csv"), 400

    try:
        job = fetch_job_by_id(int(job_id), DB_CONFIG)
        if not job:
            return jsonify(success=False, error="Job not found"), 404

        json_path = job.get("json_path")
        if not json_path or not os.path.exists(json_path):
            return jsonify(success=False, error="JSON not found"), 404

        # Save CSV into conversion workspace
        csv_name = secure_filename(csv_file.filename)
        csv_path = os.path.join(ws_path("conversion"), csv_name)
        csv_file.save(csv_path)

        # Backup existing JSON
        backup_path = backup_json(json_path, TIME_ZONE)

        # Rebuild JSON from CSV
        new_json = csv_to_fs_json(csv_path)

        with open(json_path, "w", encoding="utf-8") as fh:
            json.dump(new_json, fh, indent=2, ensure_ascii=False)

        return jsonify(
            success=True,
            backup=backup_path,
            json_path=json_path
        )

    except Exception as e:
        return jsonify(success=False, error=str(e)), 500

@app.route("/download_dashboard_json/<filename>")
def download_dashboard_json(filename):
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    filename = secure_filename(filename)
    json_path = os.path.join(DIRS["json_dir"](), filename)

    if not os.path.exists(json_path):
        return "File not found", 404

    return send_file(
        json_path,
        as_attachment=True,
        download_name=filename,
        mimetype="application/json"
    )


# =====================================================
# Upload PDFs (pipeline entry)
# =====================================================

@app.route("/upload", methods=["POST"])
def upload_files():
    if not session.get("logged_in"):
        return jsonify(success=False, error="Not logged in"), 403

    files = request.files.getlist("pdfs")
    os.makedirs(INPUT_DIR, exist_ok=True)
    user = session.get("user", "unknown")
    now = datetime.now(TIME_ZONE).strftime("%Y-%m-%d %H:%M:%S")

    for f in files:
        if not f or not f.filename.lower().endswith(".pdf"):
            continue

        name = secure_filename(f.filename)
        f.save(os.path.join(INPUT_DIR, name))

        create_job(
            {
                "file_name": name,
                "start_time": now,
                "created_by": user,
                "uploaded_by": user,
            },
            DB_CONFIG,
        )

    return jsonify(success=True)

# =====================================================
# Reprocess + SP CALL
# =====================================================

@app.route("/reprocess/<int:job_id>", methods=["POST"])
def reprocess(job_id):
    if not session.get("logged_in"):
        return jsonify(success=False, error="Session expired"), 401
    
    try:

        job = fetch_job_by_id(job_id, DB_CONFIG)
        status = job["status"]

        if not can_transition(status, JobState.UPLOADED):
            return jsonify(success=False, error=f"Cannot reprocess from {status}"), 400

        src = resolve_source_file(job["file_name"])
        # print(f"SOURCE: {src}")
        if not src:
            return jsonify(success=False, error="Source file not found"), 404
        
        file_name = job["file_name"]
        scr_path =  os.path.join(src, file_name)
        dest_path = os.path.join(INPUT_DIR, file_name)
        # print(dest_dir)

        shutil.copy(scr_path, dest_path)

        transition_job_state(
            job_id=job_id,
            from_state=status,
            to_state=JobState.UPLOADED,
            error=None,
            db_config=DB_CONFIG,
        )

        return jsonify(success=True, message=f"{job["file_name"]} reprocessing")

    except Exception as e:
        return jsonify(success=False, message=str(e)), 500

@app.route("/push_job/<int:job_id>", methods=["POST"])
def push_job(job_id):

    if not session.get("logged_in"):
        return jsonify(success=False, error="Not logged in"), 403

    try:
        job = fetch_job_by_id(job_id, DB_CONFIG)
        if not job:
            return jsonify(success=False, error="Job not found"), 404

        status = job["status"]
        json_path = job.get("json_path")

        if not json_path or not os.path.exists(json_path):
            return jsonify(success=False, error="JSON not found"), 404

        if not is_pushable_state(status):
            return jsonify(
                success=False,
                error=f"Job not pushable in state {status}"
            ), 400

        increment_push_attempts(job_id, DB_CONFIG)

        success = json_to_cog_db(json_path, DB_CONFIG)
        next_state = JobState.PUSHED if success else JobState.PUSH_FAILED

        if can_transition(status, next_state):
            transition_job_state(
                job_id=job_id,
                from_state=status,
                to_state=next_state,
                error=None if success else "Admin panel push failed",
                db_config=DB_CONFIG
            )

        return jsonify(success=success)

    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


# =====================================================
# CONFIG - EDITOR
# =====================================================

@app.route('/config-editor')
def config_editor():
    if not session.get("logged_in"):
        return redirect(url_for("login")) 

    user = session.get("user", "").lower()
    if user not in ADMIN_USERS:
        return redirect(url_for("index"))

    return render_template("config_editor.html", user=user) 

@app.route('/list-files/<year>')
def list_files(year):
    year_path = os.path.join(CONFIG_PATH, str(year))
    print(year_path)
    try:
        files = [f for f in os.listdir(year_path) if (f.endswith('.json') or  f.endswith('.json5'))]
        return jsonify({"files": files})
    except Exception as e:
        return jsonify({"files": [], "error": str(e)})
    
@app.route('/load-config', methods=['POST'])
def load_config():
    
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    data = request.get_json()
    year = data.get('year')
    filename = data.get('filename')
    path = os.path.join(CONFIG_PATH, str(year), filename)

    try:
        with open(path, 'r', encoding='utf-8') as f:
            if filename.endswith(".json5"):
                json_data = json5.load(f)   # parse JSON5
            else:
                json_data = json.load(f)    # parse strict JSON
        # pretty print back to client
        return jsonify({"success": True, "data": json_data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/save-config', methods=['POST'])
def save_config():
    data = request.get_json()
    year = data.get('year')
    filename = data.get('filename')
    content = data.get('content')
    path = os.path.join(CONFIG_PATH, str(year), filename)
    try:
        # parse content depending on extension
        if filename.endswith(".json5"):
            parsed = json5.loads(content)
        else:
            parsed = json.loads(content)

        # always save as pretty JSON (indent=2)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(parsed, f, indent=2, ensure_ascii=False)

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
  
@app.route("/backup-config", methods=["POST"])
def backup_config():
    data = request.get_json()
    year = data["year"]
    filename = data["filename"]

    src = os.path.join(CONFIG_PATH, str(year), filename)
    if not os.path.exists(src):
        return jsonify({"success": False, "message": "File not found"})

    backup_dir = os.path.join(CONFIG_PATH, "0001")
    os.makedirs(backup_dir, exist_ok=True)

    ts = datetime.now(TIME_ZONE).strftime("%y%m%d_%H%M")
    ext = ".json" if filename.endswith("json") else ".json5"
    
    backup_name = f"{filename.replace(ext, "")}_{str(year)}bkp_{ts}{ext}"
    dst = os.path.join(backup_dir, backup_name)

    shutil.copy(src, dst)
    return jsonify({"success": True})

@app.route("/create-config", methods=["POST"])
def create_config():
    data = request.get_json()
    year = data["year"]
    filename = data["filename"]

    year_dir = os.path.join(CONFIG_PATH, str(year))
    os.makedirs(year_dir, exist_ok=True)

    file_path = os.path.join(year_dir, filename)
    if os.path.exists(file_path):
        return jsonify({"success": False, "error": "File already exists"})

    with open(file_path, "w", encoding="utf-8") as f:
        f.write("{}")  # start with empty JSON

    return jsonify({"success": True})

@app.route("/delete-config", methods=["POST"])
def delete_config():
        
    data = request.get_json()
    year = data["year"]
    filename = data["filename"]

    file_path = os.path.join(CONFIG_PATH, str(year), filename)
    if not os.path.exists(file_path):
        return jsonify({"success": False, "error": "File not found"})

    os.remove(file_path)
    return jsonify({"success": True})


# =====================================================
# CSV ↔ JSON CONVERSION (WEB OWNED)
# =====================================================
@app.route('/csv-to-json')
def csv_to_json():
    if not session.get("logged_in"):
        return redirect(url_for("login")) 

    user = session.get("user", "").lower()
    return render_template("csv_to_json.html", user=user)

# SID
def sid_to_csv(json_path, output_folder):
    json_path = Path(json_path)
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)

    with open(json_path, "r", encoding="utf-8") as f:
        doc = json.load(f)
    record = doc.get("value", {}) or {}

    csv_path = output_folder / f"{json_path.stem}.csv"

    def write_df(fh, df):
        df.to_csv(fh, index=False)
        fh.write("\n\n")

    with open(csv_path, "w", encoding="utf-8", newline="") as fh:
        kv = []
        for k in sorted(record.keys()):
            if k not in ("fund_manager", "load", "field_location"):
                v = record.get(k)
                if isinstance(v, (dict, list)):
                    v = " ".join(map(str, v))
                kv.append({"key": k, "value": v or ""})
            if k == "field_location":
                kv.append({"key": k, "value": str(record.get(k))})

        write_df(fh, pd.DataFrame(kv))

        if record.get("fund_manager"):
            write_df(fh, pd.DataFrame(record["fund_manager"]))
        if record.get("load"):
            write_df(fh, pd.DataFrame(record["load"]))

    return str(csv_path)

def csv_to_sid_json(csv_path):
    csv_path = Path(csv_path)

    sections, cur = [], []
    with open(csv_path, "r", encoding="utf-8") as f:
        for row in csv.reader(f):
            if not any(cell.strip() for cell in row):
                if cur:
                    sections.append(cur)
                    cur = []
            else:
                cur.append(row)
        if cur:
            sections.append(cur)

    value = {}
    if sections:
        header, *rows = sections[0]
        k_i, v_i = header.index("key"), header.index("value")
        for r in rows:
            v = r[v_i].strip()
            if r[k_i] == "field_location":
                try:
                    v = ast.literal_eval(v)
                except Exception:
                    pass
            value[r[k_i]] = v

    if len(sections) > 1:
        header, *rows = sections[1]
        value["fund_manager"] = [
            {h: r[i] for i, h in enumerate(header) if h}
            for r in rows
        ]

    if len(sections) > 2:
        header, *rows = sections[2]
        value["load"] = [
            {h: r[i] for i, h in enumerate(header) if h}
            for r in rows
        ]

    file_name = str(csv_path.name).replace(".csv",".pdf")
    return {
        "metadata": {
            "document_name": file_name,
            "file_type": "sid",
            "process_date": datetime.now().strftime("%Y%m%d"),
        },
        "value": sorted(value.items()),
    }


# KIM
def kim_to_csv(json_path, output_folder):
    json_path = Path(json_path)
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)

    with open(json_path, "r", encoding="utf-8") as f:
        doc = json.load(f)

    record = doc.get("records", [{}])[0].get("value", {}) or {}
    csv_path = output_folder / f"{json_path.stem}.csv"

    def write_df(fh, df):
        df.to_csv(fh, index=False)
        fh.write("\n\n")

    with open(csv_path, "w", encoding="utf-8", newline="") as fh:
        keys = ["amc_name", "main_scheme_name", "mutual_fund_name", "description", "field_location"]
        write_df(fh, pd.DataFrame(
            [{"key": k, "value": str(record.get(k, ""))} for k in keys]
        ))

        rows = []
        for item in record.get("asset_allocation_pattern", []):
            row = {
                "instrument_type": item.get("instrument_type", ""),
                "risk_profile": item.get("risk_profile", ""),
                "min": "", "max": "", "total": ""
            }
            for a in item.get("allocation", []):
                row[a.get("type")] = a.get("value", "")
            rows.append(row)

        if rows:
            write_df(fh, pd.DataFrame(rows))

    return str(csv_path)

def csv_to_kim_json(csv_path):
    csv_path = Path(csv_path)
    sections, cur = [], []

    with open(csv_path, "r", encoding="utf-8") as f:
        for row in csv.reader(f):
            if not any(cell.strip() for cell in row):
                if cur:
                    sections.append(cur)
                    cur = []
            else:
                cur.append(row)
        if cur:
            sections.append(cur)

    value = {}
    if sections:
        header, *rows = sections[0]
        k_i, v_i = header.index("key"), header.index("value")
        for r in rows:
            v = r[v_i]
            if r[k_i] == "field_location":
                try:
                    v = ast.literal_eval(v)
                except Exception:
                    v = []
            value[r[k_i]] = v

    if len(sections) > 1:
        header, *rows = sections[1]
        value["asset_allocation_pattern"] = []
        for r in rows:
            row = {h: r[i] for i, h in enumerate(header)}
            value["asset_allocation_pattern"].append({
                "instrument_type": row.get("instrument_type", ""),
                "risk_profile": row.get("risk_profile", ""),
                "allocation": [
                    {"type": "min", "value": row.get("min", "")},
                    {"type": "max", "value": row.get("max", "")},
                    {"type": "total", "value": row.get("total", "")},
                ],
            })
    file_name = str(csv_path.name).replace(".csv",".pdf")
    return {
        "metadata": {
            "document_name": file_name,
            "file_type": "kim",
            "process_date": datetime.now().strftime("%Y%m%d"),
        },
        "records": [{"value": sorted(value.items())}],
    }


# FS
def json_to_csv(json_path, output_folder):
    json_path = Path(json_path)
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)

    keys = REGISTRY["field_keys"]
    static_keys = keys["static_keys"]
    load_keys = keys["load_keys"]
    metric_keys = keys["metric_keys"]
    manager_keys = keys["manager_keys"]
    field_location = keys["field_location"]

    with open(json_path, "r", encoding="utf-8") as f:
        doc = json.load(f)

    records = doc.get("records", [])
    max_mgr = max(len(r["value"].get("fund_manager", [])) for r in records) if records else 1

    headers = static_keys + load_keys + metric_keys
    for i in range(1, max_mgr + 1):
        headers += [f"{k}_{i}" for k in manager_keys]
    headers.append(field_location)

    rows = []
    for r in records:
        v = r["value"]
        row = []

        for k in static_keys:
            row.append(v.get(k, ""))

        entry = exit_ = ""
        for l in v.get("load", []):
            if l["type"] == "entry":
                entry = l["comment"]
            elif l["type"] == "exit":
                exit_ = l["comment"]
        row += [entry, exit_]

        metric_map = {m["name"]: m["value"] for m in v.get("metrics", [])}
        row += [metric_map.get(k, "") for k in metric_keys]

        mgrs = v.get("fund_manager", [])
        for i in range(max_mgr):
            if i < len(mgrs):
                row += [mgrs[i].get(k, "") for k in manager_keys]
            else:
                row += [""] * len(manager_keys)

        fl = v.get("field_location", [])
        row.append(json.dumps(fl[0]) if fl else "")
        rows.append(row)

    csv_path = output_folder / f"{json_path.stem}.csv"
    pd.DataFrame(rows, columns=headers).to_csv(csv_path, index=False)
    return str(csv_path)

def csv_to_fs_json(csv_path):
    df = pd.read_csv(csv_path, dtype=str, encoding="utf-8",encoding_errors="replace").fillna("")
    keys = REGISTRY["field_keys"]

    records = []
    for _, row in df.iterrows():
        value = {}
        for k in keys["static_keys"]:
            if k in row and row[k]:
                # if k == "benchmark_index":
                #     print(row[k])
                value[k] = row[k]

        loads = []
        if row.get("entry"):
            loads.append({"type": "entry", "comment": row["entry"]})
        if row.get("exit"):
            loads.append({"type": "exit", "comment": row["exit"]})
        if loads:
            value["load"] = loads

        metrics = []
        for k in keys["metric_keys"]:
            if row.get(k):
                metrics.append({"name": k, "value": row[k]})
        if metrics:
            value["metrics"] = metrics

        managers = []
        i = 1
        while f"name_{i}" in df.columns:
            fm = {}
            for k in keys["manager_keys"]:
                if row.get(f"{k}_{i}"):
                    fm[k] = row[f"{k}_{i}"]
            if fm:
                managers.append(fm)
            i += 1
        if managers:
            value["fund_manager"] = managers

        if row.get(keys["field_location"]):
            try:
                value["field_location"] = [json.loads(row[keys["field_location"]])]
            except Exception:
                pass

        records.append({"value": dict(sorted(value.items()))})

    csv_path = Path(csv_path)
    file_name = str(csv_path.name).replace(".csv",".pdf")
    return {
        "metadata": {
            "document_name": file_name,
            "file_type": "fs",
            "process_date": datetime.now().strftime("%Y%m%d"),
        },
        "records": records,
    }

@app.route("/convert_csv", methods=["POST"])
def convert_csv():
    if not session.get("logged_in"):
        return jsonify(success=False, error="Not logged in"), 403

    f = request.files.get("csv")
    if not f:
        return jsonify(success=False, error="No CSV uploaded"), 400

    csv_path = os.path.join(ws_path("conversion"), secure_filename(f.filename))
    f.save(csv_path)

    if csv_path.lower().endswith("_fs.csv"):
        json_data = csv_to_fs_json(csv_path)
    elif csv_path.lower().endswith("_sid.csv"):
        json_data = csv_to_sid_json(csv_path)
    elif csv_path.lower().endswith("_kim.csv"):
        json_data = csv_to_kim_json(csv_path)
    else:
        return jsonify(success=False, error="Unsupported CSV type"), 400

    json_name = f.filename.replace(".csv", ".json")
    json_path = os.path.join(ws_path("staging"), json_name)

    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(json_data, fh, indent=2, ensure_ascii=False)

    return jsonify(success=True, json_file=json_name)

@app.route("/convert_json", methods=["POST"])
def convert_json():
    if not session.get("logged_in"):
        return jsonify(success=False, error="Not logged in"), 403

    f = request.files.get("json")
    if not f:
        return jsonify(success=False, error="No JSON uploaded"), 400

    json_path = os.path.join(ws_path("conversion"), secure_filename(f.filename))
    f.save(json_path)

    lower = json_path.lower()
    if lower.endswith("_fs.json"):
        csv_path = json_to_csv(json_path, output_folder=ws_path("preview"))
    elif lower.endswith("_sid.json"):
        csv_path = sid_to_csv(json_path, output_folder=ws_path("preview"))
    elif lower.endswith("_kim.json"):
        csv_path = kim_to_csv(json_path, output_folder=ws_path("preview"))
    else:
        return jsonify(success=False, error="Unsupported JSON type"), 400

    return jsonify(success=True, csv_file=os.path.basename(csv_path))

@app.route("/download_csv/<filename>")
def download_csv(filename):
    if not session.get("logged_in"):
        return jsonify(success=False, error="Not logged in"), 403

    path = os.path.join(ws_path("preview"), secure_filename(filename))
    if not os.path.exists(path):
        return jsonify(success=False, error="File not found"), 404

    return send_file(path, as_attachment=True)

@app.route("/download_pipeline_json/<filename>")
def download_pipeline_json(filename):
    if not session.get("logged_in"):
        return jsonify(success=False, error="Not logged in"), 403

    filename = secure_filename(filename)
    path = os.path.join(ws_path("staging"), filename)

    if not os.path.exists(path):
        return jsonify(success=False, error="File not found"), 404

    return send_file(
        path,
        as_attachment=True,
        download_name=filename,
        mimetype="application/json"
    )

@app.route("/cleanup_pipeline", methods=["POST"])
def cleanup_pipeline():
    if not session.get("logged_in"):
        return jsonify(success=False), 403
    cleanup_session_workspace()
    init_session_workspace() 

    return jsonify(success=True)

@app.route("/viewer/json/<source>/<filename>")
def view_json(source, filename):
    if source == "dashboard":
        base = DIRS["json_dir"]()
    elif source == "csv":
        base = ws_path("staging")
    else:
        return jsonify(success=False, error="Invalid source"), 400

    return send_from_directory(base, filename)

# =====================================================
# ADMIN PANEL PUSH
# =====================================================

def ensure_job_for_json(pdf_name: str):
    row = fetch_job_by_name(pdf_name, DB_CONFIG)
    if row:
        return row["id"], row["status"]

    user = session.get("user", "unknown")
    now = datetime.now(TIME_ZONE).strftime("%Y-%m-%d %H:%M:%S")

    job_id = create_job(
        {
            "file_name": pdf_name,
            "start_time": now,
            "created_by": user,
            "uploaded_by": user,
        },
        DB_CONFIG,
    )
    return job_id, JobState.SP_CALL

def push_json_and_record(job_id, from_state, json_path):
    try:
        json_to_cog_db(json_path, DB_CONFIG)
        transition_job_state(
            job_id=job_id,
            from_state=from_state,
            to_state=JobState.PUSHED,
            error=None,
            db_config=DB_CONFIG,
        )
    except Exception as e:
        transition_job_state(
            job_id=job_id,
            from_state=from_state,
            to_state=JobState.PUSH_FAILED,
            error=str(e),
            db_config=DB_CONFIG,
        )
        raise

@app.route("/push_json_sp", methods=["POST"])
def push_json_sp():
    if not session.get("logged_in"):
        return jsonify(success=False, error="Not logged in"), 403

    # Case 1: File uploaded
    if "json" in request.files:
        f = request.files["json"]
        file_name = secure_filename(f.filename)

        json_path = os.path.join(ws_path("staging"), file_name)
        f.save(json_path)

    # Case 2: Only JSON name sent
    elif "json_name" in request.form:
        file_name = secure_filename(request.form["json_name"])
        json_path = os.path.join(ws_path("staging"), file_name)

    else:
        return jsonify(success=False, error="No JSON data provided"), 400

    # print(f"File Name: {file_name}")

    pdf_name = file_name.replace(".json", ".pdf")
    job_id, status = ensure_job_for_json(pdf_name)
    push_json_and_record(job_id, status, json_path)

    return jsonify(success=True)

# =====================================================
# SID/KIM UPLOAD
# =====================================================

@app.route('/sid-data')
def sid_data():
    if not session.get("logged_in"):
        return redirect(url_for("login")) 

    user = session.get("user", "").lower()
    return render_template("sid_data.html", user=user) 

@app.route("/upload-sid-kim", methods=["POST"])
def upload_sid_kim():

    if not session.get("logged_in"):
        return jsonify(success=False, error="Not authenticated"), 401

    pdf = request.files.get("pdf")
    meta_raw = request.form.get("meta")

    if not pdf or not meta_raw:
        return jsonify(success=False, error="Missing PDF or meta"), 400

    try:
        meta = json.loads(meta_raw)
    except Exception:
        return jsonify(success=False, error="Invalid meta JSON"), 400

    filename = secure_filename(pdf.filename)

    if not filename.endswith(("_SID.pdf", "_KIM.pdf")):
        return jsonify(
            success=False,
            error="Filename must end with _SID.pdf or _KIM.pdf"
        ), 400

    pdf_path = os.path.join(INPUT_DIR, filename)
    meta_path = pdf_path.replace(".pdf", ".meta.json")

    try:
        pdf.save(pdf_path)
        utils.save_json(meta, meta_path)

        now = datetime.now(TIME_ZONE).strftime("%Y-%m-%d %H:%M:%S")
        user = session.get("user", "unknown")

        create_job(
            {
                "file_name": filename,
                "start_time": now,
                "created_by": user,
                "uploaded_by": user,
            },
            DB_CONFIG,
        )

        return jsonify(success=True)

    except Exception as e:
        return jsonify(success=False, error=str(e)), 500

# =====================================================
# DAILY LOG
# =====================================================

@app.route('/daily-log')
def daily_logs():
    if not session.get("logged_in"):
        return redirect(url_for("login")) 

    user = session.get("user", "").lower()
    if user in ADMIN_USERS:
        user = "admin"
    return render_template("daily_logs.html", user=user, role = user)

@app.route("/load-daily-log", methods=["POST"])
def load_daily_log():
    if not session.get("logged_in"):
        return jsonify(success=False, error="Not logged in"), 403

    data = request.get_json(silent=True) or {}
    date = data.get("date")  # expected format: YYYY-MM-DD

    if not date:
        return jsonify(success=False, error="Missing date"), 400

    log_file = os.path.join(OUTPUT_DIR, "logs", date, "watcher.log")

    if not os.path.exists(log_file):
        return jsonify(success=False,content="No logs for this date.")

    try:
        with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
            return jsonify(success=True,content=f.read())
    except Exception:
        return jsonify(success=False, content="Error reading log file."), 500
    

@app.route("/files/json/")
def list_json_files():
    if not session.get("logged_in"):
        abort(403)

    json_dir = DIRS["json_dir"]()
    files = os.listdir(json_dir)

    html = """
    <h3>JSON Files</h3>
    <ul>
      {% for f in files %}
        <li><a href="/files/json/{{ f }}">{{ f }}</a></li>
      {% endfor %}
    </ul>
    """
    return render_template_string(html, files=files)

@app.route("/files/xlsx/")
def list_csv_files():
    if not session.get("logged_in"):
        abort(403)

    rep_dir = DIRS["rept_dir"]()
    files = sorted(os.listdir(rep_dir))

    html = """
    <h3>CSV Files</h3>
    <ul>
      {% for f in files %}
        <li><a href="/files/xlsx/{{ f }}">{{ f }}</a></li>
      {% endfor %}
    </ul>
    """
    return render_template_string(html, files=files)

@app.route("/files/xlsx/<path:filename>")
def serve_csv_files(filename):
    if not session.get("logged_in"):
        abort(403)

    return send_from_directory(
        DIRS["rept_dir"](),
        filename,
        as_attachment=False
    )
    
@app.route("/files/json/<path:filename>")
def serve_json_files(filename):
    if not session.get("logged_in"):
        abort(403)

    return send_from_directory(
        DIRS["json_dir"](),
        filename,
        as_attachment=False
    )
# =====================================================
# AMC - DATA
# =====================================================
@app.route('/amc-data')
def amc_data():
    if not session.get("logged_in"):
        return redirect(url_for("login")) 

    user = session.get("user", "").lower()
    return render_template("amc_data.html", user=user) 

@app.route("/company_registry")
def get_registry():
    company_registry = REGISTRY.get("amc_registry",{})
    company_name = {k:v.get("amc_name","") for k,v in company_registry.items()}
    return jsonify(company_name)

@app.route("/amc_data")
def get_amc_data():
    company_registry = REGISTRY.get("amc_registry", {})
    # print(company_registry.keys())
    return jsonify(company_registry)

@app.route('/json_list')
def json_list():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    json_dir = DIRS["json_dir"]()
    files = sorted(os.listdir(json_dir), reverse=True)
    return {"files": files[:20]}

# =====================================================
# Run App
# =====================================================

if __name__ == "__main__":
    TIME_ZONE = pytz.timezone("Asia/Kolkata")

    utils = Helper()
    config = utils.load_json(os.path.join(root_dir, "paths.json"))

    INPUT_DIR = config["inp_path"]
    OUTPUT_DIR = config["out_path"]
    WEB_DIR = config["web_path"]

    DIRS = {
        "prcs_dir": get_processed_dir,
        "fail_dir": get_failed_dir,
        "json_dir":get_json_dir,
        "rept_dir":get_report_dir
    }

    LDAP_CONFIG = config["ldap_config"]
    ADMIN_USERS = [u.lower() for u in LDAP_CONFIG.get("admin_user", [])]

    DB_CONFIG = config["db_config"]

    CONFIG_PATH = os.path.join(config["base_path"],"config")
    REGISTRY = utils.load_json(os.path.join(CONFIG_PATH,"0000","registry.json"))
    
    web = config.get("web_config", {})
    app.run(debug=True, host=web.get("host"), port=web.get("port"))
