import os,json,sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.config_loader import load_config

path_config = load_config()

print(path_config["base_path"])
print(path_config["amc_path"])

print(path_config["configs"]['params'])

yus = os.path.join(path_config["base_path"],path_config["configs"]['params'])

print(yus)