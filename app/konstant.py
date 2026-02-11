
import json,json5,os, sys

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(root_dir)

path_path = os.path.join(root_dir, r"paths.json")

def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
    
def load_json5(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json5.load(f)
    
def save_json(data: dict, path: str, indent: int = 2):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent)

def save_json5(data: dict, path: str, indent: int = 2):
    with open(path, "w", encoding="utf-8") as f:
        json5.dump(data, f, indent=indent)

def load_json_as_string(path: str, indent: int = None) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return json.dumps(json.load(f), indent=indent, ensure_ascii=False)

def load_json5_as_string(path: str, indent: int = None) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return json5.dumps(json5.load(f), indent=indent)
        
def create_dir(base_path, *folders):
    dir_path = os.path.join(base_path, *folders)
    os.makedirs(dir_path, exist_ok=True)
    return dir_path


def load_paths(): return load_json(path_path)
def get_output_path(): return load_paths()["out_path"]
def get_input_path(): return load_paths()["inp_path"]

#global registry
def get_registry():
    base_path = load_paths()["base_path"]
    base_path = os.path.join(base_path,"config","0000","registry.json")
    if not os.path.exists(base_path):
        return None
    return load_json(base_path)

def save_registry(key:str, data):
    base_path = load_paths()["base_path"]
    base_path = os.path.join(base_path,"config","0000","registry.json")
    if not os.path.exists(base_path):
        return None
    
    registry = load_json(base_path)
    if key not in registry:
        print(f"{key} not found in registry. Cannot Save.")
        return
    
    registry.update({
        key:data
    })
    
    save_json(registry, base_path)
    
# factsheet conf
def get_config(year = "2025", id = ""):
    base_path = load_paths()["base_path"]
    config_path = os.path.join(base_path,"config",year, f"{id}_AMC.json5")
    print(config_path)
    if not os.path.exists(config_path):
        return None
    return load_json5(config_path)

def get_regex(year = "2025"):
    base_path = load_paths()["base_path"]
    config_path = os.path.join(base_path,"config", year, f"regex_{year}.json")
    if not os.path.exists(config_path):
        return None
    return load_json(config_path)

#sid/kim conf
def get_sidkim_config(folder = "sidkim"):
    base_path = load_paths()["base_path"]
    config_path = os.path.join(base_path, "config", folder, f"sid_params.json5")
    if not os.path.exists(config_path):
        return None
    config =  load_json5(config_path)
    return config

def load_sidkimregex():
    base_path = load_paths()["base_path"]
    sid_path = os.path.join(base_path,"config", "sidkim","sid_regex.json")
    return load_json(sid_path)


def load_db_config():
    f = load_paths()
    return f["db_config"]

def load_mail_data():
    f = load_paths()
    return f["mail_data"]

def get_processed_dir(sub):
    out_dir = get_output_path()
    return create_dir(out_dir,"processed",sub)

def get_failed_dir():
    out_dir = get_output_path()
    return create_dir(out_dir,"failed")

def get_json_dir():
    out_dir = get_output_path()
    return create_dir(out_dir,"json")

def get_report_dir():
    out_dir = get_output_path()
    return create_dir(out_dir,"reports")

def get_log_dir():
    out_dir = get_output_path()
    return create_dir(out_dir,"logs")


#pdf generation constants
# TITLE_FONT_SIZE = 24
# TITLE_POSITION = 72
# TITLE_COLOR = (0, 0, 1)
# DEFAULT_FONT_NAME = "helv"
# DEFAULT_FONT_SIZE = 10
# DEFAULT_FONT_COLOR = (0, 0, 0)  # black
# LEFT_MARGIN = 32        # Left margin for alignment
# MIN_LINE_SPACING = 2     # Extra space between lines
# Y_SNAP_THRESHOLD = 3     # If two words are within 3 units, snap to same Y

#log data

FINAL_LOG_NAME = "fs_parse_log"