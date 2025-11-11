import os, re, json, string, shutil, json5
import fitz #type:ignore
from datetime import datetime
from collections import defaultdict
import pandas as pd #type:ignore
from typing import List
from app.logger import get_global_logger

class Helper:
    def __init__(self):
        self.logger = get_global_logger()

        pass
    #PARSING UTILS
    def get_pdf_with_id(self,path: str) -> dict:
        pdf_paths = defaultdict(list)

        for root, _ , files in os.walk(path):
            for file_name in files:
                if file_name.endswith("FS.pdf"):
                    self.logger.info(f"Factsheet Found: {file_name}")
                    full_path = os.path.join(root, file_name)
                    parts = file_name.split("_")
                    fund_id = parts[0]

                    is_passive = len(parts[-2]) == 1 #determine passive
                    suffix = parts[-2] if is_passive else "0"
                    fund_key = f"{fund_id}_{suffix}"
                    
                    # print(fund_key)
                    pdf_paths[fund_key].append((file_name, full_path))
                elif file_name.endswith("KIM.pdf") or file_name.endswith("SID.pdf"):
                    full_path = os.path.join(root, file_name)
                    # folder_name = os.path.basename(root).title()

                    parts = file_name.split("_")
                    fund_id = parts[0]
                    typez = parts[-1].replace(".pdf","").upper()
                    pdf_paths[fund_id].append((typez,file_name, full_path))
                else:
                    self.logger.info(f"File: {file_name} is neither a factsheet nor a SID/KIM document.")
        return pdf_paths
    
    @staticmethod
    def get_pdf_paths(base_path: str) -> dict:
        pdf_paths = {}
        suffix_map = {}
        for root, _, files in os.walk(base_path):
            folder_name = os.path.basename(root).title()

            for file_name in files:
                if file_name.lower().endswith(".pdf"):
                    full_path = os.path.join(root, file_name)
                    key = folder_name

                    if key in pdf_paths:
                        suffix = string.ascii_uppercase[suffix_map[key]]
                        key = f"{folder_name}_{suffix}"
                        suffix_map[folder_name] += 1
                    else:
                        suffix_map[folder_name] = 1

                    pdf_paths[key] = full_path
        return pdf_paths

    @staticmethod
    def get_amc_paths(base_path: str) -> dict:
        """Returns a mapping of fund keys to (fund name, file path) for all FS.pdf files in a directory."""
        fund_paths = {}
        # logger = get_logger()
        # logger.info(f"AMC At: {base_path}")
        for root, _, files in os.walk(base_path):
            # print(files)
            for file_name in files:
                if file_name.endswith("FS.pdf"):
                    # print(file_name)
                    full_path = os.path.join(root, file_name)
                    folder_name = os.path.basename(root).title()

                    parts = file_name.split("_")
                    fund_id = parts[0]

                    is_passive = len(parts[-2]) == 1 #determine passive
                    suffix = parts[-2] if is_passive else "0"
                    fund_key = f"{fund_id}_{suffix}"
                    fund_name = f"{folder_name} Passive" if is_passive else folder_name

                    # print(fund_name)
                    fund_paths[fund_key] = (fund_name, full_path)

                elif file_name.endswith("KIM.pdf") or file_name.endswith("SID.pdf"):
                    full_path = os.path.join(root, file_name)
                    folder_name = os.path.basename(root).title()

                    parts = file_name.split("_")
                    fund_id = parts[0]
                    fund_paths[fund_id] = (folder_name, full_path)
                     
        return fund_paths

    @staticmethod
    def get_fund_paths(path:str):
        mutual_fund_paths = {}
        for root, dirs, files in os.walk(path):
            file_found = False
            for name in files:
                if name.endswith((".pdf")) and not file_found:
                    tmp = root.split("\\")
                    key = tmp[-1].title()
                    value = rf'{root}\{name}'
                    mutual_fund_paths[key] = value
                    file_found = True
        
        return mutual_fund_paths
    
    @staticmethod
    def delete_file_by_suffix(base_folder: str, suffixes=[ "_clipped.pdf","_ocr.pdf","_all_ocr.pdf","_hltd.pdf"]):
        deleted_files = []

        for dirpath, _, filenames in os.walk(base_folder):
            for file in filenames:
                if any(file.endswith(suffix) for suffix in suffixes):
                    full_path = os.path.join(dirpath, file)
                    try:
                        os.remove(full_path)
                        deleted_files.append(full_path)
                    except Exception as e:
                        print(f"[ERROR] Could not delete {full_path}: {e}")
        return deleted_files
    
    @staticmethod
    def delete_all_files(folder_path):
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            if os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"Failed to delete {file_path}: {e}")

    @staticmethod
    def copy_pdfs_to_folder(dest_folder: str, data):

        if isinstance(data, dict):
            file_paths = list(data.values())
        elif isinstance(data, list):
            file_paths = data
        elif isinstance(data, str):
            file_paths = [data]
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
    def clear_folder(folder_path):
        """Delete all files (not subfolders) inside the given folder."""
        logger = get_global_logger()

        if not os.path.exists(folder_path):
            logger.warning(f"[clear_folder] Folder not found: {folder_path}")
            return

        deleted = 0
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            if os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                    deleted += 1
                except PermissionError:
                    logger.warning(f"Permission denied deleting {file_path}")
                except Exception as e:
                    logger.error(f"Failed to delete {file_path}: {e}")
        logger.info(f"Cleared {deleted} file(s) from {folder_path}")
        
    @staticmethod
    def delete_files(data):
        """Delete all files (not subfolders) inside the given folder."""
        logger = get_global_logger()

        if isinstance(data, dict):
            file_paths = list(data.values())
        elif isinstance(data, list):
            file_paths = data
        elif isinstance(data, str):
            file_paths = [data]
        else:
            logger.error(f"[archive_files] Invalid data type: {type(data)}")
            return

        for filepath in file_paths:
            if os.path.isfile(filepath):
                try:
                    os.remove(filepath)
                except PermissionError:
                    logger.warning(f"Permission denied deleting {filepath}")
                except Exception as e:
                    logger.error(f"Failed to delete {filepath}: {e}")

    @staticmethod
    def archive_files(dest_folder: str, data):
        """Copy one or more files to a destination folder (e.g., processed/ or failed/)."""
        logger = get_global_logger()

        if not os.path.exists(dest_folder):
            os.makedirs(dest_folder, exist_ok=True)
            logger.info(f"Created destination folder: {dest_folder}")

        if isinstance(data, dict):
            file_paths = list(data.values())
        elif isinstance(data, list):
            file_paths = data
        elif isinstance(data, str):
            file_paths = [data]
        else:
            logger.error(f"[archive_files] Invalid data type: {type(data)}")
            return

        copied = 0
        for path in file_paths:
            if not os.path.isfile(path):
                logger.warning(f"File not found, skipping: {path}")
                continue
            try:
                file_name = os.path.basename(path)
                dest_path = os.path.join(dest_folder, file_name)
                shutil.copy2(path, dest_path)
                copied += 1
            except Exception as e:
                logger.error(f"Failed to copy '{path}' → {dest_folder}: {e}")

        logger.info(f"Archived {copied} file(s) to {dest_folder}")

    
    #JSON UN/LOAD
    @staticmethod
    def create_dir(base_path, *folders):
        dir_path = os.path.join(base_path, *folders)
        os.makedirs(dir_path, exist_ok=True)
        return dir_path
    
    @staticmethod
    def save_json(data: dict, path: str, indent: int = 2):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent)

    @staticmethod
    def load_json(path: str):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
        
    @staticmethod
    def save_json5(data: dict, path: str, indent: int = 2):
        with open(path, "w", encoding="utf-8") as f:
            json5.dump(data, f, indent=indent)

    @staticmethod
    def load_json5(path: str):
        with open(path, "r", encoding="utf-8") as f:
            return json5.load(f)
    
    #WRITE TEXT
    @staticmethod
    def save_text(data,path:str):
        if not data:
            print("Empty Data")
            return
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'a', encoding='utf-8') as f:
            if isinstance(data,dict):
                f.writelines(f"{k}:{v}\n" for k,v in data.items())
            elif isinstance(data,list):
                f.writelines(f"{k}\n" for k in data)
            elif isinstance(data,str):
                f.writelines(data)
            else: print("Invalid type")
           
    def debug_save(pdf_bytes: bytes, filename="debug.pdf"):
        """Save in-memory PDF bytes to disk for debugging purposes."""
        with open(filename, "wb") as f:
            f.write(pdf_bytes)
        print(f"[debug] PDF saved to {filename}")
    
    def _clean_leading_noise(self,text: str) -> str:
        if not isinstance(text,str):
            return text
        return re.sub(r'^[\s\n\r\t\\:;\-–—•|]+', '', text).strip()
    
    def _normalize_key(self,text: str) -> str:
        if not isinstance(text,str):
            return text
        text = re.sub(r"[^\w\s\.]", "", text)
        text = re.sub(r"\s+", "_", text)
        return text.strip().lower()
    
    def _normalize_key_to_alnum_underscore(self, text: str) -> str:
        if not isinstance(text, str):
            return text
        text = text.strip().lower()
        text = re.sub(r"[^\w]", "_", text)
        text = re.sub(r"__+", "_", text)
        return text.strip("_")

    def _remove_duplicates(self,text):
        if not text:
            return text
        seen = []
        text = text.split(" ")
        for word in text:
            word = word.lower().strip()
            if word not in seen:
                seen.append(word)
        return " ".join(seen)

    #match type
    def is_numeric(self,text):
        return bool(re.fullmatch(r'[+-]?(\d+(\.\d*)?|\.\d+)', text))

    def is_alphanumeric(self,text):
        return bool(re.fullmatch(r'[A-Za-z0-9]+', text))

    def is_alpha(self,text):
        return bool(re.fullmatch(r'[A-Za-z]+', text))
        
    def _remove_non_word_space_chars(self,text:str)->str:
        if not isinstance(text,str):
            return text
        text = re.sub("[^\\w\\s]", "", text).strip()
        return text
    
    def _normalize_whitespace(self,text:str)->str:
        if not isinstance(text,str):
            return text
        return re.sub(r"\s+", " ", text).strip()
    
    def _normalize_date(self,text:str)->str:
        if not isinstance(text,str):
            return text
        text = re.sub(r"[^A-Za-z0-9\s\.\/\,\-\\]+"," ",text).strip()
        return self._normalize_whitespace(text)
    
    def _normalize_alphanumeric(self, text: str) -> str:
        if not isinstance(text,str):
            return text
        text = re.sub(r"[^a-zA-Z0-9]+", " ", str(text))
        return re.sub(r"\s+", " ", text).strip().lower()
    
    def _normalize_alpha(self, text: str) -> str:
        if not isinstance(text,str):
            return text
        text = re.sub(r"[^a-zA-Z]+", " ", str(text))
        return re.sub(r"\s+", " ", text).strip().lower()

    def _normalize_numeric(self, text: str) -> str:
        if not isinstance(text,str):
            return text
        text = re.sub(r"[^0-9\.]+", " ", str(text))
        return re.sub(r"\s+", " ", text).strip().lower()
    
    
