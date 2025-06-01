import os, re, inspect,sys, ocrmypdf, camelot # type: ignore
import fitz # type: ignore
import pandas as pd
import numpy as np

from app.parse_sid_regex import *
from app.fund_sid_data import *
from app.parse_table import *
from logging_config import *
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
    
    def _ocr_pdf(self,path:str,pages)->str:
        print(f"Function Running: {inspect.currentframe().f_code.co_name}")
        ocr_path = path.replace(".pdf", "_all_ocr.pdf")
        ocrmypdf.ocr(path, ocr_path, deskew=True, force_ocr=True, pages=pages)
        return ocr_path
    
    def _extract_sorted_text_blocks(self,page,clip_area=None)->list:
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
        self.FIELD_LOCATION["page_zero"] = int(pages[0])
        final_dict = {"risk_bbox": [], "other_text": []}
        zero_params = self.PARAMS["page_zero"]
        
        path = self._ocr_pdf(self.PDF_PATH) if zero_params["ocr"] else self.PDF_PATH

        with fitz.open(path) as doc:
            for pgn in pages:
                page = doc[pgn]
                for bbox in zero_params["bbox"]:
                    final_dict["risk_bbox"].extend(self._extract_sorted_text_blocks(page,clip_area=bbox))# Extract bbox text
                final_dict["other_text"].extend(self._extract_sorted_text_blocks(page)) # Extract full text
        return final_dict

    def _parse_scheme_table_data(self,pages:str)->dict:
        print(f"Function Running: {inspect.currentframe().f_code.co_name}")
        self.FIELD_LOCATION["page_table"] = int(pages.split(",")[0])
        table_params = self.PARAMS["table_data"]
        regex = SidKimRegex()
        tableparse = TableParser()
        
        dfs = tableparse._extract_tables_from_pdf(path=self.PDF_PATH,pages=pages)
        col_start = tableparse._get_matching_col_indices(dfs,thresh=table_params["threshold"],keywords=table_params["keywords"])
        dfs = tableparse._get_sub_dataframe(dfs,cs=col_start[0])
    
        dfs = tableparse._clean_dataframe(dfs, ["newline_to_space"])
        dfs.iloc[:, 0] = tableparse._clean_series(dfs.iloc[:, 0], ["str_to_pd_NA"]).ffill()
    
        dfs.columns = ['Title'] + [f'Data{i}' for i in range(1, dfs.shape[1])] #new col structure
        return tableparse._group_and_collect(dfs,group_col="Title")

    def _parse_fund_manager_info(self, pages: str) -> dict:
        print(f"Function Running: {inspect.currentframe().f_code.co_name}")
        self.FIELD_LOCATION["page_manager"] = int(pages.split(",")[0])
        manager_params = self.PARAMS["manager_data"]
        regex = SidKimRegex()
        tableparse = TableParser()

        dfs = tableparse._extract_tables_from_pdf(path=self.PDF_PATH,pages=pages)
        dfs = tableparse._clean_dataframe(dfs,steps=["newline_to_space","remove_extra_whitespace"])

        col_start = tableparse._get_matching_row_indices(dfs,thresh=manager_params["threshold"],keywords=manager_params["keywords"])
        dfs = tableparse._get_sub_dataframe(dfs,cs=col_start[0])
        dfs.dropna(axis=1, how="all", inplace=True) #drop NA cols

        match_order = manager_params["order"]
        # print(match_order)
        manager_list = []
        data_rows = [list(row) for _, row in dfs.iterrows()] #row_count gets NA sometimes  if row.count() >= manager_params["row_count"]
        # print(data_rows)
        for row in data_rows:
            manager = {
                key: regex._normalize_whitespace(row[col_idx])
                for key, col_idx in match_order.items()
            }
            manager_list.append(manager)

        return {"fund_manager": manager_list}
      
    # =================== KIM ===================
    
    # def __is_percentage(self,val):
    #     return isinstance(val, str) and bool(re.fullmatch(r"(\d+\%?\s*\d*\%?)+", val.strip()))

    # def __detect_kim_row_start_end(self,dfs):
    #     regex = SidKimRegex()
    #     pattern = re.compile(r"^(minimum|maximum|minimummaximum|maximumminimum|instruments)$", re.IGNORECASE)
    #     row_start,row_end = 0,0
    #     for index, row in dfs.iterrows():
    #         values = [regex._normalize_alphanum_percentage(val) for val in row if isinstance(val, str)]
    #         matches = [val for val in values if re.match(pattern, val)]
            
    #         if len(matches) >= 1:  # both minimum and maximum-type matches present
    #             row_start = index
    #             break
        
    #     row_end = row_start
    #     for idx in range(row_start + 1, len(dfs)):
    #         row = list(dfs.iloc[idx])
    #         if any(self.__is_percentage(val) for val in row):
    #             row_end = idx
    #         else:
    #             break
    #     print(f"row start: {row_start} row end: {row_end}")
    #     return row_start,row_end
    
    def _get_kim_data(self,pages:str):
        
        tableparse = TableParser()
        
        dfs = tableparse._extract_tables_from_pdf(self.PDF_PATH,pages=pages)
        dfs = tableparse._clean_dataframe(dfs,['newline_to_space','str_to_pd_NA'])
        
        start_keywords = ["^minimum","^maximum","^minimummaximum","^maximumminimum","instruments","indicative asset allocation"]
        end_keywords = ["^\\d+\\%?\\d*\\%?"]
        
        # row_start,row_end = self.__detect_kim_row_start_end(dfs)
        row_start = tableparse._get_matching_row_indices(dfs,keywords=start_keywords,thresh=2)
        row_end = tableparse._get_matching_row_indices(dfs,keywords=end_keywords,thresh=2)
        print(row_start,row_end)
        
        dfs = tableparse._get_sub_dataframe(dfs,rs=row_start[0])
        dfs = dfs.dropna(axis=1,how="all")
        dfs.fillna("",inplace=True)
        
        #fill header
        # if pd.isna(df.iloc[0, 0]) or df.iloc[0, 0] == '':
        #     df.iat[0, 0] = "Instrument"
        # return df.fillna("").values.tolist()
        return dfs
    
    # def _get_unique_key(self,base_key:str, data:dict):
    #     for suffix in ["bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel", "india", "juliett", "kilo"]:
    #         new_key = f"{base_key}_{suffix}"
    #         if new_key not in data:
    #             return new_key
    #     return "exhausted"
      
    def refine_extracted_data(self, extracted_text: dict):
        print(f"Function Running: {inspect.currentframe().f_code.co_name}")
        regex = SidKimRegex()
        # header_map = {}
        primary_refine = {}
        for raw_key, raw_values in extracted_text.items():
            # header_map[raw_key] = raw_key
            matched = self._match_with_patterns(raw_key, raw_values, level="primary")
            if matched:
                key, value = next(iter(matched.items()))
                primary_refine[raw_key] = value
            else:
                primary_refine[raw_key] = raw_values  # fallback to original

        primary_refine = regex._flatten_dict(primary_refine) #flat_primary
        primary_refine = regex._transform_keys(primary_refine)
      
        secondary_refine = {}
        for main_key, main_value in primary_refine.items():
            matched = self._match_with_patterns(main_key, main_value, level="secondary")
            if matched:
                key, value = next(iter(matched.items()))
                secondary_refine[main_key] = value
            else:
                secondary_refine[main_key] = main_value

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
        regex = SidKimRegex()
        
        temp = self._clone_fund_data(data)
        temp = self._merge_fund_data(temp)
        temp = self._clone_fund_data(temp)
        temp = self._select_by_regex(temp) #select
        
        #mapping typez:sid/kim
        mappend_data = {}
        for key, value in temp.items():
            new_key = regex._map_json_keys_to_dict(text=key,typez=sid_or_kim) or key
            mappend_data[new_key] = value
        temp = mappend_data
        
        temp = self.__min_add_ops(temp)
        temp = regex._populate_all_indices_in_json(data=temp,typez=sid_or_kim) #populate
        temp = self.__load_ops(temp)
        
        if special_func:
            for main_key,value in temp.items():
                updated_temp = self._special_match_regex_to_content(main_key,value)
            if updated_temp:
                temp.update(updated_temp)
        
        temp = self._promote_key_from_dict(temp)
        temp = self._update_imp_data(temp) #update default values like amc_name
        temp = regex._field_locations(temp,self.FIELD_LOCATION,typez=sid_or_kim)
        temp = self._delete_fund_data_by_key(temp) #final delete unwanted keys
        temp = regex._final_json_construct(temp, self.DOCUMENT_NAME)
        return dict(sorted(temp.items()))