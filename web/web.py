import os, sys, json, time, json5,shutil, pytz
# setup project root
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(root_dir)


from datetime import timedelta, datetime
# from zoneinfo import ZoneInfo
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, jsonify, send_file
from werkzeug.utils import secure_filename
# from werkzeug.security import generate_password_hash
from ldap3 import Server, Connection, ALL #type: ignore
import pandas as pd

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

        # Optional: keep meta ONLY for parser hints (not business state)
        # meta_path = os.path.splitext(file_path)[0] + ".meta.json"
        # with open(meta_path, "w", encoding="utf-8") as mf:
        #     json.dump({
        #         "uploaded_by": user,
        #         "uploaded_at": now
        #     }, mf)

        # Create job (NO outcome fields)
        job = {
            "file_name": filename,
            "start_time": now,
            "created_by": user,
            "uploaded_by": user,
        }
        create_job(job, DB_CONFIG)
        # print(f"[JOB CREATED] {filename} by {user}")
    return redirect('/')

@app.route("/reprocess/<filename>", methods=["POST"])
def reprocess(filename):
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    user = session.get("user", "unknown")
    now = datetime.now(TIME_ZONE).strftime("%Y-%m-%d %H:%M:%S")

    # locate archived file
    sub_dir = ""
    if filename.endswith("_SID.pdf"):
        sub_dir = "sid"
    elif filename.endswith("_KIM.pdf"):
        sub_dir = "kim"
    elif filename.endswith("_FS.pdf"):
        sub_dir = "fs"

    processed_path = os.path.join(OUTPUT_DIR, "processed", sub_dir, filename)
    failed_path = os.path.join(OUTPUT_DIR, "failed", filename)

    if os.path.exists(processed_path):
        src = processed_path
    elif os.path.exists(failed_path):
        src = failed_path
    else:
        return {"success": False, "message": "File not found"}

    # copy back to input for watcher
    os.makedirs(INPUT_DIR, exist_ok=True)
    dst = os.path.join(INPUT_DIR, filename)
    shutil.copy(src, dst)

    # optional parser meta
    meta_path = os.path.splitext(dst)[0] + ".meta.json"
    with open(meta_path, "w", encoding="utf-8") as mf:
        json.dump({
            "uploaded_by": user,
            "reprocess": True
        }, mf)

    # NEW job entry
    job = {
        "file_name": filename,
        "start_time": now,
        "created_by": user,
        "uploaded_by": user,
    }
    create_job(job, DB_CONFIG)
    # print(f"[REPROCESS JOB CREATED] {filename} by {user}")
    return {"success": True, "message": f"{filename} requeued"}

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
def json_to_csv(json_path, output_dir=".csv_folder"):
    keys = REGISTRY.get(
        "field_keys",
        {
            "static_keys": [
                "amc_name", "main_scheme_name", "mutual_fund_name", "benchmark_index",
                "monthly_aaum_date", "monthly_aaum_value", "scheme_launch_date",
                "min_addl_amt", "min_addl_amt_multiple", "min_amt", "min_amt_multiple"
            ],
            "load_keys": ["entry", "exit"],
            "metric_keys": [
                "alpha", "arithmetic_mean_ratio", "average_div_yield", "average_pb", "average_pe",
                "avg_maturity", "beta", "correlation_ratio", "downside_deviation", "information_ratio",
                "macaulay", "mod_duration", "port_turnover_ratio", "r_squared_ratio", "roe_ratio",
                "sharpe", "sortino_ratio", "std_dev", "tracking_error", "treynor_ratio",
                "upside_deviation", "ytm"
            ],
            "manager_keys": ["name", "managing_fund_since", "total_exp", "qualification"],
            "field_location":"field_location"
        }
    )
    static_keys, load_keys, metric_keys, manager_keys,field_location = (
        keys["static_keys"], keys["load_keys"], keys["metric_keys"], keys["manager_keys"],keys["field_location"]
    )

    # Keys to exclude
    EXCLUDE_KEYS = {"Riskometer", "Riskometer_benchmark", "Riskometer_scheme"}

    with open(json_path, "r", encoding="utf-8") as f:
        doc = json.load(f)

    records = doc.get("records", [])
    
    meta_data = doc.get("metadata",{
        "document_name": "X_DD-MMM-YY_FS.pdf",
        "file_type": "fs",
        "process_date": "YYYYMMDD"
    })
    
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

@app.route("/download_csv", methods=["GET"])
def download_csv():
    # Get JSON path from query parameter
    json_path = request.args.get("path")
    if not json_path:
        return {"success": False, "message": "Missing ?path=... parameter"}, 400

  
    csv_path = json_to_csv(json_path)
   
    return send_file(
        csv_path,
        as_attachment=True,
        download_name=os.path.basename(csv_path),
        mimetype="text/csv"
    )

# ------------------ JSON VIEW ROUTE ------------------
@app.route('/viewer/json/<filename>')
def view_json(filename):
    json_dir = os.path.join(OUTPUT_DIR, "json")
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
            SELECT file_name, start_time, end_time, status, json_path, error,
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

# @app.route("/push_job", methods=["POST"])
# def push_job():
#     if not session.get("logged_in"):
#         return {"success": False, "error": "Not logged in"}, 403

#     # optional: restrict to admins only
#     if session.get("role") != "admin":
#         return {"success": False, "error": "Forbidden"}, 403

#     data = request.get_json()
#     job_id = data.get("job_id")

#     if not job_id:
#         return {"success": False, "error": "Missing job_id"}, 400

#     try:
#         # 1. fetch job
#         job = fetch_job_by_id(int(job_id), DB_CONFIG)

#         # only allow push from APPROVED or PUSH_FAILED
#         if job["status"] not in (JobState.APPROVED, JobState.PUSH_FAILED):
#             return {
#                 "success": False,
#                 "error": f"Job not pushable in state {job['status']}"
#             }, 400

#         json_path = job["json_path"]
#         if not json_path or not os.path.exists(json_path):
#             return {"success": False, "error": "JSON not found"}, 404

#         # 2. increment push_attempts (INTENT expressed)
#         conn = establish_connection(DB_CONFIG)
#         cur = conn.cursor()
#         cur.execute(
#             """
#             UPDATE mf_status_report
#             SET push_attempts = push_attempts + 1
#             WHERE id = %s
#             """,
#             (job_id,)
#         )
#         conn.commit()
#         cur.close()
#         conn.close()

#         # 3. call SP
#         success = json_to_cog_db(json_path, DB_CONFIG)

#         # 4. transition job state
#         transition_job_state(
#             job_id=int(job_id),
#             from_state=job["status"],
#             to_state=JobState.PUSHED if success else JobState.PUSH_FAILED,
#             error=None if success else "Admin panel push failed",
#             db_config=DB_CONFIG
#         )

#         return {"success": success}

#     except Exception as e:
#         return {"success": False, "error": str(e)}, 500

@app.route("/push_job/<int:job_id>", methods=["POST"])
def push_job(job_id):
    if not session.get("logged_in"):
        return jsonify({"success": False, "error": "Not logged in"}), 403

    # TEMP stub – real logic later
    print(f"[PUSH REQUEST] job_id={job_id}")

    return jsonify({"success": True})



# --- run app ---
if __name__ == '__main__':

    TIME_ZONE = pytz.timezone("Asia/Kolkata")

    utils = Helper()
    path = os.path.join(root_dir, r"paths.json")
    config = utils.load_json(path)
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
    
    # host = "NCOG-LPT-TCH-32.Cogencis.com"
    # port = 5000
    # host = WEB_CONFIG.get("host")
    # port = WEB_CONFIG.get("port") 
    # app.run(debug=True, host=host, port=port)

    app.run(debug=True, host="127.0.0.1", port=5055)
