import os, sys, json, time
# setup project root
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(root_dir)


from datetime import timedelta
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
from ldap3 import Server, Connection, ALL #type: ignore
from app.sqlconnect import establish_connection
from app.utils import Helper

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
    return render_template("dashboard.html", json_files=json_files, user=session.get("user"))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        username = request.form["username"].strip().lower()
        password = request.form["password"]
        remember = "remember" in request.form

        if ldap_authenticate(username, password):
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

@app.route('/upload', methods=['POST'])
def upload_files():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    uploaded_files = request.files.getlist('pdfs')
    os.makedirs(INPUT_DIR, exist_ok=True)
    
    total_size = 0

    for file in uploaded_files:
        if file and file.filename.lower().endswith(".pdf"):
            filename = secure_filename(file.filename)
            file.save(os.path.join(INPUT_DIR, filename))
            
            file.seek(0, os.SEEK_END)
            size = file.tell()
            file.seek(0)
            

    time.sleep(2)
    return redirect('/')


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
            SELECT file_name, start_time, end_time, status, json_path, error
            FROM holy_sheet
            ORDER BY start_time DESC
            LIMIT 20
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()
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


# --- run app ---
if __name__ == '__main__':
    app.run(debug=True)
