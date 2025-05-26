import os, re, math, json, inspect,sys, ocrmypdf # type: ignore
import fitz # type: ignore
import camelot #type: ignore
import pandas as pd
import numpy as np
from collections import defaultdict

from app.parse_regex import *
from app.fund_data import *
from logging_config import *
from app.vendor_to_user import *
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.config_loader import *

conf = get_config() #path to paths.json


class ReaderSIDKIM:
    def __init__(self,params:dict,amc_id:str,path:str):
    
        self.PARAMS = params #amc specific paramaters
        self.FILE_NAME = path.split("\\")[-1] # filename requried later for json
        self.OUTPUTPATH = conf["output_path"]
        self.PDF_PATH = path #amc factsheet pdf path
        # self.DRYPATH = os.path.join(self.OUTPUTPATH, conf["output"]["dry"])
        # self.REPORTPATH = os.path.join(self.OUTPUTPATH, paths.get("rep", ""))
        self.JSONPATH = os.path.join(self.OUTPUTPATH, conf["output"]["json"])
        self.TEXT_ONLY = {}
        
        for output_path in [self.DRYPATH, self.JSONPATH]: # self.REPORTPATH
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    def _ocr_pdf(self,path:str):
        print(f"Function Running: {inspect.currentframe().f_code.co_name}")
        ocr_path = path.replace(".pdf", "_all_ocr.pdf")
        ocrmypdf.ocr(path, ocr_path, deskew=True, force_ocr=True)
        return ocr_path
    
    def _parse_page_zero(self,pages:list):
        
        final_dict,bbox_text,other_text = {},[],[]
        risk_bbox = self.PARAMS["page_zero"]["bbox"]
        with fitz.open(self.PDF_PATH) as doc:
            for pgn, page in enumerate(doc):
                if pgn in pages:
                    bbox_text.append(page.get_text("text", clip=risk_bbox).replace("\n", ""))
                    other_text.append(page.get_text("text").replace("\n", ""))
            final_dict["risk_bbox"] = bbox_text
            final_dict["other_text"] = other_text
        return final_dict

    def _detect_column_start_by_keywords(self,df,threshold,keywords):
        
        for i in range(df.shape[1]):
            col = df.iloc[:, i]
            col_cleaned = col.dropna().astype(str)
            col_cleaned = col_cleaned.apply(lambda x: re.sub(r"\s+", " ", x).strip())
            col_cleaned = col_cleaned[col_cleaned.str.strip() != ""]

            count = sum(any(kw in cell for kw in keywords) for cell in col_cleaned)

            if count >= threshold:
                return i
        return 1

    def _parse_scheme_table_data(self,pages:str):
        
        final_dict = {}
        threshold =self.PARAMS["table_data"]["threshold"]
        keywords = self.PARAMS["table_data"]["keywords"]
        
        scheme_tables = camelot.read_pdf(self.PDF_PATH, pages=pages, flavor='lattice')
        
        dfs = pd.concat([table.df for table in scheme_tables], ignore_index=True)
        col_start = self._detect_column_start_by_keywords(dfs,threshold=threshold,keywords=keywords)
        dfs = dfs.iloc[:,col_start:]
        # print(dfs.head(20))
        
        dfs = dfs.applymap(lambda x: x.replace('\n', ' ') if isinstance(x, str) else x) #applies to dataframe not series
        dfs.iloc[:, 0] = dfs.iloc[:, 0].replace(r'^\s*$', np.nan, regex=True)
        dfs.iloc[:, 0] = dfs.iloc[:, 0].ffill() #fill corresponding structure
        dfs.columns = ['Title'] + [f'Data{i}' for i in range(1, dfs.shape[1])] #new col structure
        
        data_cols = [col for col in dfs.columns if col != 'Title']
        for title, group_df in dfs.groupby('Title', sort=False):
            title = re.sub(r"[^A-Za-z0-9\s]+","",title).strip()
            title = re.sub(r"\s+"," ",title).strip()
            title = "_".join(title.lower().split(" "))
            
            current_title_values = []
            for index, row in group_df.iterrows():
                for col_name in data_cols:
                    cell_value = row[col_name]
                    if isinstance(cell_value, str) and cell_value.strip() != '':
                        current_title_values.append(cell_value)
            final_dict[title] = current_title_values
            
        return final_dict

    def _parse_fund_manager_info(self,pages:str):
        
        row_count =self.PARAMS["manager_data"]["row_count"]
        match_order = self.PARAMS["manager_data"]["order"]
        
        manager_tables = camelot.read_pdf(self.PDF_PATH, pages=pages, flavor='lattice')
        dfs = pd.concat([table.df for table in manager_tables], ignore_index=True)
        dfs = dfs.applymap(lambda x: x.replace('\n', ' ') if isinstance(x, str) else x)
        
        data_rows = [list(row) for _, row in dfs.iterrows() if row.count()==row_count]
        manager_list = []
        for data_r in data_rows:
            manager_list.append({
                "name":data_r[match_order["name"]],
                "experience":data_r[match_order["experience"]],
                "qualification":data_r[match_order["qualification"]],
            })
        return  {"fund_manager": manager_list}
    
    def get_data(self):
        pass
    
    def _get_unique_key(self,base_key:str, data:dict):
        for suffix in ["bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel", "india", "juliett", "kilo"]:
            new_key = f"{base_key}_{suffix}"
            if new_key not in data:
                return new_key
        return "exhausted"

    def refine_extracted_data(self, extracted_text: dict):
        print(f"Function Running: {inspect.currentframe().f_code.co_name}")
        primary_refine = {}
        regex = FundRegex()
        
        header_map = {} #keep track of headers after each iteration, its imp
        for main_key, main_value in extracted_text.items():
            content_dict = {}
            if clean_head:=  regex.header_mapper(main_key):
                header_map[main_key] = clean_head
                content = self._match_with_patterns(clean_head, main_value,level = "primary") # applies regex to clean data
                content = regex.transform_keys(content) #lowercase
                if content:
                    key, value = next(iter(content.items()))
    
                if clean_head in content_dict:
                    unique_key = self._get_unique_key(clean_head, content_dict)
                    content_dict[unique_key] = value
                else:
                    content_dict[clean_head] = value           
            primary_refine[key] = content_dict
            
        #Flatten primary
        primary_refine = {fund: regex.flatten_dict(data) for fund, data in primary_refine.items()}
        
        secondary_refine = {}
        for main_key, main_value in primary_refine.items():
            content_dict = {}
            clean_head = header_map.get(main_key, main_key)
            content = self._match_with_patterns(clean_head, main_value,level = "secondary")
            
            # if clean_head in self.FLATTENABLE_KEYS: wip
            #     content = regex.flatten_dict(content)
            if content is not None:
                content_dict.update(content)
            secondary_refine = content_dict
            
        tertiary_refine = {}
        for main_key, main_value in secondary_refine.items():
            content_dict = {}
            clean_head = header_map.get(main_key, main_key)
            content = self._match_with_patterns(clean_head, main_value,level = "secondary")
            if content is not None:
                content_dict.update(content)
            tertiary_refine = content_dict
            
        return tertiary_refine
    
    def merge_and_select_data(self):
        pass