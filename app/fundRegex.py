import re
import os
import json
from dateutil import parser

class FundRegex():
    def __init__(self, path = r'C:\Users\Kaustubh.keny\OneDrive - Cogencis Information Services Ltd\Documents\mywork-repo\data\config\regex.json'):
        self.config_path = path
        self.regex_data = self.load_config()
        self.HEADER_PATTERNS = self.regex_data.get("header_patterns", {})
        self.STOP_WORDS = self.regex_data.get("stop_words", [])

    def load_config(self):
        """Load regex configuration from a JSON file."""
        if not os.path.exists(self.config_path):
            print(f"Config file not found: {self.config_path}")
            return {}
        try:
            with open(self.config_path, 'r') as file:
                return json.load(file)
        except Exception as e:
            print(f"Error loading config file: {e}")
            return {}

    @staticmethod
    def extract_date(text: str):
        try:
            return parser.parse(text).strftime(r"%y%m%d")
        except Exception as e:
            print(f"\n{e}")
            return text

    def header_mapper(self, text: str):
    
        for replacement, patterns in self.HEADER_PATTERNS.items():
            try:
                if isinstance(patterns, list):
                    for pattern in patterns:
                        if re.match(pattern, text, re.IGNORECASE):
                            return replacement
                else:
                    if re.match(patterns, text, re.IGNORECASE):
                        return replacement
            except Exception as e:
                print(f"\n{e}")
        return text
