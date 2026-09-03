import ast
import base64
import csv
import json
import os
import re
import shutil
import uuid
from datetime import datetime
from functools import wraps
from pathlib import Path

import json5
import pandas as pd
import pytz
from django.conf import settings
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt

# Existing parser/domain code is deliberately reused rather than duplicated.
from app.utils import Helper
from app.logger import setup_logger, rotate_daily_log
from app.sqlconnect import (
    create_job, fetch_job_by_name, fetch_job_by_id, establish_connection,
    can_transition, transition_job_state, is_pushable_state,
    increment_push_attempts, json_to_cog_db, get_job_states,
)
from app.konstant import (
    get_processed_dir, get_failed_dir, get_json_dir, get_report_dir,
    get_log_dir, FINAL_LOG_NAME, FINAL_WEB_LOG_NAME,
)

TIME_ZONE = pytz.timezone("Asia/Kolkata")
ROOT_DIR = Path(getattr(settings, "REPO_ROOT", settings.BASE_DIR))


def _load_runtime_config():
    cfg = getattr(settings, "PATHS", {}) or {}
    if not cfg:
        path = ROOT_DIR / "paths.json"
        if path.exists():
            try:
                cfg = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                cfg = {}
    return cfg


CONFIG = _load_runtime_config()
UTILS = Helper()

INPUT_DIR = CONFIG.get("inp_path", str(ROOT_DIR / "input"))
OUTPUT_DIR = CONFIG.get("out_path", str(ROOT_DIR / "output"))
WEB_DIR = CONFIG.get("web_path", str(ROOT_DIR / "web"))
CONFIG_PATH = str(Path(CONFIG.get("base_path", ROOT_DIR)) / "config")
REGISTRY_PATH = Path(CONFIG_PATH) / "0000" / "registry.json"
try:
    REGISTRY = UTILS.load_json(str(REGISTRY_PATH)) if REGISTRY_PATH.exists() else {}
except Exception:
    REGISTRY = {}

LDAP_CONFIG = CONFIG.get("ldap_config", {})
WEB_CONFIG = REGISTRY.get("config_web", {})
ADMIN_USERS = WEB_CONFIG.get("admin_user", [])
DB_CONFIG = CONFIG.get("db_config", {})
DB_TABLE = CONFIG.get("db_tables", {}).get("status_report", "mf_status_report")

try:
    logger = setup_logger(FINAL_WEB_LOG_NAME, base_dir=get_log_dir(), log_level=12, set_global=True)
except Exception:
    import logging
    logger = logging.getLogger("rep_fsparse.web")
    logging.basicConfig(level=logging.INFO)


def clean_filename(name):
    name = os.path.basename(name or "")
    name = re.sub(r"[^A-Za-z0-9._ -]", "_", name).strip()
    return name or "upload"


def detect_doc_type(filename):
    name = filename.lower()
    for suffix, kind in (("_fs", "fs"), ("_if", "if"), ("_sid", "sid"), ("_kim", "kim")):
        if name.endswith(suffix + ".csv") or name.endswith(suffix + ".json") or name.endswith(suffix + ".pdf"):
            return kind
    return None


def resolve_source_file(filename):
    sub = detect_doc_type(filename)
    if not sub:
        return None
    processed = Path(get_processed_dir(sub)) / filename
    failed = Path(get_failed_dir()) / filename
    if processed.exists():
        return str(processed.parent)
    if failed.exists():
        return str(failed.parent)
    return None


def _safe_join(base, filename):
    base = Path(base).resolve()
    target = (base / clean_filename(filename)).resolve()
    if target != base and base not in target.parents:
        raise ValueError("Invalid path")
    return target


def validate_json_for_push(json_path):
    path = Path(json_path)
    if not path.exists():
        return False, "JSON file not found"
    if path.stat().st_size == 0:
        return False, "JSON file is empty"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return False, "Invalid JSON format"
    if not data:
        return False, "JSON content is empty"
    return True, ""


def backup_json(json_path, tz=TIME_ZONE):
    path = Path(json_path)
    backup_dir = path.parent / "backup"
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(tz).strftime("%Y%m%d_%H%M%S")
    dst = backup_dir / f"{path.name}.{ts}.bak"
    shutil.copy2(path, dst)
    return str(dst)


def init_session_workspace(request):
    if request.session.get("ws_id"):
        return
    ws_id = uuid.uuid4().hex
    request.session["ws_id"] = ws_id
    base = Path(WEB_DIR) / "web_sessions" / ws_id
    for sub in ("conversion", "preview", "staging"):
        (base / sub).mkdir(parents=True, exist_ok=True)


def cleanup_session_workspace(request):
    ws_id = request.session.get("ws_id")
    if not ws_id:
        return
    shutil.rmtree(Path(WEB_DIR) / "web_sessions" / ws_id, ignore_errors=True)
    request.session.pop("ws_id", None)


def ws_path(request, kind):
    init_session_workspace(request)
    return Path(WEB_DIR) / "web_sessions" / request.session["ws_id"] / kind


def web_login_required(view=None, *, api=False):
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            if not request.session.get("logged_in"):
                if api:
                    return JsonResponse({"success": False, "error": "Unauthorized"}, status=401)
                return redirect("login")
            return func(request, *args, **kwargs)
        return wrapper
    return decorator(view) if view else decorator


def web_admin_required(view=None, *, api=False):
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            if not request.session.get("logged_in"):
                if api:
                    return JsonResponse({"success": False, "error": "Unauthorized"}, status=401)
                return redirect("login")
            if request.session.get("role") != "admin":
                if api:
                    return JsonResponse({"success": False, "error": "Forbidden"}, status=403)
                return redirect("dashboard")
            return func(request, *args, **kwargs)
        return wrapper
    return decorator(view) if view else decorator


def page_context(request, **extra):
    return {"user": request.session.get("user", "").lower(), "role": request.session.get("role", "user"), **extra}


@csrf_exempt
def login(request):
    rotate_daily_log(logger)
    if request.session.get("logged_in"):
        return redirect("dashboard")
    if request.method == "POST":
        username = request.POST.get("username", "").strip().lower()
        password = request.POST.get("password", "")
        if not username or not password:
            return render(request, "webapp/login.html", {"error": "Username and password required."})
        # Preserve current behaviour: authentication is a stub until LDAP is enabled.
        auth_success = True
        if not auth_success:
            return render(request, "webapp/login.html", {"error": "Invalid credentials."})
        request.session.flush()
        request.session["logged_in"] = True
        request.session["user"] = username
        request.session["role"] = "admin" if username in ADMIN_USERS else "user"
        request.session.set_expiry(7 * 24 * 60 * 60)
        init_session_workspace(request)
        logger.info("%s logged in", username)
        return redirect("dashboard")
    return render(request, "webapp/login.html")


@web_login_required
def logout(request):
    cleanup_session_workspace(request)
    request.session.flush()
    return redirect("login")


@web_login_required
def auth_check(request):
    return JsonResponse({"logged_in": bool(request.session.get("logged_in"))})


@web_login_required
def dashboard(request):
    json_dir = Path(get_json_dir())
    files = sorted((p.name for p in json_dir.iterdir()), reverse=True) if json_dir.exists() else []
    return render(request, "webapp/dashboard.html", page_context(request, json_files=files))


@web_login_required
def status_data(request):
    try:
        page = max(1, int(request.GET.get("page", 1)))
        size = min(100, max(1, int(request.GET.get("size", 25))))
        offset = (page - 1) * size
        conn = establish_connection(db_config=DB_CONFIG)
        cur = conn.cursor(dictionary=True)
        cur.execute(f"SELECT COUNT(*) AS total FROM {DB_TABLE}")
        total = cur.fetchone()["total"]
        cur.execute(f"""
            SELECT id, file_name, start_time, end_time, status, json_path, error,
                   created_by, uploaded_by, push_attempts
            FROM {DB_TABLE}
            ORDER BY start_time DESC
            LIMIT %s OFFSET %s
        """, (size, offset))
        rows = cur.fetchall()
        cur.close(); conn.close()
        return JsonResponse({"success": True, "rows": rows, "total": total, "page": page,
                             "size": size, "totalPages": (total + size - 1) // size})
    except Exception as exc:
        logger.exception("status_data error")
        return JsonResponse({"success": False, "rows": [], "error": str(exc)}, status=500)


@web_login_required(api=True)
def view_pdf(request, filename):
    filename = clean_filename(filename)
    pdf_dir = resolve_source_file(filename)
    if not pdf_dir:
        return JsonResponse({"success": False, "error": "PDF not found"}, status=404)
    path = _safe_join(pdf_dir, filename)
    if not path.exists():
        return JsonResponse({"success": False, "error": "PDF not found"}, status=404)
    return FileResponse(open(path, "rb"), content_type="application/pdf")


@web_login_required(api=True)
def dash_csv(request):
    filename = clean_filename(request.GET.get("file"))
    if not filename:
        return JsonResponse({"success": False, "error": "Missing File Name."}, status=400)
    json_path = _safe_join(get_json_dir(), filename)
    if not json_path.exists():
        return JsonResponse({"success": False, "error": "JSON not found"}, status=404)
    doc_type = detect_doc_type(filename)
    if not doc_type:
        return JsonResponse({"success": False, "error": "Unsupported JSON type"}, status=400)
    preview_dir = ws_path(request, "preview")
    converter = {"fs": json_to_csv, "sid": sid_to_csv, "kim": kim_to_csv, "if": if_to_csv}.get(doc_type)
    if not converter:
        return JsonResponse({"success": False, "error": "Unsupported JSON type"}, status=400)
    csv_path = converter(str(json_path), output_folder=str(preview_dir))
    return FileResponse(open(csv_path, "rb"), as_attachment=True, filename=Path(csv_path).name, content_type="text/csv")


@csrf_exempt
@web_login_required(api=True)
def apply_csv(request):
    job_id = request.POST.get("job_id")
    csv_file = request.FILES.get("csv")
    if not job_id or not csv_file:
        return JsonResponse({"success": False, "error": "Missing job_id or csv"}, status=400)
    try:
        job = fetch_job_by_id(int(job_id), DB_CONFIG)
        if not job:
            return JsonResponse({"success": False, "error": "Job not found"}, status=404)
        json_path = job.get("json_path")
        if not json_path or not Path(json_path).exists():
            return JsonResponse({"success": False, "error": "JSON not found"}, status=404)
        csv_path = _safe_join(ws_path(request, "conversion"), csv_file.name)
        with open(csv_path, "wb+") as dest:
            for chunk in csv_file.chunks(): dest.write(chunk)
        backup_path = backup_json(json_path)
        new_json = csv_to_fs_json(str(csv_path))
        Path(json_path).write_text(json.dumps(new_json, indent=2, ensure_ascii=False), encoding="utf-8")
        return JsonResponse({"success": True, "backup": backup_path, "json_path": json_path})
    except Exception as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=500)


@web_login_required
def download_dashboard_json(request, filename):
    path = _safe_join(get_json_dir(), filename)
    if not path.exists(): return HttpResponse("File not found", status=404)
    return FileResponse(open(path, "rb"), as_attachment=True, filename=path.name, content_type="application/json")


@csrf_exempt
@web_login_required(api=True)
def upload_files(request):
    files = request.FILES.getlist("pdfs")
    Path(INPUT_DIR).mkdir(parents=True, exist_ok=True)
    user = request.session.get("user", "unknown")
    now = datetime.now(TIME_ZONE).strftime("%Y-%m-%d %H:%M:%S")
    for f in files:
        if not f or not f.name.lower().endswith(".pdf"): continue
        name = clean_filename(f.name)
        with open(_safe_join(INPUT_DIR, name), "wb+") as dest:
            for chunk in f.chunks(): dest.write(chunk)
        create_job({"file_name": name, "start_time": now, "created_by": user, "uploaded_by": user}, DB_CONFIG)
    return JsonResponse({"success": True})


@csrf_exempt
@web_login_required(api=True)
def reprocess(request, job_id):
    try:
        JobState = get_job_states()
        job = fetch_job_by_id(job_id, DB_CONFIG)
        if not job: return JsonResponse({"success": False, "error": "Job not found"}, status=404)
        status, file_name = job["status"], job["file_name"]
        if not can_transition(status, JobState.UPLOADED):
            return JsonResponse({"success": False, "error": f"Cannot reprocess from {status}"}, status=400)
        src = resolve_source_file(file_name)
        if not src: return JsonResponse({"success": False, "error": "Source file not found"}, status=404)
        shutil.copy2(_safe_join(src, file_name), _safe_join(INPUT_DIR, file_name))
        transition_job_state(job_id=job_id, from_state=status, to_state=JobState.UPLOADED, error=None, db_config=DB_CONFIG)
        return JsonResponse({"success": True, "message": f"{file_name} reprocessing"})
    except Exception as exc:
        return JsonResponse({"success": False, "message": str(exc)}, status=500)


@csrf_exempt
@web_login_required(api=True)
def push_job(request, job_id):
    try:
        JobState = get_job_states()
        job = fetch_job_by_id(job_id, DB_CONFIG)
        if not job: return JsonResponse({"success": False, "error": "Job not found"}, status=404)
        status, json_path = job["status"], job.get("json_path")
        if not json_path or not Path(json_path).exists(): return JsonResponse({"success": False, "error": "JSON not found"}, status=404)
        if not is_pushable_state(status): return JsonResponse({"success": False, "error": f"Job not pushable in state {status}"}, status=400)
        increment_push_attempts(job_id, DB_CONFIG)
        success = json_to_cog_db(json_path, DB_CONFIG)
        next_state = JobState.PUSHED if success else JobState.PUSH_FAILED
        if can_transition(status, next_state):
            transition_job_state(job_id=job_id, from_state=status, to_state=next_state,
                                 error=None if success else "Admin panel push failed", db_config=DB_CONFIG)
        return JsonResponse({"success": bool(success)})
    except Exception as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=500)


@web_admin_required
def new_data(request): return render(request, "webapp/new_data.html", page_context(request))
@web_admin_required
def config_editor(request): return render(request, "webapp/config_editor.html", page_context(request))
@web_login_required
def csv_to_json(request): return render(request, "webapp/csv_to_json.html", page_context(request))
@web_login_required
def sid_data(request): return render(request, "webapp/sid_data.html", page_context(request))
@web_login_required
def daily_logs(request): return render(request, "webapp/daily_logs.html", page_context(request))
@web_login_required
def amc_data(request): return render(request, "webapp/amc_data.html", page_context(request))


@web_admin_required
def list_files(request, year):
    try:
        year_path = _safe_join(CONFIG_PATH, str(year))
        files = [p.name for p in year_path.iterdir() if p.suffix in (".json", ".json5")]
        return JsonResponse({"files": files})
    except Exception as exc:
        return JsonResponse({"files": [], "error": str(exc)})


@web_admin_required(api=True)
def get_years(request):
    try:
        folders = [p.name for p in Path(CONFIG_PATH).iterdir() if p.is_dir()]
        return JsonResponse(folders, safe=False)
    except Exception as exc:
        logger.exception("Error reading years")
        return JsonResponse([], safe=False)


def _json_body(request):
    try: return json.loads(request.body.decode("utf-8"))
    except Exception: return {}


@csrf_exempt
@web_admin_required(api=True)
def load_config(request):
    try:
        data = _json_body(request); year, filename = data.get("year"), data.get("filename")
        path = _safe_join(Path(CONFIG_PATH) / str(year), filename)
        raw = path.read_text(encoding="utf-8")
        parsed = json5.loads(raw) if filename.endswith(".json5") else json.loads(raw)
        return JsonResponse({"success": True, "data": parsed})
    except Exception as exc:
        return JsonResponse({"success": False, "error": str(exc)})


@csrf_exempt
@web_admin_required(api=True)
def save_config(request):
    try:
        data = _json_body(request); year, filename, content = data.get("year"), data.get("filename"), data.get("content", "")
        path = _safe_join(Path(CONFIG_PATH) / str(year), filename)
        parsed = json5.loads(content) if filename.endswith(".json5") else json.loads(content)
        path.write_text(json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8")
        return JsonResponse({"success": True})
    except Exception as exc:
        return JsonResponse({"success": False, "error": str(exc)})


@csrf_exempt
@web_admin_required(api=True)
def backup_config(request):
    try:
        data = _json_body(request); year, filename = data["year"], data["filename"]
        src = _safe_join(Path(CONFIG_PATH) / str(year), filename)
        if not src.exists(): return JsonResponse({"success": False, "message": "File not found"})
        ext = ".json" if filename.endswith("json") else ".json5"
        stem = filename[:-len(ext)]
        backup_name = f"{stem}_{year}bkp_{datetime.now(TIME_ZONE).strftime('%y%m%d_%H%M')}{ext}"
        backup_dir = Path(CONFIG_PATH) / "0001"; backup_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, backup_dir / backup_name)
        return JsonResponse({"success": True})
    except Exception as exc:
        return JsonResponse({"success": False, "error": str(exc)})


@csrf_exempt
@web_admin_required(api=True)
def create_config(request):
    try:
        data = _json_body(request); year, filename = data["year"], clean_filename(data["filename"])
        year_dir = Path(CONFIG_PATH) / str(year); year_dir.mkdir(parents=True, exist_ok=True)
        path = _safe_join(year_dir, filename)
        if path.exists(): return JsonResponse({"success": False, "error": "File already exists"})
        path.write_text("{}", encoding="utf-8")
        return JsonResponse({"success": True})
    except Exception as exc:
        return JsonResponse({"success": False, "error": str(exc)})


@csrf_exempt
@web_admin_required(api=True)
def delete_config(request):
    try:
        data = _json_body(request); path = _safe_join(Path(CONFIG_PATH) / str(data["year"]), data["filename"])
        if not path.exists(): return JsonResponse({"success": False, "error": "File not found"})
        path.unlink(); return JsonResponse({"success": True})
    except Exception as exc:
        return JsonResponse({"success": False, "error": str(exc)})


# ---------- CSV / JSON conversion functions ----------
def sid_to_csv(json_path, output_folder):
    json_path, output_folder = Path(json_path), Path(output_folder); output_folder.mkdir(parents=True, exist_ok=True)
    record = json.loads(json_path.read_text(encoding="utf-8")).get("value", {}) or {}
    csv_path = output_folder / f"{json_path.stem}.csv"
    def write_df(fh, df): df.to_csv(fh, index=False); fh.write("\n\n")
    with open(csv_path, "w", encoding="utf-8", newline="") as fh:
        kv = []
        for k in sorted(record.keys()):
            if k not in ("fund_manager", "load", "field_location"):
                v = record.get(k); v = " ".join(map(str, v)) if isinstance(v, (dict, list)) else v
                kv.append({"key": k, "value": v or ""})
            if k == "field_location": kv.append({"key": k, "value": str(record.get(k))})
        write_df(fh, pd.DataFrame(kv))
        if record.get("fund_manager"): write_df(fh, pd.DataFrame(record["fund_manager"]))
        if record.get("load"): write_df(fh, pd.DataFrame(record["load"]))
    return str(csv_path)


def _read_sections(csv_path):
    sections, cur = [], []
    with open(csv_path, "r", encoding="utf-8") as f:
        for row in csv.reader(f):
            if not any(cell.strip() for cell in row):
                if cur: sections.append(cur); cur = []
            else: cur.append(row)
    if cur: sections.append(cur)
    return sections


def csv_to_sid_json(csv_path):
    sections = _read_sections(csv_path); value = {}
    if sections:
        header, *rows = sections[0]; ki, vi = header.index("key"), header.index("value")
        for r in rows:
            k, v = r[ki].strip(), r[vi].strip()
            if k == "field_location" and v:
                try: v = ast.literal_eval(v)
                except Exception: pass
            value[k] = v
    for idx, key in ((1, "fund_manager"), (2, "load")):
        if len(sections) > idx:
            header, *rows = sections[idx]
            value[key] = [{h: r[i].strip() if i < len(r) else "" for i, h in enumerate(header) if h} for r in rows]
    return {"metadata": {"document_name": Path(csv_path).name, "file_type": "sid", "process_date": datetime.today().strftime("%Y%m%d")}, "value": dict(sorted(value.items()))}


def kim_to_csv(json_path, output_folder):
    json_path, output_folder = Path(json_path), Path(output_folder); output_folder.mkdir(parents=True, exist_ok=True)
    doc = json.loads(json_path.read_text(encoding="utf-8")); record = doc.get("records", [{}])[0].get("value", {}) or {}
    csv_path = output_folder / f"{json_path.stem}.csv"
    def write_df(fh, df): df.to_csv(fh, index=False); fh.write("\n\n")
    with open(csv_path, "w", encoding="utf-8", newline="") as fh:
        keys = ["amc_name", "main_scheme_name", "mutual_fund_name", "description", "field_location"]
        write_df(fh, pd.DataFrame([{"key": k, "value": str(record.get(k, ""))} for k in keys]))
        rows = []
        for item in record.get("asset_allocation_pattern", []):
            row = {"instrument_type": item.get("instrument_type", ""), "risk_profile": item.get("risk_profile", ""), "min": "", "max": "", "total": ""}
            for a in item.get("allocation", []): row[a.get("type")] = a.get("value", "")
            rows.append(row)
        if rows: write_df(fh, pd.DataFrame(rows))
    return str(csv_path)


def csv_to_kim_json(csv_path):
    sections = _read_sections(csv_path); value = {}
    if sections:
        header, *rows = sections[0]; ki, vi = header.index("key"), header.index("value")
        for r in rows:
            k, v = r[ki].strip(), r[vi].strip()
            if k == "field_location" and v:
                try: v = ast.literal_eval(v)
                except Exception: v = []
            value[k] = v
    if len(sections) > 1:
        header, *rows = sections[1]
        value["asset_allocation_pattern"] = [{"instrument_type": r[header.index("instrument_type")] if "instrument_type" in header else "",
            "risk_profile": r[header.index("risk_profile")] if "risk_profile" in header else "",
            "allocation": [{"type": k, "value": r[header.index(k)] if k in header and header.index(k) < len(r) else ""} for k in ("min", "max", "total")] } for r in rows]
    return {"metadata": {"document_name": Path(csv_path).name, "file_type": "kim", "process_date": datetime.today().strftime("%Y%m%d")}, "records": [{"value": dict(sorted(value.items()))}]}


def json_to_csv(json_path, output_folder):
    json_path, output_folder = Path(json_path), Path(output_folder); output_folder.mkdir(parents=True, exist_ok=True)
    keys = REGISTRY["field_keys"]; static_keys, load_keys, metric_keys, manager_keys, field_location = keys["static_keys"], keys["load_keys"], keys["metric_keys"], keys["manager_keys"], keys["field_location"]
    records = json.loads(json_path.read_text(encoding="utf-8")).get("records", [])
    max_mgr = max((len(r["value"].get("fund_manager", [])) for r in records), default=1)
    headers = static_keys + load_keys + metric_keys + [f"{k}_{i}" for i in range(1, max_mgr + 1) for k in manager_keys] + [field_location]
    rows = []
    for r in records:
        v = r["value"]; row = [v.get(k, "") for k in static_keys]; entry = exit_ = ""
        for l in v.get("load", []):
            if l["type"] == "entry": entry = l["comment"]
            elif l["type"] == "exit": exit_ = l["comment"]
        row += [entry, exit_]; metric_map = {m["name"]: m["value"] for m in v.get("metrics", [])}; row += [metric_map.get(k, "") for k in metric_keys]
        mgrs = v.get("fund_manager", [])
        for i in range(max_mgr): row += ([mgrs[i].get(k, "") for k in manager_keys] if i < len(mgrs) else [""] * len(manager_keys))
        fl = v.get("field_location", []); row.append(json.dumps(fl[0]) if fl else ""); rows.append(row)
    csv_path = output_folder / f"{json_path.stem}.csv"; pd.DataFrame(rows, columns=headers).to_csv(csv_path, index=False); return str(csv_path)


def csv_to_fs_json(csv_path):
    df = pd.read_csv(csv_path, dtype=str, encoding="utf-8", encoding_errors="replace").fillna(""); keys = REGISTRY["field_keys"]; records = []
    for _, row in df.iterrows():
        value = {k: row[k] for k in keys["static_keys"] if k in row and row[k]}
        loads = ([{"type": "entry", "comment": row["entry"]}] if row.get("entry") else []) + ([{"type": "exit", "comment": row["exit"]}] if row.get("exit") else [])
        if loads: value["load"] = loads
        metrics = [{"name": k, "value": row[k]} for k in keys["metric_keys"] if row.get(k)];
        if metrics: value["metrics"] = metrics
        managers = []; i = 1
        while f"name_{i}" in df.columns:
            fm = {k: row[f"{k}_{i}"] for k in keys["manager_keys"] if row.get(f"{k}_{i}")}
            if fm: managers.append(fm)
            i += 1
        if managers: value["fund_manager"] = managers
        if row.get(keys["field_location"]):
            try: value["field_location"] = [json.loads(row[keys["field_location"]])]
            except Exception: pass
        records.append({"value": dict(sorted(value.items()))})
    return {"metadata": {"document_name": Path(csv_path).with_suffix(".pdf").name, "file_type": "fs", "process_date": datetime.now().strftime("%Y%m%d")}, "records": records}


def if_to_csv(json_path, output_folder):
    json_path, output_folder = Path(json_path), Path(output_folder); output_folder.mkdir(parents=True, exist_ok=True)
    keys = REGISTRY["field_keys"]["if_keys"]; headers = keys["static_keys"] + keys["portfolio_keys"]; rows = []
    records = json.loads(json_path.read_text(encoding="utf-8")).get("records", [])
    for r in records:
        v = r.get("value", {}); static_values = [v.get(k, "") for k in keys["static_keys"]]; portfolio_list = v.get("portfolio_data", [])
        if not isinstance(portfolio_list, list): continue
        rows.extend([static_values + [item.get(k, "") for k in keys["portfolio_keys"]] for item in portfolio_list]); rows += [[""] * len(headers), [""] * len(headers)]
    csv_path = output_folder / f"{json_path.stem}.csv"; pd.DataFrame(rows, columns=headers).to_csv(csv_path, index=False); return str(csv_path)


@csrf_exempt
@web_login_required(api=True)
def convert_csv(request):
    init_session_workspace(request); f = request.FILES.get("csv")
    if not f: return JsonResponse({"success": False, "error": "No CSV uploaded"}, status=400)
    filename, doc_type = clean_filename(f.name), detect_doc_type(f.name)
    if not doc_type: return JsonResponse({"success": False, "error": "Unsupported CSV type"}, status=400)
    csv_path = _safe_join(ws_path(request, "conversion"), filename)
    with open(csv_path, "wb+") as dest:
        for chunk in f.chunks(): dest.write(chunk)
    converter = {"fs": csv_to_fs_json, "sid": csv_to_sid_json, "kim": csv_to_kim_json}.get(doc_type)
    if not converter: return JsonResponse({"success": False, "error": "Unsupported CSV type"}, status=400)
    json_data = converter(str(csv_path)); json_name = Path(filename).with_suffix(".json").name; json_path = _safe_join(ws_path(request, "staging"), json_name)
    json_path.write_text(json.dumps(json_data, indent=2, ensure_ascii=False), encoding="utf-8")
    return JsonResponse({"success": True, "json_file": json_name})


@csrf_exempt
@web_login_required(api=True)
def convert_json(request):
    init_session_workspace(request); f = request.FILES.get("json")
    if not f: return JsonResponse({"success": False, "error": "No JSON uploaded"}, status=400)
    filename, doc_type = clean_filename(f.name), detect_doc_type(f.name)
    if not doc_type: return JsonResponse({"success": False, "error": "Unsupported JSON type"}, status=400)
    json_path = _safe_join(ws_path(request, "conversion"), filename)
    with open(json_path, "wb+") as dest:
        for chunk in f.chunks(): dest.write(chunk)
    converter = {"fs": json_to_csv, "sid": sid_to_csv, "kim": kim_to_csv, "if": if_to_csv}.get(doc_type)
    if not converter: return JsonResponse({"success": False, "error": "Unsupported JSON type"}, status=400)
    csv_path = converter(str(json_path), output_folder=str(ws_path(request, "preview")))
    return JsonResponse({"success": True, "csv_file": Path(csv_path).name})


@web_login_required
def download_csv(request, filename):
    path = _safe_join(ws_path(request, "preview"), filename)
    if not path.exists(): return HttpResponse("File not found", status=404)
    return FileResponse(open(path, "rb"), as_attachment=True, filename=path.name, content_type="text/csv")


@web_login_required
def download_pipeline_json(request, filename):
    path = _safe_join(ws_path(request, "staging"), filename)
    if not path.exists(): return HttpResponse("File not found", status=404)
    return FileResponse(open(path, "rb"), as_attachment=True, filename=path.name, content_type="application/json")


@csrf_exempt
@web_login_required(api=True)
def cleanup_pipeline(request):
    cleanup_session_workspace(request); init_session_workspace(request); return JsonResponse({"success": True})


@web_login_required
def view_json(request, source, filename):
    base = get_json_dir() if source == "dashboard" else ws_path(request, "staging") if source == "csv" else None
    if base is None: return JsonResponse({"success": False, "error": "Invalid source"}, status=400)
    path = _safe_join(base, filename)
    if not path.exists(): return HttpResponse("File not found", status=404)
    return FileResponse(open(path, "rb"), content_type="application/json")


def ensure_job_for_json(request, pdf_name):
    JobState = get_job_states(); row = fetch_job_by_name(pdf_name, DB_CONFIG)
    if row: return row["id"], row["status"]
    user = request.session.get("user", "unknown"); now = datetime.now(TIME_ZONE).strftime("%Y-%m-%d %H:%M:%S")
    job_id = create_job({"file_name": pdf_name, "start_time": now, "created_by": user, "uploaded_by": user}, DB_CONFIG)
    return job_id, JobState.SP_CALL


def push_json_and_record(job_id, from_state, json_path):
    JobState = get_job_states()
    try:
        json_to_cog_db(json_path, DB_CONFIG); transition_job_state(job_id=job_id, from_state=from_state, to_state=JobState.PUSHED, error=None, db_config=DB_CONFIG)
    except Exception:
        logger.exception("Job PUSH_FAILED during SP call")
        transition_job_state(job_id=job_id, from_state=from_state, to_state=JobState.PUSH_FAILED, error="Push Job Failed. Chk Log.", db_config=DB_CONFIG); raise


@csrf_exempt
@web_login_required(api=True)
def push_json_sp(request):
    init_session_workspace(request)
    if "json" in request.FILES:
        f = request.FILES["json"]; file_name = clean_filename(f.name); json_path = _safe_join(ws_path(request, "staging"), file_name)
        with open(json_path, "wb+") as dest:
            for chunk in f.chunks(): dest.write(chunk)
    elif "json_name" in request.POST:
        file_name = clean_filename(request.POST["json_name"]); json_path = _safe_join(ws_path(request, "staging"), file_name)
        if not json_path.exists(): return JsonResponse({"success": False, "error": "JSON file not found"}, status=404)
    else: return JsonResponse({"success": False, "error": "No JSON data provided"}, status=400)
    valid, msg = validate_json_for_push(str(json_path))
    if not valid: return JsonResponse({"success": False, "error": msg}, status=400)
    pdf_name = Path(file_name).with_suffix(".pdf").name; job_id, status = ensure_job_for_json(request, pdf_name)
    if not is_pushable_state(status): return JsonResponse({"success": False, "error": f"Job not pushable in state {status}"}, status=400)
    try: push_json_and_record(job_id, status, str(json_path)); return JsonResponse({"success": True})
    except Exception as exc: return JsonResponse({"success": False, "error": str(exc)}, status=500)


@csrf_exempt
@web_login_required(api=True)
def upload_sid_kim(request):
    pdf, meta_raw = request.FILES.get("pdf"), request.POST.get("meta")
    if not pdf or not meta_raw: return JsonResponse({"success": False, "error": "Missing PDF or meta"}, status=400)
    try: meta = json.loads(meta_raw)
    except Exception: return JsonResponse({"success": False, "error": "Invalid meta JSON"}, status=400)
    filename = clean_filename(pdf.name)
    if not (filename.lower().endswith("_sid.pdf") or filename.lower().endswith("_kim.pdf")):
        return JsonResponse({"success": False, "error": "Filename must end with _SID.pdf or _KIM.pdf"}, status=400)
    try:
        Path(INPUT_DIR).mkdir(parents=True, exist_ok=True); pdf_path = _safe_join(INPUT_DIR, filename); meta_path = pdf_path.with_suffix(".meta.json")
        with open(pdf_path, "wb+") as dest:
            for chunk in pdf.chunks(): dest.write(chunk)
        UTILS.save_json(meta, str(meta_path)); user = request.session.get("user", "unknown"); now = datetime.now(TIME_ZONE).strftime("%Y-%m-%d %H:%M:%S")
        create_job({"file_name": filename, "start_time": now, "created_by": user, "uploaded_by": user}, DB_CONFIG)
        return JsonResponse({"success": True})
    except Exception as exc: return JsonResponse({"success": False, "error": str(exc)}, status=500)


@csrf_exempt
@web_login_required(api=True)
def load_daily_log(request):
    data = _json_body(request); date = data.get("date"); log_select = data.get("logSelect")
    if not date: return JsonResponse({"success": False, "error": "Missing date"}, status=400)
    try: datetime.strptime(date, "%Y-%m-%d")
    except ValueError: return JsonResponse({"success": False, "error": "Invalid date format"}, status=400)
    log_name = FINAL_WEB_LOG_NAME if log_select != "fslog" else FINAL_LOG_NAME; log_file = Path(get_log_dir()) / date / f"{log_name}.log"
    if not log_file.exists(): return JsonResponse({"success": False, "content": "No logs for this date."})
    try: return JsonResponse({"success": True, "content": log_file.read_text(encoding="utf-8", errors="ignore")})
    except Exception: return JsonResponse({"success": False, "content": "Error reading log file."}, status=500)


@web_login_required
def list_json_files(request):
    directory = Path(get_json_dir()); files = sorted(p.name for p in directory.iterdir()) if directory.exists() else []
    return render(request, "webapp/file_list.html", {"title": "JSON Files", "files": files, "kind": "json"})


@web_login_required
def list_csv_files(request):
    directory = Path(get_report_dir()); files = sorted(p.name for p in directory.iterdir()) if directory.exists() else []
    return render(request, "webapp/file_list.html", {"title": "Reports", "files": files, "kind": "xlsx"})


@web_login_required
def serve_csv_files(request, filename):
    path = _safe_join(get_report_dir(), filename)
    if not path.exists(): return HttpResponse("File not found", status=404)
    return FileResponse(open(path, "rb"), content_type="application/octet-stream")


@web_login_required
def serve_json_files(request, filename):
    path = _safe_join(get_json_dir(), filename)
    if not path.exists(): return HttpResponse("File not found", status=404)
    return FileResponse(open(path, "rb"), content_type="application/json")


@web_login_required(api=True)
def company_registry(request):
    return JsonResponse({k: v.get("amc_name", "") for k, v in REGISTRY.get("amc_registry", {}).items()})


@web_login_required(api=True)
def amc_data_registry(request): return JsonResponse(REGISTRY.get("amc_registry", {}))

@web_login_required(api=True)
def json_list(request):
    directory = Path(get_json_dir()); files = sorted((p.name for p in directory.iterdir()), reverse=True) if directory.exists() else []
    return JsonResponse({"files": files[:20]})

@web_login_required(api=True)
def get_logo(request, logo_id):
    b64 = REGISTRY.get("z_logos", {}).get(str(logo_id), "")
    if not b64: return JsonResponse({"error": "Logo not found"}, status=404)
    return HttpResponse(base64.b64decode(b64), content_type="image/png")
