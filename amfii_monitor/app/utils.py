import re
import os
import json
import time
import yaml #type:ignore
import json5
import random
import shutil
import string
import zipfile
import smtplib
import traceback
import unicodedata
from typing import List
from datetime import datetime, timedelta
import pandas as pd #type:ignore
# from email.mime.multipart import MIMEMultipart
# from email.mime.application import MIMEApplication
# from email.mime.text import MIMEText

from app.logger import get_global_logger

class Helper:
    
    def __init__(self):
        self.logger = get_global_logger()
        pass
    #PARSING UTILS
    def get_xlsx_in_folder(self,path:str, expected_file_name ="table_data.xlsx" ) -> dict:
        df = pd.DataFrame()
        for root,_,files in os.walk(path):
            for file_name in files:
                if file_name.endswith(".xlsx") and file_name.lower() == expected_file_name:
                    self.logger.info(f"Excel sheet containing table data found.")
                    full_path = os.path.join(root, file_name)
                    df = pd.read_excel(full_path)
                    return df
        # self.logger.warning(f"{expected_file_name} not found !! Returning empty df.")
        return df


    @staticmethod
    def copy_pdfs_to_folder(dest_folder: str, data):
        os.makedirs(dest_folder, exist_ok=True)

        if isinstance(data, dict):
            file_paths = list(data.values())
        elif isinstance(data, list):
            file_paths = data
        else:
            raise ValueError("Data must be a list of paths or a dict with path values")

        for path in file_paths:
            if not os.path.isfile(path):
                continue
            try:
                file_name = os.path.basename(path)
                dest_path = os.path.join(dest_folder, file_name)
                shutil.copy2(path, dest_path)
            except Exception as e:
                # logger = get_logger()
                # logger.error(f"Failed to copy '{path}' → {dest_folder}: {e}")
                pass
    
    @staticmethod
    def delete_files_and_empty_folder(file_path: str) -> bool:
        try:
            # print(file_path)
            if os.path.exists(file_path):
                os.remove(file_path)
                
                parent_dir = os.path.dirname(file_path)
                print("Remaining:", os.listdir(parent_dir))

                if os.path.isdir(parent_dir) and not os.listdir(parent_dir):
                    os.rmdir(parent_dir)
                return True
            return False
        except Exception as e:
            # logger = get_logger()
            # logger.exception(f"delete_file_and_empty_folder -> {e}")
            return False
        
    @staticmethod
    def delete_amc_pdf(data):
        try:
            for k, path in data.items():
                Helper.delete_files_and_empty_folder(path)
        except Exception as e:
            # logger = get_logger()
            # logger.exception(f"delete_amc_pdf: {e}")
            return
        return
    
    #JSON UN/LOAD 
    @staticmethod
    def save_json(data: dict,path: str):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        

    @staticmethod
    def load_json(path: str):
        with open(path, "r", encoding="utf-8") as f:
           return json.load(f)
        
    @staticmethod
    def save_json5(data: dict,path: str):
        with open(path, "w", encoding="utf-8") as f:
            json5.dump(data, f)

    @staticmethod
    def load_json5(path: str):
        with open(path, "r", encoding="utf-8") as f:
            return json5.load(f)
        
    # ---------------- NDJSON ---------------- #

    @staticmethod
    def save_ndjson(data: list, path: str):
        with open(path, "w", encoding="utf-8") as f:
            for row in data:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    @staticmethod
    def load_ndjson(path: str):
        rows = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        return rows

    # ---------------- YAML ---------------- #

    @staticmethod
    def save_yaml(data: dict, path: str):
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)

    @staticmethod
    def load_yaml(path: str):
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    
    @staticmethod
    def read_html(path: str) -> str:
        try:
            if not os.path.exists(path): return ""
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            print(f"Failed to read HTML file: {path} | {e}")
            return ""

    
    #WRITE TEXT
    @staticmethod
    def save_text(data,path:str,mode = 'w'):
        if not data:
            raise ValueError("Empty data cannot be saved.")
        if mode not in ('w', 'a'):
            raise ValueError(f"Invalid mode '{mode}'. Use 'w' or 'a'.")
        
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, mode, encoding='utf-8') as f:
            if isinstance(data, dict):
                # Write K-V Pair
                for k, v in data.items():
                    f.write(f"{k}:{v}\n")
            elif isinstance(data, list):
                # Write New Line
                for k in data:
                    f.write(f"{k}\n")
            elif isinstance(data, str):
                # Write Single String
                f.write(data)
            else:
                raise ValueError(f"Invalid data type: {type(data)}")
        
    @staticmethod        
    def create_dirs(root_path: str, dirs: list) -> list:
        created_paths = []
        for dir_name in dirs:
            full_path = os.path.join(root_path, dir_name)
            os.makedirs(full_path, exist_ok=True)
            created_paths.append(full_path)
        
        return created_paths if len(created_paths)>1 else created_paths[0]
    
    @staticmethod        
    def create_dir(root_path: str, *args) -> str:
        full_path = os.path.join(root_path, *args)
        os.makedirs(full_path, exist_ok=True)
        return full_path

    @staticmethod
    def create_path(path:str,*args)->str:
        return os.path.join(path, *args)

    @staticmethod
    def get_timestamp(sep=":"):
        now = datetime.now()
        return now.strftime(f"%H{sep}%M{sep}%S")
    
    #normal check
    @staticmethod
    def is_numeric(text):
        return bool(re.fullmatch(r'[+-]?(\d+(\.\d*)?|\.\d+)', text))

    @staticmethod
    def is_alphanumeric(text):
        return bool(re.fullmatch(r'[A-Za-z0-9]+', text))

    @staticmethod
    def is_alpha(text):
        return bool(re.fullmatch(r'[A-Za-z]+', text))
    
    #normal change
    @staticmethod
    def apply_sub(text, pattern, replacement='', ignore_case=True):
        if not isinstance(text, str):
            return text
        flags = re.IGNORECASE if ignore_case else 0
        return re.sub(pattern, replacement, text, flags=flags)
    
    @staticmethod
    def _remove_newline(text:str)->str:
        if not isinstance(text, str):
            return text
        return text.replace('\n', '')
    
    @staticmethod
    def _remove_tabspace(text:str)->str:
        if not isinstance(text, str):
            return text
        return text.replace('\t', '')
    
    @staticmethod
    def _remove_non_word_space_chars(text: str) -> str:
        if not isinstance(text, str):
            return text
        text = re.sub("[^\\w\\s]", "", text).strip()
        return text
    
    @staticmethod
    def normalize_unicode_via_nkfc(text:str)->str:
        if not isinstance(text,str):
            return text
        # Normalize Unicode
        return unicodedata.normalize("NFKC", text)

    
    @staticmethod
    def _normalize_whitespace(text: str) -> str:
        if not isinstance(text, str):
            return text
        return re.sub(r"\s+", " ", text).strip()
    
    @staticmethod
    def _normalize_date(text: str) -> str:
        if not isinstance(text, str):
            return text
        text = re.sub(r"[^A-Za-z0-9\s\.\/\,\-\\]+", " ", text).strip()
        return Helper._normalize_whitespace(text)
    
    @staticmethod
    def sanitize_Win_filename(name):
        # Replace illegal Windows characters with underscores
        return re.sub(r'[<>:"/\\|?*]', '_', name)

    
    @staticmethod
    def _normalize_alphanumeric(text: str) -> str:
        if not isinstance(text, str):
            return text
        text = re.sub(r"[^a-zA-Z0-9]+", " ", str(text))
        return re.sub(r"\s+", " ", text).strip().lower()
    
    @staticmethod
    def _normalize_alpha(text: str) -> str:
        if not isinstance(text, str):
            return text
        text = re.sub(r"[^a-zA-Z]+", " ", str(text))
        return re.sub(r"\s+", " ", text).strip().lower()

    @staticmethod
    def _normalize_numeric(text: str) -> str:
        if not isinstance(text, str):
            return text
        text = re.sub(r"[^0-9\.]+", " ", str(text))
        return re.sub(r"\s+", " ", text).strip().lower()
    
    @staticmethod
    def snake_case(text: str) -> str:
        text = re.sub(r'([A-Z]+)', r' \1', text).strip()
        return re.sub(r'[_\s-]+', '_', text).lower()

    @staticmethod
    def camel_case(text: str) -> str:
        text = re.sub(r'[_\s-]+', ' ', text)
        text = text.title()
        return text[0].lower() + text[1:].replace(' ', '')
     
    @staticmethod
    def fix_mojibake(text:str)->str:
        try:
            return text.encode("latin1").decode("utf-8")
        except:
            return text  # If it fails, return original


    def zip_folder(self,folder_path, zip_path):
        logger = get_global_logger()
        logger.info(f"Zipping folder: {folder_path} into {zip_path}")
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                file_count = 0
                for root, dirs, files in os.walk(folder_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, folder_path)
                        zipf.write(file_path, arcname)
                        file_count += 1
            logger.info(f"Zip file created: {zip_path}")
        except Exception as e:
            logger.error(f"Zipping Error: {type(e).__name__}: {e}")
            logger.debug(traceback.format_exc())

    def zip_file(file_path, zip_path):
        logger = get_global_logger()
        logger.info(f"Zipping file: {file_path} into {zip_path}")
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                arcname = os.path.basename(file_path)
                zipf.write(file_path, arcname)
            logger.info(f"Zip file created: {zip_path}")
        except Exception as e:
            logger.error(f"Zipping Error: {type(e).__name__}: {e}")
            logger.debug(traceback.format_exc())

    
    #file read/write   
    @staticmethod
    def read_file(filepath: str) -> str:
        with open(filepath, 'r') as f:
            return f.read()

    @staticmethod
    def write_file(filepath: str, content: str):
        with open(filepath, 'w') as f:
            f.write(content)
            
    @staticmethod
    def write_binary_file(filepath: str, binary_content: bytes):
        with open(filepath, 'wb') as f:
            f.write(binary_content)


    @staticmethod
    def get_file_extension(filename: str) -> str:
        return os.path.splitext(filename)[1]
    
    @staticmethod
    def chunk_list(data: list, size: int):
        return [data[i:i + size] for i in range(0, len(data), size)]

    @staticmethod
    def flatten_list(list_of_lists: list):
        return [item for sublist in list_of_lists for item in sublist]
    
    @staticmethod
    def remove_duplicates(data:list):
        return list(dict.fromkeys(data))
    
    
    #genrate
    def generate_uid(segment_count=3, segment_length=3):
        segments = [
            ''.join(random.choices(string.ascii_uppercase, k=segment_length))
            for _ in range(segment_count)
        ]
        return '-'.join(segments)


    def scheduler_loop(self, logger, run_fn, sch_days:list, sch_time:list):
        """
        Wraps the main() scraper function to run at specific times (HHMM format)
        and only on specified weekdays. times = ["0800", "1240", "1530"] run_days = ["mon", "tue", "wed", "thu", "fri"]
        
        """
        while True:
            now = datetime.now()
            weekday_str = now.strftime("%a").lower()

            # Skip non-run days (like weekends)
            if weekday_str not in sch_days:
                logger.info(f"Skipping today ({weekday_str.upper()}) — not in run days.")
                tomorrow = datetime.combine(now.date() + timedelta(days=1), datetime.min.time())
                wait_seconds = (tomorrow - now).total_seconds()
                time.sleep(wait_seconds)
                continue  # restart loop

            # --- Determine next scheduled run time ---
            today_times = [datetime.strptime(t, "%H%M").time() for t in sch_time]
            future_runs = [datetime.combine(now.date(), t) for t in today_times if datetime.combine(now.date(), t) > now]

            if future_runs:
                next_run = future_runs[0]
            else:
                # All times passed — find next valid run day
                next_day = now.date() + timedelta(days=1)
                while next_day.strftime("%a").lower() not in sch_days:
                    next_day += timedelta(days=1)
                next_run = datetime.combine(next_day, today_times[0])

            wait_seconds = (next_run - now).total_seconds()
            logger.info(f"Next Schdeuled Run @ {next_run.strftime('%d-%m-%y %H:%M')}. Waiting {int(wait_seconds)} seconds...")
            time.sleep(wait_seconds)

            # --- Execute scheduled run ---
            weekday_str = datetime.now().strftime("%a").lower()
            if weekday_str in sch_days:
                try:
                    logger.info("=" * 60)
                    logger.info(f"Running Schduled Program @ {datetime.now().strftime('%H:%M')} ({weekday_str.upper()})")

                    run_fn() #< -- function runs here
                    
                    logger.info(f"Completed Scheduled Run @ {datetime.now().strftime('%H:%M')}")
                except Exception as e:
                    logger.critical(f"Run failed: {type(e).__name__}: {e}")
                    
            else:
                logger.info(f"Skipped run because today ({weekday_str.upper()}) is not in run days.")
