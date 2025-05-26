import os, re, math, json, inspect,sys, ocrmypdf # type: ignore
import fitz # type: ignore
from collections import defaultdict

from app.parse_regex import *
from app.fund_data import *
from logging_config import *
from app.vendor_to_user import *
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.config_loader import *

conf = get_config() #path to paths.json


class ReaderSIDKIM:
    def __init__(self):
        pass
    
    
    