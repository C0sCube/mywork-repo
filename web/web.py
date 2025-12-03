import os, sys, json, time, json5,shutil, pytz
# setup project root
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(root_dir)


from datetime import timedelta, datetime
# from zoneinfo import ZoneInfo
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, jsonify
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
from ldap3 import Server, Connection, ALL #type: ignore
from app.sqlconnect import establish_connection
from app.utils import Helper
from sqlconnect import update_report_table

# --- Flask app setup ---
app = Flask(__name__)
app.secret_key = "supersecretkey" 
app.permanent_session_lifetime = timedelta(days=7)


# --- timezone ---

TIME_ZONE = pytz.timezone("Asia/Kolkata")


# --- paths and config ---
utils = Helper()
path = os.path.join(root_dir, r"paths.json")
config = utils.load_json(path)
INPUT_DIR = config["amc_path"]
OUTPUT_DIR = config["output_path"]
USERS_FILE = os.path.join(root_dir, "web", "config", "users.json")

LDAP_CONFIG = config.get("ldap")
LDAP_SERVER = LDAP_CONFIG["path"]
LDAP_DOMAIN = LDAP_CONFIG["domain"]
ADMIN_USERS = LDAP_CONFIG.get("admin_user", [])

CONFIG_BASE_PATH = config["config_base_path"]
DB_CONFIG = config.get("db_config")

REGISTRY = utils.load_json(config.get("config_global_path",""))

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


# --- helper to load/save users ---
def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)


# --- ROUTES ---
@app.route('/')
def index():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    json_dir = os.path.join(OUTPUT_DIR, "json")
    os.makedirs(json_dir, exist_ok=True)
    json_files = os.listdir(json_dir)
    user = session.get("user", "")  # Ensure user is passed
    return render_template("dashboard.html", json_files=json_files, user=user)

@app.route('/dashboard')
def dashboard():
    user = session.get("user", "")
    return render_template('dashboard.html', user=user)


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
            return redirect(url_for("index"))
        else:
            return render_template("login.html", error="Invalid LDAP credentials.")

    return render_template("login.html")

def not_logged_in_response():
    return jsonify({"success": False, "error": "Not logged in"}), 401

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == "POST":
        username = request.form["username"].strip().lower()
        password = request.form["password"]
        confirm = request.form["confirm"]

        if not username or not password:
            return render_template("signup.html", error="All fields are required.")
        if password != confirm:
            return render_template("signup.html", error="Passwords do not match.")

        users = load_users()

        if username in users:
            return render_template("signup.html", error="User already exists.")

        users[username] = {"password": generate_password_hash(password)}
        save_users(users)

        return redirect(url_for("login"))

    return render_template("signup.html")

@app.route('/upload', methods=['POST'])
def upload_files():
    if not session.get("logged_in"): return redirect(url_for("login"))

    uploaded_by = session.get("user", "unknown")
    uploaded_files = request.files.getlist('pdfs')
    os.makedirs(INPUT_DIR, exist_ok=True)

    for file in uploaded_files:
        if file and file.filename.lower().endswith(".pdf"):
            filename = secure_filename(file.filename)
            file_path = os.path.join(INPUT_DIR, filename)
            file.save(file_path)

            # create a small sidecar meta JSON so parser can read who uploaded it
            meta = {
                "uploaded_by": uploaded_by,
                "uploaded_at": datetime.now(TIME_ZONE).strftime("%Y-%m-%d %H:%M:%S")
            }
            try:
                meta_path = os.path.splitext(file_path)[0] + ".meta.json"
                # print(meta_path)
                with open(meta_path, "w", encoding="utf-8") as mf:
                    json.dump(meta, mf)
            except Exception as e:
                print(f"Failed to write meta for {filename}: {e}")

            # insert initial DB row via update_table (so dashboard shows file immediately)
            now = datetime.now(TIME_ZONE).strftime("%Y-%m-%d %H:%M:%S")
            print(now)
            initial = {
                "start_time": now,
                "end_time": None,
                "file_name": filename,
                "json_path": None,
                "status": "Pending",
                "error": None,
                "uploaded_by": uploaded_by
            }
            try:
                # import update_table at top: from sqlconnect import update_table
                update_report_table(initial, db_config=DB_CONFIG)
            except Exception as e:
                print(f"Failed to write initial DB row for {filename}: {e}")

            print(f"File '{filename}' uploaded by {uploaded_by}")

    time.sleep(1)
    return redirect('/')

@app.route("/reprocess/<filename>", methods=["POST"])
def reprocess(filename):
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    uploaded_by = session.get("user", "unknown")

    # Look for file in processed or failed dirs
    processed_path = os.path.join(OUTPUT_DIR, "processed", secure_filename(filename))
    failed_path = os.path.join(OUTPUT_DIR, "failed", secure_filename(filename))

    if os.path.exists(processed_path):
        file_path = processed_path
    elif os.path.exists(failed_path):
        file_path = failed_path
    else:
        return {"success": False, "message": f"{filename} not found in output dirs"}

    # Copy/move back into INPUT_DIR so the parser picks it up again
    os.makedirs(INPUT_DIR, exist_ok=True)
    new_path = os.path.join(INPUT_DIR, filename)
    shutil.copy(file_path, new_path)

    # Write fresh meta JSON
    meta = {
        "uploaded_by": uploaded_by,
        "uploaded_at": datetime.now(TIME_ZONE).strftime("%Y-%m-%d %H:%M:%S")
    }
    meta_path = os.path.splitext(new_path)[0] + ".meta.json"
    with open(meta_path, "w", encoding="utf-8") as mf:
        json.dump(meta, mf)

    # Insert new DB row so dashboard shows it again
    now = datetime.now(TIME_ZONE).strftime("%Y-%m-%d %H:%M:%S")
    print(now)
    initial = {
        "start_time": now,
        "end_time": None,
        "file_name": filename,
        "json_path": None,
        "status": "Pending",
        "error": None,
        "uploaded_by": uploaded_by
    }
    update_report_table(initial, db_config=DB_CONFIG)

    print(f"File '{filename}' requeued for processing by {uploaded_by}")
    return {"success": True, "message": f"{filename} requeued"}

@app.route('/record-upload', methods=['POST'])
def record_upload():
    if not session.get("logged_in"):
        return jsonify({"success": False, "error": "Not logged in"}), 403

    data = request.get_json()
    data["json_path"] = ""  # optional: fill later via parser
    success = update_report_table(data, db_config=DB_CONFIG)

    return jsonify({"success": success})



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
    processed_dir = os.path.join(OUTPUT_DIR, "processed")
    failed_dir = os.path.join(OUTPUT_DIR, "failed")

    processed_path = os.path.join(processed_dir, filename)
    failed_path = os.path.join(failed_dir, filename)

    if os.path.exists(processed_path):
        return send_from_directory(processed_dir, filename)

    if os.path.exists(failed_path):
        return send_from_directory(failed_dir, filename)

    return "PDF not found", 404

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

# @app.route('/status_data')
# def status_data():
#     """Return latest entries from holy_sheet as JSON for dashboard polling."""
#     if not session.get("logged_in"):
#         return redirect(url_for("login"))

#     try:
#         conn = establish_connection(db_config=DB_CONFIG)
#         cur = conn.cursor(dictionary=True)
#         cur.execute("""
#             SELECT file_name, start_time, end_time, status,json_path, error, uploaded_by
#             FROM mf_status_report
#             ORDER BY start_time DESC
#             LIMIT 30
#         """)
#         rows = cur.fetchall()
#         cur.close()
#         conn.close()
#         # print(rows)
#         return {"success": True, "rows": rows}
#     except Exception as e:
#         print("status_data error:", e)
#         return {"success": False, "rows": []}
 
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
            SELECT file_name, start_time, end_time, status, json_path, error, uploaded_by
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

@app.route('/config-editor')
def config_editor():
    if not session.get("logged_in"):
        return redirect(url_for("login")) 

    user = session.get("user", "").lower()
    if user != "kaustubh.keny":
        return redirect(url_for("index"))

    return render_template("config_editor.html", user=user) 

@app.route('/list-files/<year>')
def list_files(year):
    if not session.get('logged_in'):
        return not_logged_in_response()
    
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
    
    if not session.get('logged_in'):
        return not_logged_in_response()

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
    
    if not session.get('logged_in'):
        return not_logged_in_response()
    
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
    
    if not session.get('logged_in'):
        return not_logged_in_response()
    
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
    
    if not session.get('logged_in'):
        return not_logged_in_response()    
    data = request.get_json()
    year = data["year"]
    filename = data["filename"]

    file_path = os.path.join(CONFIG_BASE_PATH, str(year), filename)
    if not os.path.exists(file_path):
        return jsonify({"success": False, "error": "File not found"})

    os.remove(file_path)
    return jsonify({"success": True})

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

# --- run app ---
if __name__ == '__main__':
    
    host = "NCOG-LPT-TCH-32.Cogencis.com"
    port = 5000
    
    app.run(debug=True, host=host, port=port)
    # app.run(debug=True, host="127.0.0.1", port=5055)
