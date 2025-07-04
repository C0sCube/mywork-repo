import os
import json

_config = None
_original_config = None
_config_path = None

def get_project_root():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def load_config_once(filename="paths.json", output_folder=None):
    global _config, _original_config, _config_path

    if _config is not None:
        print("Config already loaded. Skipping re-initialization.")
        return _config  # Return cached config if already loaded

    root = get_project_root()
    _config_path = os.path.join(root, filename)

    if not os.path.exists(_config_path):
        raise FileNotFoundError(f"Config file not found: {_config_path}")

    with open(_config_path, "r") as f:
        _original_config = json.load(f)
        _config = json.loads(json.dumps(_original_config))  # Deep copy

    if output_folder:
        output_base = os.path.join(_config["output_path"], output_folder)
        os.makedirs(output_base, exist_ok=True)

        for key, val in _config.get("output", {}).items():
            basename = os.path.basename(val)
            _config["output"][key] = os.path.join(output_folder, basename)

    print(f"Loaded config with output_folder = {output_folder}")
    return _config

def get_config():
    if _config is None:
        raise RuntimeError("Config not loaded. Call load_config_once() first.")
    return _config

def restore_config():
    global _original_config, _config_path
    if _original_config and _config_path:
        with open(_config_path, "w") as f:
            json.dump(_original_config, f, indent=4)
        # logger.info("Restored original 'paths.json'")
