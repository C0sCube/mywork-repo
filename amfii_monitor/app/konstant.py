import os,json,yaml #type: ignore
from datetime import datetime


root_dir = os.path.dirname(os.path.dirname(__file__))
path_dir = os.path.join(root_dir,r"paths.json")

def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
        
def load_yaml(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)




def get_root_dir():
    f = load_json(path_dir)
    return f["root"]

def get_output_dir():
    f = load_json(path_dir)
    return f["output"]

def get_log_dir():
    out_dir = get_output_dir()
    return os.path.join(out_dir,"log")

def get_raw_dir():
    out_dir = get_output_dir()
    return os.path.join(out_dir,"raw")

def get_adverse_kw_config():
    f = get_root_dir()
    yaml_path = os.path.join(f,"doc","controversy.yaml")
    return load_yaml(yaml_path)


def config_schedule():
    f = load_json(path_dir)
    return f["schl_data"]
   
def config_mail():
    f = load_json(path_dir)
    return f["mail_data"]

def config_program():
    conf_path = os.path.join(root_dir,"doc","config.json")
    return load_json(conf_path)
