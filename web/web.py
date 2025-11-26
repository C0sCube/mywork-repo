import os, sys, json, time, json5
# setup project root
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(root_dir)


from datetime import timedelta, datetime
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

# inside web.py (edit upload_files route)
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
                "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            try:
                meta_path = os.path.splitext(file_path)[0] + ".meta.json"
                # print(meta_path)
                with open(meta_path, "w", encoding="utf-8") as mf:
                    json.dump(meta, mf)
            except Exception as e:
                print(f"Failed to write meta for {filename}: {e}")

            # insert initial DB row via update_table (so dashboard shows file immediately)
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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

@app.route('/status_data')
def status_data():
    """Return latest entries from holy_sheet as JSON for dashboard polling."""
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    try:
        conn = establish_connection(db_config=DB_CONFIG)
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT file_name, start_time, end_time, status,json_path, error, uploaded_by
            FROM mf_status_report
            ORDER BY start_time DESC
            LIMIT 30
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        # print(rows)
        return {"success": True, "rows": rows}
    except Exception as e:
        print("status_data error:", e)
        return {"success": False, "rows": []}

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

@app.route('/list-files/<int:year>')
def list_files(year):
    year_path = os.path.join(CONFIG_BASE_PATH, str(year))
    try:
        files = [f for f in os.listdir(year_path) if (f.endswith('.json') or  f.endswith('.json5'))]
        return jsonify({"files": files})
    except Exception as e:
        return jsonify({"files": [], "error": str(e)})
    
@app.route('/load-config', methods=['POST'])
def load_config():
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
  
@app.route('/backup-config', methods=['POST'])
def backup_config():
    data = request.get_json()
    year = data.get('year')
    filename = data.get('filename')

    print(f"Backup requested for {year}/{filename}")
    return jsonify({"success": True, "message": "Backup triggered"})



#logs
@app.route('/daily-log')
def daily_logs():
    if not session.get("logged_in"):
        return redirect(url_for("login")) 

    user = session.get("user", "").lower()
    if user != "kaustubh.keny":
        return redirect(url_for("index"))

    return render_template("daily_logs.html", user=user) 

# --- run app ---
if __name__ == '__main__':
    
    host = "NCOG-LPT-TCH-32.Cogencis.com"
    port = 5000
    
    app.run(debug=True, host=host, port=port)
