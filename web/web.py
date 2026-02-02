import os, sys, json, json5,shutil, pytz, csv, ast #type: ignore
import pandas as pd
from datetime import timedelta, datetime
from pathlib import Path
# setup project root
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(root_dir)

from flask import ( #type: ignore
    Flask, render_template, request, 
    redirect, url_for, session, 
    send_from_directory, jsonify, send_file
)

from ldap3 import Server, Connection, ALL #type: ignore
from werkzeug.utils import secure_filename #type: ignore
# from werkzeug.security import generate_password_hash

from app.utils import Helper
from app.sqlconnect import *

# --- Flask app setup ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    static_folder=os.path.join(BASE_DIR, "static"),
    template_folder=os.path.join(BASE_DIR, "templates"),
)
app.secret_key = "supersecretkey" 
app.permanent_session_lifetime = timedelta(days=7)


def ldap_authenticate(username, password):
    server = Server(LDAP_SERVER, get_info=ALL)
    user_dn = f"{username}@{LDAP_DOMAIN}"  # Try UPN format first
    print(f"Trying LDAP bind with DN: {user_dn}")
    try:
        conn = Connection(server, user=user_dn, password=password, auto_bind=True)
        print("LDAP bind successful.")
        return conn.bound
    except Exception as e:
        print(f"LDAP auth failed: {e}")
        return False

# --- ROUTES ---
@app.route('/')
def index():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    json_dir = os.path.join(OUTPUT_DIR, "json")
    os.makedirs(json_dir, exist_ok=True)
    json_files = os.listdir(json_dir)
    user = session.get("user", "")  # Ensure user is passed
    role = session.get("role", "user")
    return render_template("dashboard.html", json_files=json_files, user=user, role = role)

@app.route('/dashboard')
def dashboard():
    user = session.get("user","")
    role = session.get("role", "user")
    return render_template("dashboard.html", user=user, role=role)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        username = request.form["username"].strip().lower()
        password = request.form["password"]
        remember = "remember" in request.form

        # if ldap_authenticate(username, password):
        if True:
            session["logged_in"] = True
            session["user"] = username
            session.permanent = remember
            session["role"] = "admin" if username in ADMIN_USERS else "user"
            return redirect(url_for("index"))
        else:
            return render_template("login.html", error="Invalid LDAP credentials.")

    return render_template("login.html")


@app.route('/auth-check')
def auth_check():
    return {"logged_in":
        bool(session.get("logged_in"))
    }

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for("login"))

def backup_json(json_path, tz):
    ts = datetime.now(tz).strftime("%Y%m%d_%H%M%S")
    base = os.path.basename(json_path)

    backup_dir = os.path.join(os.path.dirname(json_path), "backup")
    os.makedirs(backup_dir, exist_ok=True)

    backup_path = os.path.join(backup_dir, f"{base}.{ts}.bak")
    shutil.copy(json_path, backup_path)

    return backup_path



# @app.route('/signup', methods=['GET', 'POST'])
# def signup():
#     if request.method == "POST":
#         username = request.form["username"].strip().lower()
#         password = request.form["password"]
#         confirm = request.form["confirm"]

#         if not username or not password:
#             return render_template("signup.html", error="All fields are required.")
#         if password != confirm:
#             return render_template("signup.html", error="Passwords do not match.")

#         users = load_users()

#         if username in users:
#             return render_template("signup.html", error="User already exists.")

#         users[username] = {"password": generate_password_hash(password)}
#         save_users(users)

#         return redirect(url_for("login"))

#     return render_template("signup.html")

@app.route('/upload', methods=['POST'])
def upload_files():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    uploaded_files = request.files.getlist('pdfs')
    os.makedirs(INPUT_DIR, exist_ok=True)

    user = session.get("user", "unknown")
    now = datetime.now(TIME_ZONE).strftime("%Y-%m-%d %H:%M:%S")

    for file in uploaded_files:
        if not file or not file.filename.lower().endswith(".pdf"):
            continue

        filename = secure_filename(file.filename)
        file_path = os.path.join(INPUT_DIR, filename)
        file.save(file_path)

        job = {
            "file_name": filename,
            "start_time": now,
            "created_by": user,
            "uploaded_by": user,
        }
        create_job(job, DB_CONFIG)
        # print(f"[JOB CREATED] {filename} by {user}")
    return redirect('/')


@app.route("/reprocess/<int:job_id>", methods=["POST"])
def reprocess(job_id):
    
    #error : Unexpected token '<', "<!doctype "... is not valid JSON

    if not session.get("logged_in"):
        return jsonify(
            success=False,
            message="Session expired"
        ), 401

    
    REPROCESS_TARGET = {
        JobState.UPLOADED: JobState.UPLOADED,
        JobState.PARSED: JobState.UPLOADED,
        JobState.PARSE_FAILED: JobState.UPLOADED,
        JobState.PUSH_FAILED: JobState.UPLOADED,
        JobState.PUSHED: JobState.UPLOADED, 
    }

    user = session.get("user", "unknown")
    now = datetime.now(TIME_ZONE).strftime("%Y-%m-%d %H:%M:%S")

    # 1) Fetch existing job
    job = fetch_job_by_id(job_id, DB_CONFIG)
    filename = job["file_name"]
    status = job["status"]

    # 2) Decide retry target state
    
    if status not in REPROCESS_TARGET:
        return jsonify(
                success=False,
                message="Source file not found"
            ), 404

    target_state = REPROCESS_TARGET[status]

    # 3) Locate archived file
    sub_dir = ""
    if filename.endswith("_SID.pdf"):
        sub_dir = "sid"
    elif filename.endswith("_KIM.pdf"):
        sub_dir = "kim"
    elif filename.endswith("_FS.pdf"):
        sub_dir = "fs"

    processed_path = os.path.join(OUTPUT_DIR, "processed", sub_dir, filename)
    failed_path = os.path.join(OUTPUT_DIR, "failed", filename)

    src = processed_path if os.path.exists(processed_path) \
        else failed_path if os.path.exists(failed_path) \
        else None

    if not src:
        return {"success": False, "message": "Source file not found"}, 404

    os.makedirs(INPUT_DIR, exist_ok=True)
    dst = os.path.join(INPUT_DIR, filename)
    shutil.copy(src, dst)

    transition_job_state(
        job_id=job_id,
        from_state=status,
        to_state=target_state,
        error=None,
        db_config=DB_CONFIG
    )

    return {
        "success": True,
        "message": f"{filename} requeued for reprocessing"
    }

@app.route('/delete/<filename>')
def delete_file(filename):
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    file_path = os.path.join(OUTPUT_DIR, "json", filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    return redirect('/')

@app.route('/json/<filename>')
def get_json(filename):
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    return send_from_directory(os.path.join(OUTPUT_DIR, "json"), filename)

# ------------------ PDF VIEW ROUTE ------------------
@app.route('/viewer/pdf/<filename>')
def view_pdf(filename):
    
    sub_dir = ""
    if filename.endswith("_SID.pdf"):
        sub_dir = "sid"
    elif filename.endswith("_KIM.pdf"):
        sub_dir = "kim"
    elif filename.endswith("_FS.pdf"):
        sub_dir = "fs"
    
    processed_dir = os.path.join(OUTPUT_DIR, "processed",sub_dir)
    failed_dir = os.path.join(OUTPUT_DIR, "failed")

    processed_path = os.path.join(processed_dir, filename)
    failed_path = os.path.join(failed_dir, filename)

    if os.path.exists(processed_path):
        return send_from_directory(processed_dir, filename)

    if os.path.exists(failed_path):
        return send_from_directory(failed_dir, filename)

    return "PDF not found", 404


# ------------------ CSV/XLS VIEW ROUTE ------------------

#sid
def sid_to_csv(json_path, output_folder="csv_folder"):
    json_path = Path(json_path)

    output_folder = Path(output_folder) if output_folder else json_path.parent
    output_folder.mkdir(parents=True, exist_ok=True)

    csv_path = output_folder / f"{json_path.stem}.csv"

    #load json
    with open(json_path, "r", encoding="utf-8") as f:
        doc = json.load(f)
    record = doc.get("value", {}) or {}

    def write_df(fh, df):
        df.to_csv(fh, index=False)
        fh.write("\n\n")  # 2 blank rows as section separator

    with open(csv_path, "w", encoding="utf-8", newline="") as fh:

        kv_rows = []
        for k in sorted(record.keys()):
            if k not in ("fund_manager", "load", "field_location"):
                v = record.get(k)
                if isinstance(v, (dict, list)):
                    v = " ".join(v)
              
                kv_rows.append({
                    "key": k,
                    "value": v if v is not None else ""
                })
            
            if k == "field_location":
                v = record.get(k)
                v = str(v)
                kv_rows.append({
                     "key": k,
                     "value": v if v is not None else ""
                })

        df1 = pd.DataFrame(kv_rows, columns=["key", "value"])
        write_df(fh, df1)

        fund_manager = record.get("fund_manager") or []
        if fund_manager:
            df2 = pd.DataFrame(fund_manager)
            write_df(fh, df2)

        load = record.get("load") or []
        if load:
            df3 = pd.DataFrame(load)
            write_df(fh, df3)

    return str(csv_path)

def csv_to_sid_json(csv_path, output_folder="csv_folder"):
    csv_path = Path(csv_path)

    output_folder = Path(output_folder) if output_folder else csv_path.parent
    output_folder.mkdir(parents=True, exist_ok=True)

    # json_path = output_folder / f"{csv_path.stem}.json"
    # ---------- split CSV into sections ----------
    sections = []
    current = []

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if not any(cell.strip() for cell in row):
                if current:
                    sections.append(current)
                    current = []
            else:
                current.append(row)

        if current:
            sections.append(current)

    value = {}
    if sections:
        header, *rows = sections[0]
        key_idx = header.index("key")
        val_idx = header.index("value")

        for r in rows:
            k = r[key_idx].strip()
            v = r[val_idx].strip()

            if k == "field_location" and v:
                try:
                    v = ast.literal_eval(v)  # safe dict restore
                except Exception:
                    pass

            value[k] = v

    if len(sections) > 1:
        header, *rows = sections[1]
        fund_manager = []

        for r in rows:
            rec = {
                h: r[i].strip() if i < len(r) else ""
                for i, h in enumerate(header)
                if h
            }
            fund_manager.append(rec)

        value["fund_manager"] = fund_manager

    if len(sections) > 2:
        header, *rows = sections[2]
        load = []

        for r in rows:
            rec = {
                h: r[i].strip() if i < len(r) else ""
                for i, h in enumerate(header)
                if h
            }
            load.append(rec)

        value["load"] = load

    output = {
        "metadata": {
        "document_name": csv_path.name,
        "file_type": "sid",
        "process_date": datetime.today().strftime("%Y%m%d")
    },
        "value": value
    }

    # with open(json_path, "w", encoding="utf-8") as f:
    #     json.dump(output, f, ensure_ascii=False, indent=2)

    return output

#kim
def kim_to_csv(json_path, output_folder="csv_folder"):
    json_path = Path(json_path)

    output_folder = Path(output_folder) if output_folder else json_path.parent
    output_folder.mkdir(parents=True, exist_ok=True)

    csv_path = output_folder / f"{json_path.stem}.csv"

    with open(json_path, "r", encoding="utf-8") as f:
        doc = json.load(f)

    record = (
        doc.get("records", [{}])[0]
        .get("value", {})
    ) or {}

    def write_df(fh, df):
        df.to_csv(fh, index=False)
        fh.write("\n\n")  # section separator

    with open(csv_path, "w", encoding="utf-8", newline="") as fh:

        # ================= DF1: Static KV =================
        kim_static_keys = [
            "amc_name",
            "main_scheme_name",
            "mutual_fund_name",
            "description",
            "field_location"   # ✅ added
        ]

        kv_rows = []
        for k in kim_static_keys:
            v = record.get(k, "")
            if isinstance(v, (dict, list)):
                v = str(v)
            kv_rows.append({
                "key": k,
                "value": v if v is not None else ""
            })

        df1 = pd.DataFrame(kv_rows, columns=["key", "value"])
        write_df(fh, df1)

        # ================= DF2: Asset Allocation =================
        allocation_rows = []

        for item in record.get("asset_allocation_pattern", []):
            row = {
                "instrument_type": item.get("instrument_type", ""),
                "risk_profile": item.get("risk_profile", "")
            }

            row.update({"min": "", "max": "", "total": ""})

            for alloc in item.get("allocation", []):
                alloc_type = alloc.get("type")
                if alloc_type in row:
                    row[alloc_type] = alloc.get("value", "")

            allocation_rows.append(row)

        if allocation_rows:
            df2 = pd.DataFrame(
                allocation_rows,
                columns=["instrument_type", "min", "max", "total", "risk_profile"]
            )
            write_df(fh, df2)

    return str(csv_path)

def csv_to_kim_json(csv_path, output_folder="csv_folder"):
    csv_path = Path(csv_path)

    output_folder = Path(output_folder) if output_folder else csv_path.parent
    output_folder.mkdir(parents=True, exist_ok=True)

    # json_path = output_folder / f"{csv_path.stem}.json"

    # ---------- split CSV into sections ----------
    sections, current = [], []

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if not any(cell.strip() for cell in row):
                if current:
                    sections.append(current)
                    current = []
            else:
                current.append(row)
        if current:
            sections.append(current)

    value = {}
    if sections:
        header, *rows = sections[0]
        key_idx = header.index("key")
        val_idx = header.index("value")

        for r in rows:
            k = r[key_idx].strip()
            v = r[val_idx].strip()

            if k == "field_location" and v:
                try:
                    v = ast.literal_eval(v)  # ✅ safe restore
                except Exception:
                    v = []

            value[k] = v

    if len(sections) > 1:
        header, *rows = sections[1]
        asset_allocation_pattern = []

        for r in rows:
            row = {h: r[i].strip() if i < len(r) else "" for i, h in enumerate(header)}

            allocation = [
                {"type": "min", "value": row.get("min", "")},
                {"type": "max", "value": row.get("max", "")},
                {"type": "total", "value": row.get("total", "")},
            ]

            asset_allocation_pattern.append({
                "instrument_type": row.get("instrument_type", ""),
                "risk_profile": row.get("risk_profile", ""),
                "allocation": allocation
            })

        value["asset_allocation_pattern"] = asset_allocation_pattern

    output = {
        "metadata": {
        "document_name": csv_path.name,
        "file_type": "kim",
        "process_date": datetime.today().strftime("%Y%m%d")
    },
        "records": [{"value": value}]
    }
    # with open(json_path, "w", encoding="utf-8") as f:
    #     json.dump(output, f, ensure_ascii=False, indent=2)

    return output

#factsheet
def json_to_csv(json_path, output_dir="csv_folder"):
    keys = REGISTRY.get("field_keys")
    static_keys, load_keys, metric_keys, manager_keys,field_location = (
        keys["static_keys"], keys["load_keys"], keys["metric_keys"], keys["manager_keys"],keys["field_location"]
    )

    # Keys to exclude
    EXCLUDE_KEYS = {"Riskometer", "Riskometer_benchmark", "Riskometer_scheme"}

    with open(json_path, "r", encoding="utf-8") as f:
        doc = json.load(f)

    records = doc.get("records", [])
        
    max_manager = max((len(r["value"].get("fund_manager", [])) for r in records), default=1)

    # Build headers
    headers = [k for k in static_keys if k not in EXCLUDE_KEYS] + load_keys + metric_keys
    for i in range(1, max_manager + 1):
        headers.extend([f"{k}_{i}" for k in manager_keys])
        
    headers.append(field_location)

    def flatten_to_row(value):
        # Remove unwanted keys
        for bad_key in EXCLUDE_KEYS:
            value.pop(bad_key, None)

        row = []
        # static
        for k in static_keys:
            if k in EXCLUDE_KEYS:
                continue
            v = value.get(k, "")
            if isinstance(v, list):
                v = ", ".join(v)
            row.append(v)

        # loads FIRST (to match header order)
        entry, exit_ = "", ""
        for l in value.get("load", []):
            if l.get("type") == "entry":
                entry = l.get("comment", "")
            elif l.get("type") == "exit":
                exit_ = l.get("comment", "")
        row.extend([entry, exit_])

        # metrics AFTER loads
        metric_map = {m.get("name"): m.get("value") for m in value.get("metrics", [])}
        row.extend([metric_map.get(k, "") for k in metric_keys])

        # fund managers
        managers = value.get("fund_manager", [])
        for i in range(max_manager):
            if i < len(managers):
                fm = managers[i]
                row.extend([fm.get(k, "") for k in manager_keys])
            else:
                row.extend([""] * len(manager_keys))
                
        #field location
        fl = value.get("field_location", [{}])
        if isinstance(fl, list) and fl:
            fl_val = json.dumps(fl[0], ensure_ascii=False)
        else:
            fl_val = ""
        
        row.extend([fl_val])

        return row

    # Build rows
    rows = [flatten_to_row(r["value"]) for r in records]

    # Sanity check: ensure row length matches headers
    for i, row in enumerate(rows[:5]):  # check first few rows
        if len(row) != len(headers):
            raise ValueError(f"Row {i} length mismatch: {len(row)} vs {len(headers)}")

    # Save CSV
    base = os.path.splitext(os.path.basename(json_path))[0]
    csv_path = os.path.join(output_dir, f"{base}.csv")
    pd.DataFrame(rows, columns=headers).to_csv(csv_path, index=False, encoding="utf-8")
    return csv_path

def rebuild_json_from_csv(csv_path):
    df = pd.read_csv(csv_path, dtype=str)
    df = df.dropna(axis=1, how="all")
    df = df.loc[:, ~(df == "").all()]
    df = df.fillna("")

    keys = REGISTRY.get("field_keys", {})
    static_keys = keys.get("static_keys", [])
    load_keys = keys.get("load_keys", [])
    metric_keys = keys.get("metric_keys", [])
    manager_keys = keys.get("manager_keys", [])
    field_location_key = keys.get("field_location", "field_location")


    records = []

    for _, row in df.iterrows():
        # print(row)
        value = {}

        for k in static_keys:
            if k in df.columns and row[k] != "":
                value[k] = row[k]

    
        loads = []
        if "entry" in df.columns and row["entry"] != "":
            loads.append({"type": "entry", "comment": row["entry"]})
        if "exit" in df.columns and row["exit"] != "":
            loads.append({"type": "exit", "comment": row["exit"]})
        if loads:
            value["load"] = loads
        
        # print(loads)
        # print(value)

        metrics = []
        for m in metric_keys:
            if m in df.columns and row[m] != "":
                metrics.append({"name": m, "value": row[m]})
        if metrics:
            value["metrics"] = metrics

        managers = []
        i = 1
        while True:
            if f"name_{i}" not in df.columns:
                break

            fm = {}
            for k in manager_keys:
                col = f"{k}_{i}"
                if col in df.columns and row[col] != "":
                    fm[k] = row[col]

            if fm:
                managers.append(fm)
            i += 1
            
        # print(metrics)
        # print(managers)

        if managers:
            value["fund_manager"] = managers

        if field_location_key in df.columns and row[field_location_key]:
            try:
                value["field_location"] = [json.loads(row[field_location_key])]
            except Exception:
                pass
        
        value = dict(sorted(value.items()))
        records.append({"value": value})
        

    base = os.path.splitext(os.path.basename(csv_path))[0]
 

    return {
        "metadata": {
            "document_name": f"{base}.json",
            "file_type": "fs",
            "process_date": datetime.now().strftime("%Y%m%d")
        },
        "records": records
    }
   
 
@app.route("/download_json", methods=["GET"])
def download_json():
    # Get JSON path from query parameter
    json_path = request.args.get("path")
    if not json_path:
        return {"success": False, "message": "Missing ?path=... parameter"}, 400
    
    return send_file(
        json_path,
        as_attachment=True,
        download_name=os.path.basename(json_path),
        mimetype="text/json"
    )
    

@app.route("/download_csv", methods=["GET"])
def download_csv():
    # Get JSON path from query parameter
    json_path = request.args.get("path")
    if not json_path:
        return {"success": False, "message": "Missing ?path=... parameter"}, 400

    if json_path.lower().endswith("_fs.json"):
        csv_path = json_to_csv(json_path)
    
    elif json_path.lower().endswith("_kim.json"):
        csv_path = kim_to_csv(json_path)
    
    elif json_path.lower().endswith("_sid.json"):
        csv_path = sid_to_csv(json_path)

    return send_file(
        csv_path,
        as_attachment=True,
        download_name=os.path.basename(csv_path),
        mimetype="text/csv"
    )
    
@app.route("/convert_csv", methods=["POST"])
def convert_csv():
    if not session.get("logged_in"):
        return jsonify(success=False, error="Not logged in"), 403

    csv_file = request.files.get("csv")
    if not csv_file:
        return jsonify(success=False, error="No CSV uploaded"), 400

    try:
        os.makedirs("tmp", exist_ok=True)

        csv_path = os.path.join("tmp", csv_file.filename)
        csv_file.save(csv_path)
        
        if csv_path.lower().endswith("_fs.csv"):

            json_data = rebuild_json_from_csv(csv_path)
        
        elif csv_path.lower().endswith("_sid.csv"):
            json_data = csv_to_sid_json(csv_path)
        
        elif csv_path.lower().endswith("_kim.csv"):
            json_data = csv_to_kim_json(csv_path)

        json_filename = csv_file.filename.replace(".csv", ".json")
        json_path = os.path.join("tmp", json_filename)

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=2)

        return jsonify(
            success=True,
            json_file=json_filename   # ✅ IMPORTANT
        )

    except Exception as e:
        return jsonify(success=False, error=str(e)), 500

# ------------------ JSON VIEW ROUTE ------------------
@app.route('/viewer/json/<source>/<filename>')
def view_json(source, filename):
    if source == "dashboard":
        json_dir = os.path.join(OUTPUT_DIR, "json")
    
    elif source == "csv":
        json_dir = "tmp"

    # print(json_dir)
    return send_from_directory(json_dir, filename)

@app.route('/logs')
def logs():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    log_dir = os.path.join(OUTPUT_DIR, "logs")
    json_dir = os.path.join(OUTPUT_DIR, "json")

    latest_log_text = ""
    if os.path.exists(log_dir):
        log_files = sorted(
            [os.path.join(log_dir, f) for f in os.listdir(log_dir) if f.endswith(".log")],
            key=os.path.getmtime,
            reverse=True,
        )
        if log_files:
            with open(log_files[0], "r", encoding="utf-8", errors="ignore") as f:
                latest_log_text = "".join(f.readlines()[-50:])  # last 50 lines

    json_files = []
    if os.path.exists(json_dir):
        json_files = sorted(
            [f for f in os.listdir(json_dir) if f.endswith(".json")],
            reverse=True
        )

    return {
        "logs": latest_log_text,
        "json_files": json_files
    }

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
    json_dir = os.path.join(OUTPUT_DIR, "json")
    os.makedirs(json_dir, exist_ok=True)
    files = sorted(os.listdir(json_dir), reverse=True)
    return {"files": files[:20]}


#config editor
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
    year_path = os.path.join(CONFIG_BASE_PATH, str(year))
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
    path = os.path.join(CONFIG_BASE_PATH, str(year), filename)

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
    path = os.path.join(CONFIG_BASE_PATH, str(year), filename)
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

    src = os.path.join(CONFIG_BASE_PATH, str(year), filename)
    if not os.path.exists(src):
        return jsonify({"success": False, "message": "File not found"})

    backup_dir = os.path.join(CONFIG_BASE_PATH, "0001")
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

    year_dir = os.path.join(CONFIG_BASE_PATH, str(year))
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

    file_path = os.path.join(CONFIG_BASE_PATH, str(year), filename)
    if not os.path.exists(file_path):
        return jsonify({"success": False, "error": "File not found"})

    os.remove(file_path)
    return jsonify({"success": True})

#check amc data
@app.route('/amc-data')
def amc_data():
    if not session.get("logged_in"):
        return redirect(url_for("login")) 

    user = session.get("user", "").lower()
    # if user not in ADMIN_USERS:
    #     return redirect(url_for("index"))

    return render_template("amc_data.html", user=user) 

@app.route('/sid-data')
def sid_data():
    if not session.get("logged_in"):
        return redirect(url_for("login")) 

    user = session.get("user", "").lower()
    # if user not in ADMIN_USERS:
    #     return redirect(url_for("index"))

    return render_template("sid_data.html", user=user) 
#logs
@app.route('/csv-to-json')
def csv_to_json():
    if not session.get("logged_in"):
        return redirect(url_for("login")) 

    user = session.get("user", "").lower()
    return render_template("csv_to_json.html", user=user)

#logs
@app.route('/daily-log')
def daily_logs():
    if not session.get("logged_in"):
        return redirect(url_for("login")) 

    user = session.get("user", "").lower()
    return render_template("daily_logs.html", user=user)

@app.route("/load-daily-log", methods=["POST"])
def load_daily_log():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    date = request.get_json().get("date")  # format: 2025-10-20
    log_file = os.path.join(OUTPUT_DIR, "logs", date, "watcher.log")

    if not os.path.exists(log_file):
        return {"success": False, "content": "No logs for this date."}

    try:
        with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
            return {"success": True, "content": f.read()}
    except:
        return {"success": False, "content": "Error reading log file."}


#csv-apply
@app.route("/apply_csv", methods=["POST"])
def apply_csv():
    if not session.get("logged_in"):
        return {"success": False, "error": "Not logged in"}, 403

    job_id = request.form.get("job_id")
    csv_file = request.files.get("csv")

    if not job_id or not csv_file:
        return {"success": False, "error": "Missing job_id or csv"}, 400

    try:
        job = fetch_job_by_id(int(job_id), DB_CONFIG)
        json_path = job["json_path"]

        if not json_path or not os.path.exists(json_path):
            return {"success": False, "error": "JSON not found"}, 404

        # save uploaded CSV temporarily
        tmp_csv = os.path.join("/tmp", secure_filename(csv_file.filename))
        csv_file.save(tmp_csv)

        # backup existing JSON
        backup_path = backup_json(json_path, TIME_ZONE)

        # rebuild JSON
        new_json = rebuild_json_from_csv(tmp_csv)

        # overwrite active JSON
        with open(json_path, "w", encoding="utf-8") as fh:
            json.dump(new_json, fh, indent=2, ensure_ascii=False)

        return {
            "success": True,
            "backup": backup_path,
            "json_path": json_path
        }

    except Exception as e:
        return {"success": False, "error": str(e)}, 500

@app.route("/push_job/<int:job_id>", methods=["POST"])
def push_job(job_id):
    # --- auth guards ---
    if not session.get("logged_in"):
        return jsonify(success=False, error="Not Logged In"), 403

    # if session.get("role") != "admin":
    #     return jsonify(success=False, error="Forbidden"), 403

    try:
        job = fetch_job_by_id(job_id, DB_CONFIG)
        status = job["status"]

        if status not in (JobState.PARSED, JobState.PUSH_FAILED):
            return jsonify(success=False, error=f"Job not pushable in state {status}"), 400

        json_path = job.get("json_path")
        if not json_path or not os.path.exists(json_path):
            return jsonify(success=False, error=f"JSON not found"), 404

        # 4) Express intent (increment push attempts)
        conn = establish_connection(DB_CONFIG)
        cur = conn.cursor()
        cur.execute("""
            UPDATE mf_status_report
               SET push_attempts = push_attempts + 1
             WHERE id = %s
               AND status IN ('PARSED', 'PUSH_FAILED')
        """, (job_id,))
        conn.commit()
        cur.close()
        conn.close()

        success = json_to_cog_db(json_path, DB_CONFIG)

        # 6) Final state transition
        transition_job_state(
            job_id=job_id,
            from_state=status,
            to_state=JobState.PUSHED if success else JobState.PUSH_FAILED,
            error=None if success else "Admin panel push failed",
            db_config=DB_CONFIG
        )

        return {"success": success}

    except Exception as e:
        return jsonify(success=False, error= str(e)), 500


#sid/kim

@app.route("/upload-sid-kim", methods=["POST"])
def upload_sid_kim():
    if not session.get("logged_in"):
        return {"success": False, "error": "Not authenticated"}, 401

    pdf = request.files.get("pdf")
    meta_raw = request.form.get("meta")

    if not pdf or not meta_raw:
        return {"success": False, "error": "Missing PDF or meta"}, 400

    try:
        meta = json.loads(meta_raw)
    except Exception:
        return {"success": False, "error": "Invalid meta JSON"}, 400

    filename = secure_filename(pdf.filename)

    # 🔒 enforce naming rule
    if not (filename.endswith("_SID.pdf") or filename.endswith("_KIM.pdf")):
        return {
            "success": False,
            "error": "Filename must end with _SID.pdf or _KIM.pdf"
        }, 400

    # paths
    pdf_path = os.path.join(INPUT_DIR, filename)
    meta_path = pdf_path.replace(".pdf", ".meta.json")

    try:
        # save PDF
        pdf.save(pdf_path)

        # save meta.json
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)

        # OPTIONAL: create DB job entry (if needed)
        now = datetime.now(TIME_ZONE).strftime("%Y-%m-%d %H:%M:%S")
        user = session.get("user", "unknown")

        create_job({
            "file_name": filename,
            "start_time": now,
            "created_by": user,
            "uploaded_by": user
        }, DB_CONFIG)

        return {"success": True}

    except Exception as e:
        return {"success": False, "error": str(e)}, 500


# --- run app ---
if __name__ == '__main__':

    TIME_ZONE = pytz.timezone("Asia/Kolkata")

    utils = Helper()
    path = os.path.join(root_dir, r"paths.json")
    config = utils.load_json(path)
    print(path)
    INPUT_DIR = config["amc_path"]
    OUTPUT_DIR = config["output_path"]

    LDAP_CONFIG = config.get("ldap")
    LDAP_SERVER = LDAP_CONFIG["path"]
    LDAP_DOMAIN = LDAP_CONFIG["domain"]
    ADMIN_USERS = [val.lower() for val in LDAP_CONFIG.get("admin_user", [])]

    CONFIG_BASE_PATH = config["config_base_path"]
    DB_CONFIG = config.get("db_config")
    WEB_CONFIG = config.get("web_host",{})

    REGISTRY = utils.load_json(config.get("config_global_path",""))
    SP_REPORT_RUN = True
    
    # host = WEB_CONFIG.get("host")
    # port = WEB_CONFIG.get("port") 
    # host = "NCOG-LPT-TCH-32.Cogencis.com"
    # port = 5000
    # app.run(debug=True, host=host, port=port)

    app.run(debug=True, host="127.0.0.1", port=5055)
