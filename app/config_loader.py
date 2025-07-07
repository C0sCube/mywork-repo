import json
import json5  # type: ignore
from pathlib import Path

class Config:
    def __init__(self, config_path: str = "paths.json"):
        self._path = Path(config_path)
        if not self._path.exists():
            raise FileNotFoundError(f"Config file not found: {self._path}")

        with self._path.open("r", encoding="utf-8") as f:
            self._data = json5.load(f)

        self._params_cache = None
        self._sid_params_cache = None
        self._regex_cache = None
        self._sid_regex_cache = None

    def __getitem__(self, key):
        return self._data[key]

    @property
    def output(self) -> dict:
        return self._data.get("output", {})

    @property
    def output_path(self) -> str:
        return self._data.get("output_path", "")

    @property
    def watch_path(self) -> str:
        return self._data.get("amc_path", "")

    @property
    def params(self) -> dict:
        if self._params_cache is None:
            param_path = Path(self["base_path"]) / self["configs"]["params"]
            # print(f"[DEBUG] Loading params from: {param_path}")
            if not param_path.exists():
                raise FileNotFoundError(f"params.json5 not found at: {param_path}")
            with param_path.open("r", encoding="utf-8") as f:
                self._params_cache = json5.load(f)
        return self._params_cache

    @property
    def sid_params(self) -> dict:
        if self._sid_params_cache is None:
            param_path = Path(self["base_path"]) / self["configs"]["sid_params"]
            # print(f"[DEBUG] Loading sid_params from: {param_path}")
            if not param_path.exists():
                raise FileNotFoundError(f"sid_params.json5 not found at: {param_path}")
            with param_path.open("r", encoding="utf-8") as f:
                self._sid_params_cache = json5.load(f)
        return self._sid_params_cache

    @property
    def regex(self) -> dict:
        if self._regex_cache is None:
            regex_path = Path(self["base_path"]) / self["configs"]["regex"]
            # print(f"[DEBUG] Loading regex from: {regex_path}")
            if not regex_path.exists():
                raise FileNotFoundError(f"Regex config not found: {regex_path}")
            with regex_path.open("r", encoding="utf-8") as f:
                self._regex_cache = json5.load(f)
        return self._regex_cache

    @property
    def sid_regex(self) -> dict:
        if self._sid_regex_cache is None:
            regex_path = Path(self["base_path"]) / self["configs"]["sid_regex"]
            # print(f"[DEBUG] Loading sid_regex from: {regex_path}")
            if not regex_path.exists():
                raise FileNotFoundError(f"Sid Regex config not found: {regex_path}")
            with regex_path.open("r", encoding="utf-8") as f:
                self._sid_regex_cache = json5.load(f)
        return self._sid_regex_cache


_config_instance = None

def get_config():
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance