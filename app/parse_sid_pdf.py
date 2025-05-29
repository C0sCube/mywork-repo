import os, re, inspect,sys, ocrmypdf # type: ignore
import fitz # type: ignore
import camelot #type: ignore
import pandas as pd
import numpy as np
from collections import defaultdict

from app.parse_sid_regex import *
from app.fund_sid_data import *
from logging_config import *
from app.vendor_to_user import *
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.config_loader import *

conf = get_config() #path to paths.json


class ReaderSIDKIM:
    def __init__(self,params:dict,path:str):
    
        self.PARAMS = params #amc specific paramaters
        self.DOCUMENT_NAME = path.split("\\")[-1] # docname requried later for json
        self.OUTPUTPATH = conf["output_path"]
        self.PDF_PATH = path #amc factsheet pdf path
        self.JSONPATH = os.path.join(self.OUTPUTPATH, conf["output"]["json"])
        self.TEXT_ONLY = {}
        self.FIELD_LOCATION = {
            "page_zero":0,
            "page_table":0,
            "page_manager":0    
        } #to update field location as code progresses
    
        os.makedirs(os.path.dirname(self.JSONPATH), exist_ok=True)
    
    def _ocr_pdf(self,path:str)->str:
        print(f"Function Running: {inspect.currentframe().f_code.co_name}")
        ocr_path = path.replace(".pdf", "_all_ocr.pdf")
        ocrmypdf.ocr(path, ocr_path, deskew=True, force_ocr=True)
        return ocr_path
    
    def __extract_sorted_text_blocks(self,page,clip_area=None)->list:
        blocks = page.get_text("dict", clip=clip_area)["blocks"]
        text_blocks = []
        for block in blocks:
            if block.get("type") == 0:
                text = ""
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text += span.get("text", "")
                text = re.sub(r"\s+", " ", text).strip()
                if text:
                    text_blocks.append((block["bbox"], text))

        return [text for _, text in sorted(text_blocks, key=lambda b: (b[0][1], b[0][0]))] #top botton, left right
    
    def _parse_page_zero(self,pages: list) -> dict:
        print(f"Function Running: {inspect.currentframe().f_code.co_name}")
        final_dict = {"risk_bbox": [], "other_text": []}
        risk_bbox = self.PARAMS["page_zero"]["bbox"]

        with fitz.open(self.PDF_PATH) as doc:
            for pgn in pages:
                page = doc[pgn]
                final_dict["risk_bbox"].extend(self.__extract_sorted_text_blocks(page,clip_area=risk_bbox)) # Extract bbox text
                final_dict["other_text"].extend(self.__extract_sorted_text_blocks(page)) # Extract full text
        self.FIELD_LOCATION["page_zero"] = int(pages[0])
        return final_dict

    def __detect_column_start_by_keywords(self,df, threshold:int, keywords:list)->int:
        #important to noramalize both keywords and col_cleaned for == ops
        normalized_keywords = [re.sub(r"\s+", " ", kw.strip().lower()) for kw in keywords]

        for i in range(df.shape[1]):
            col = df.iloc[:, i].dropna().astype(str)
            col_cleaned = col.apply(lambda x: re.sub(r"\s+", " ", x).strip().lower())
            col_cleaned = col_cleaned[col_cleaned != ""]

            count = sum(any(kw in cell for kw in normalized_keywords) for cell in col_cleaned)

            if count >= threshold:
                return i
        return 1

    def _parse_scheme_table_data(self,pages:str)->dict:
        print(f"Function Running: {inspect.currentframe().f_code.co_name}")
        final_dict = {}
        threshold =self.PARAMS["table_data"]["threshold"]
        keywords = self.PARAMS["table_data"]["keywords"]
        regex = SidKimRegex()
        
        scheme_tables = camelot.read_pdf(self.PDF_PATH, pages=pages, flavor='lattice')
        
        dfs = pd.concat([table.df for table in scheme_tables], ignore_index=True)
        col_start = self.__detect_column_start_by_keywords(dfs,threshold=threshold,keywords=keywords)
        dfs = dfs.iloc[:,col_start:]
        # print(dfs.head(20))
        
        dfs = dfs.applymap(lambda x: x.replace('\n', ' ') if isinstance(x, str) else x) #applies to dataframe not series
        dfs.iloc[:, 0] = dfs.iloc[:, 0].replace(r'^\s*$', np.nan, regex=True).ffill() #fill corresponding structure
        dfs.columns = ['Title'] + [f'Data{i}' for i in range(1, dfs.shape[1])] #new col structure
        
        data_cols = dfs.columns.drop('Title')
        for title, group_df in dfs.groupby('Title', sort=False):
            
            title = regex._normalize_key(title)
            current_title_values = []
            for index, row in group_df.iterrows():
                for col_name in data_cols:
                    cell_value = row[col_name]
                    if isinstance(cell_value, str) and cell_value.strip() != '':
                        current_title_values.append(cell_value)
            final_dict[title] = current_title_values
        
        self.FIELD_LOCATION["page_table"] = int(pages.split(",")[0])
        return final_dict

    # def __detect_manager_column_start_by_keywords(self,df, threshold:int, keywords:list)->int:
    #     normalized_keywords = [re.sub(r"\s+", " ", kw.strip().lower()) for kw in keywords]
    #     first_kw = normalized_keywords[0]

    #     match_counts = {}

    #     for col_idx in range(df.shape[1]):
    #         count = 0
    #         for row_idx in range(df.shape[0]):
    #             cell = df.iat[row_idx, col_idx]
    #             if pd.isna(cell):
    #                 continue

    #             cell_clean = re.sub(r"\s+", " ", str(cell).strip().lower())
    #             if first_kw in cell_clean:
    #                 # Look at the full row from current column index
    #                 row_segment = df.iloc[row_idx, col_idx:].dropna().astype(str)
    #                 row_segment_cleaned = row_segment.apply(lambda x: re.sub(r"\s+", " ", x.strip().lower())).tolist()
    #                 # print(row_segment_cleaned)
    #                 # print(normalized_keywords)
    #                 for kw in normalized_keywords:
    #                     if any(kw in cell for cell in row_segment_cleaned):
    #                         count += 1
    #         match_counts[col_idx] = count
    #     # print(match_counts)
    #     # Return column index with highest valid match count over threshold
    #     for col_idx, count in match_counts.items():
    #         if count >= threshold:
    #             return col_idx

    #     return 1  # default fallback

    def __detect_manager_column_start_by_keywords(self, df, threshold: int, keywords: list) -> int:
        regex = SidKimRegex()
        normalized_keywords = [regex._normalize_alphanumeric(kw) for kw in keywords]
        match_counts = {}

        for col_idx in range(df.shape[1]):
            count = 0
            for row_idx in range(df.shape[0]):
                cell = df.iat[row_idx, col_idx]
                if pd.isna(cell):
                    continue

                cell_clean = regex._normalize_alphanumeric(cell)

                if any(kw in cell_clean for kw in normalized_keywords):
                    row_segment = df.iloc[row_idx, col_idx:].dropna().astype(str)
                    row_segment_cleaned = [regex._normalize_alphanumeric(x) for x in row_segment]

                    for kw in normalized_keywords:
                        for seg_cell in row_segment_cleaned:
                            if kw in seg_cell:
                                count += 1

            match_counts[col_idx] = count

        for col_idx, count in match_counts.items():
            if count >= threshold:
                return col_idx

        return 1  # fallback

    def _parse_fund_manager_info(self, pages: str) -> dict:
        print(f"Function Running: {inspect.currentframe().f_code.co_name}")
        
        row_count = self.PARAMS["manager_data"]["row_count"]
        match_order = self.PARAMS["manager_data"]["order"]
        threshold = self.PARAMS["manager_data"]["threshold"]
        keywords = self.PARAMS["manager_data"]["keywords"]
        
        regex = SidKimRegex()

        manager_tables = camelot.read_pdf(self.PDF_PATH, pages=pages, flavor='lattice')
        dfs = pd.concat([table.df for table in manager_tables], ignore_index=True)
        dfs = dfs.applymap(lambda x: x.replace('\n', ' ') if isinstance(x, str) else x)
        
        col_start = self.__detect_manager_column_start_by_keywords(dfs, threshold, keywords)
        dfs = dfs.iloc[:, col_start:]

        data_rows = [list(row) for _, row in dfs.iterrows() if row.count() >= row_count] #row_count gets NA sometimes

        manager_list = []
        for data_r in data_rows:
            manager_list.append({
                "name": regex._normalize_whitespace(data_r[match_order["name"]]),
                "experience": regex._normalize_whitespace(data_r[match_order["experience"]]),
                "qualification": regex._normalize_whitespace(data_r[match_order["qualification"]]),
            })

        self.FIELD_LOCATION["page_manager"] = int(pages.split(",")[0])
        return {"fund_manager": manager_list}
    
    # def _parse_fund_manager_info(self,pages:str)->dict:
    #     print(f"Function Running: {inspect.currentframe().f_code.co_name}")
    #     row_count =self.PARAMS["manager_data"]["row_count"]
    #     match_order = self.PARAMS["manager_data"]["order"]
    #     regex = SidKimRegex()
        
    #     manager_tables = camelot.read_pdf(self.PDF_PATH, pages=pages, flavor='lattice')
    #     dfs = pd.concat([table.df for table in manager_tables], ignore_index=True)
    #     dfs = dfs.applymap(lambda x: x.replace('\n', ' ') if isinstance(x, str) else x)
        
    #     data_rows = [list(row) for _, row in dfs.iterrows() if row.count()==row_count]
    #     manager_list = []
    #     for data_r in data_rows:
    #         manager_list.append({
    #             "name":regex._normalize_whitespace(data_r[match_order["name"]]),
    #             "experience":regex._normalize_whitespace(data_r[match_order["experience"]]),
    #             "qualification":regex._normalize_whitespace(data_r[match_order["qualification"]]),
    #         })
        
    #     self.FIELD_LOCATION["page_manager"] = int(pages.split(",")[0])
    #     return  {"fund_manager": manager_list}
    
    # def get_data(self,pages):
    #     # | Tool      | Page Indexing | Example                  |
    #     # | --------- | ------------- | ------------------------ |
    #     # | `fitz`    | **0-based**   | `doc[0]` → first page    |
    #     # | `camelot` | **1-based**   | `pages="1"` → first page |
    #     final_dict = {}

    #     final_dict.update(self._parse_page_zero(pages))
    #     final_dict.update(self._parse_scheme_table_data(pages))
    #     final_dict.update(self._parse_fund_manager_info(pages))

    #     return final_dict
    
    # =================== KIM ===================
    
    def __is_percentage(self,val):
        return isinstance(val, str) and bool(re.fullmatch(r"(\d+\%?\s*\d*\%?)+", val.strip()))

    def __detect_kim_row_start_end(self,dfs):
        regex = SidKimRegex()
        pattern = re.compile(r"^(minimum|maximum|minimummaximum|maximumminimum|instruments)$", re.IGNORECASE)
        row_start,row_end = 0,0
        for index, row in dfs.iterrows():
            values = [regex._normalize_alphanum_percentage(val) for val in row if isinstance(val, str)]
            matches = [val for val in values if re.match(pattern, val)]
            
            if len(matches) >= 1:  # both minimum and maximum-type matches present
                row_start = index
                # print(row_start)
                break
        
        row_end = row_start
        for idx in range(row_start + 1, len(dfs)):
            row = list(dfs.iloc[idx])
            if any(self.__is_percentage(val) for val in row):
                row_end = idx
                # print(row_end)
            else:
                break
        print(f"row start: {row_start} row end: {row_end}")
        return row_start,row_end
    
    def _get_kim_data(self,pages:str):
        
        table_data = camelot.read_pdf(self.PDF_PATH,pages=pages, flavor="lattice")
        dfs = pd.concat([table.df for table in table_data], ignore_index=True)
        dfs = dfs.replace(r"\n","",regex=True).replace(r'^\s*$', pd.NA, regex=True).dropna(axis=1, how='all')
        row_start,row_end = self.__detect_kim_row_start_end(dfs)
        df = dfs.iloc[row_start:row_end+1,:].dropna(axis=1,how="all")
        df.fillna("",inplace=True)
        
        #fill header
        if pd.isna(df.iloc[0, 0]) or df.iloc[0, 0] == '':
            df.iat[0, 0] = "Instrument"
        # if pd.isna(df.iloc[0, -1]) or df.iloc[0, -1] == '':
        #     df.iat[0, -1] = "Risk"
        return df.fillna("").values.tolist()
    
    def _get_unique_key(self,base_key:str, data:dict):
        for suffix in ["bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel", "india", "juliett", "kilo"]:
            new_key = f"{base_key}_{suffix}"
            if new_key not in data:
                return new_key
        return "exhausted"
      
    def refine_extracted_data(self, extracted_text: dict):
        print(f"Function Running: {inspect.currentframe().f_code.co_name}")
        regex = SidKimRegex()

        # header_map = {}
        primary_refine = {}

        # ─── Primary Refinement ─────────────────────────────
        for raw_key, raw_values in extracted_text.items():
            # header_map[raw_key] = raw_key
            matched = self._match_with_patterns(raw_key, raw_values, level="primary")
            if matched:
                key, value = next(iter(matched.items()))
                primary_refine[raw_key] = value
            else:
                primary_refine[raw_key] = raw_values  # fallback to original

        primary_refine = regex._flatten_dict(primary_refine) # Flatten ONLY primary
        primary_refine = regex._transform_keys(primary_refine)
        # ─── Secondary Refinement ───────────────────────────
        secondary_refine = {}
        for main_key, main_value in primary_refine.items():
            matched = self._match_with_patterns(main_key, main_value, level="secondary")
            if matched:
                key, value = next(iter(matched.items()))
                secondary_refine[main_key] = value
            else:
                secondary_refine[main_key] = main_value

        # ─── Tertiary Refinement ────────────────────────────
        tertiary_refine = {}
        for main_key, main_value in secondary_refine.items():
            matched = self._match_with_patterns(main_key, main_value, level="tertiary")
            if matched:
                key, value = next(iter(matched.items()))
                tertiary_refine[main_key] = value
            else:
                tertiary_refine[main_key] = main_value

        
        return tertiary_refine
    
    def __min_add_ops(self,df:dict):
        try:
            new_values = {}
            for key in ["min_amt", "min_addl_amt"]:
                if key in df:
                    new_values[key] = df[key].get("amt", "")
                    new_values[f"{key}_multiple"] = df[key].get("thraftr", "")
            df.update(new_values)
        except Exception as e:
            # logger.error(e)
            print(f"Error in _min_add_ops ->Min/Add Error: {e}")
        return df
    
    def __load_ops(self,df:dict):
        load_data = df.get("load", {})
        if not isinstance(load_data, dict):
            print(f"Returning _load_ops -> Type Error")
            return df
        try:
            new_load = []
            for load_key, load_value in load_data.items():
                load_section = {
                    "comment":None,
                    "type":None,
                    "value":""
                }
                value = load_value if isinstance(load_value, str) else " ".join(load_value)
                if re.search(r"(entry|.*entry_load)", load_key, re.IGNORECASE) and value:
                    load_section["comment"] = value
                    load_section["type"] = "entry_load"
                    new_load.append(load_section)
                elif re.search(r"(exit|.*exit_load)", load_key, re.IGNORECASE) and value:
                    load_section["comment"] = value
                    load_section["type"] = "exit_load"
                    new_load.append(load_section)
        except Exception as e:
            print(f"Error in _load_ops ->Load Error: {e}")
        
        df["load"] = new_load
        return df
    

    def merge_and_select_data(self, data:dict, sid_or_kim:str,special_func:bool):
        print(f"Function Running: {inspect.currentframe().f_code.co_name}")
        # finalData = {}
        regex = SidKimRegex()
        
        temp = self._clone_fund_data(data)
        temp = self._merge_fund_data(temp)
        temp = self._clone_fund_data(temp)
        
        #selecting
        temp = self._select_by_regex(temp)
        
        #mapping typez:sid/kim
        mappend_data = {}
        for key, value in temp.items():
            new_key = regex._map_json_keys_to_dict(text=key,typez=sid_or_kim) or key
            mappend_data[new_key] = value
        temp = mappend_data
        
        temp = self.__min_add_ops(temp)
        temp = regex._populate_all_indices_in_json(data=temp,typez=sid_or_kim) #populate
        # temp = regex._transform_keys(temp) #lowercase
        temp = self.__load_ops(temp)
        
        if special_func:
            for main_key,value in temp.items():
                updated_temp = self._special_match_regex_to_content(main_key,value)
            if updated_temp:
                temp.update(updated_temp)
        
        temp = self._promote_key_from_dict(temp)
        temp = self._update_imp_data(temp) #update default values like amc_name
        # temp = regex._check_replace_type(temp,fund) #type conversion
        temp = regex._field_locations(temp,self.FIELD_LOCATION,typez=sid_or_kim)
        temp = regex._final_json_construct(temp, self.DOCUMENT_NAME)
        temp = self._delete_fund_data_by_key(temp) #final delete unwanted keys
        return dict(sorted(temp.items()))