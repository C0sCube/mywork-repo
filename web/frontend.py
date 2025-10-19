from flask import Flask, render_template, request, redirect, send_from_directory #type: ignore
import os, sys
from werkzeug.utils import secure_filename
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.konstant import *

app = Flask(__name__)

@app.route('/')
def index():
    json_dir = os.path.join(OUTPUT_PATH, "json")
    json_files = os.listdir(json_dir)
    return render_template("dashboard.html", json_files=json_files)



@app.route('/upload', methods=['POST'])
def upload_files():
    uploaded_files = request.files.getlist('pdfs')
    os.makedirs(INPUT_PATH, exist_ok=True)
    for file in uploaded_files:
        if file and file.filename.lower().endswith(".pdf"):
            filename = secure_filename(file.filename)
            file.save(os.path.join(INPUT_PATH, filename))

    return redirect('/')

@app.route('/json/<filename>')
def get_json(filename):
    return send_from_directory(os.path.join(OUTPUT_PATH, "json"), filename)

@app.route('/logs')
def logs():
    log_dir = os.path.join(app.root_path, 'static', 'logs')
    log_files = os.listdir(log_dir) if os.path.exists(log_dir) else []
    log_files.sort(reverse=True)

    return render_template('logs.html', log_files=log_files)


if __name__ == '__main__':
    app.run(debug=True)
