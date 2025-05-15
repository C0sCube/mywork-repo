import os
import json

def get_project_root():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def load_config(filename="paths.json"):
    root = get_project_root()
    if not os.path.exists(root):
        raise FileNotFoundError(f"Root FNF: {root}")
    config_path = os.path.join(root, filename)
    with open(config_path, "r") as f:
        return json.load(f)
