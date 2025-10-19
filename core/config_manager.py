# core/config_manager.py
import os, json, json5
from functools import lru_cache

class ConfigManager:
    def __init__(self, base_path="config"):
        self.base_path = base_path

    @lru_cache(maxsize=None)
    def load(self, filename):
        path = os.path.join(self.base_path, filename)
        if filename.endswith(".json5"):
            with open(path, "r", encoding="utf-8") as f:
                return json5.load(f)
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get(self, key, file="parameters.json5"):
        data = self.load(file)
        return data.get(key, None)

    def reload(self, filename):
        self.load.cache_clear()
        return self.load(filename)
