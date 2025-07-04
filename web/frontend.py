from flask import Flask, render_template, request, redirect, send_from_directory #type: ignore
import os, sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.config_loader import get_config,load_config_once

app = Flask(__name__)
load_config_once(output_folder=None)
CONFIG = get_config()

INPUT_DIR = CONFIG["amc_path"]
OUTPUT_DIR = CONFIG["output_path"]

@app.route('/')
def index():
    json_dir = os.path.join(OUTPUT_DIR, "json")
    json_files = os.listdir(json_dir)
    return render_template("dashboard.html", json_files=json_files)

@app.route('/upload', methods=['POST'])
def upload_files():
    folder_name = request.form['foldername']
    uploaded_files = request.files.getlist('pdfs')

    target_dir = os.path.join(INPUT_DIR, folder_name)
    os.makedirs(target_dir, exist_ok=True)

    for file in uploaded_files:
        if file and file.filename.endswith(".pdf"):
            file.save(os.path.join(target_dir, file.filename))

    return redirect('/')

@app.route('/json/<filename>')
def get_json(filename):
    return send_from_directory(os.path.join(OUTPUT_DIR, "json"), filename)

@app.route('/logs')
def logs():
    log_dir = os.path.join(app.root_path, 'static', 'logs')
    log_files = os.listdir(log_dir) if os.path.exists(log_dir) else []
    log_files.sort(reverse=True)

    return render_template('logs.html', log_files=log_files)


if __name__ == '__main__':
    app.run(debug=True)
