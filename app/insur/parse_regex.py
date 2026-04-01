import re, sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import random,string, inspect,datetime
from dateutil import parser #type:ignore
from datetime import datetime
from app.utils import Helper
from app.logger import log_exceptions
from app.konstant import get_registry, save_registry


class InstrRegex:
    
    def __init__(self, data):
        
        pass
    
    