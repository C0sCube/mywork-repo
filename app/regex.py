import re , os

class Regex():
    
    def __init__(self):
        pass
    
    @staticmethod
    def extract_decimals(text:str):
        
        pattern = r'\b-?\d+(?:\.\d+)?\b'
        match = re.search(pattern,text)
        return float(match.group()) if match else "NA"