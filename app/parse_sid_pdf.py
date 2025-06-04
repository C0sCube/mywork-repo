import os, re, inspect,sys, ocrmypdf, camelot, pprint # type: ignore
import fitz # type: ignore
import pandas as pd
import numpy as np

from app.parse_sid_regex import *
from app.fund_sid_data import *
from app.parse_table import *

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
            "page_manager":0,
            "kim":0    
        } #to update field location as code progresses
    
        os.makedirs(os.path.dirname(self.JSONPATH), exist_ok=True)
    
    def _ocr_pdf(self,path:str,pages)->str:
        print(f"Function Running: {inspect.currentframe().f_code.co_name}")
        ocr_path = path.replace(".pdf", "_all_ocr.pdf")
        ocrmypdf.ocr(path, ocr_path, deskew=True, force_ocr=True, pages=pages)
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
    
    def _get_text_from_pages_and_bboxes(self,path:str, pages_csv: str, bboxes: list) -> str:
        pages_list = [int(p.strip()) for p in pages_csv.split(",") if p.strip()]
        extracted_text = []

        with fitz.open(path) as doc:
            for pg in pages_list:
                if 0 <= pg < len(doc):
                    page = doc[pg]
                    for bbox in bboxes:
                        extracted_text.extend(self.__extract_sorted_text_blocks(page, clip_area=bbox))

        return " ".join(extracted_text).strip()

    def _get_full_text_from_pages(self,path:str, pages_csv: str) -> list:
        pages = [int(p.strip()) for p in pages_csv.split(",") if p.strip()]
        extracted = []
        with fitz.open(path) as doc:
            for p in pages:
                if 0 <= p < len(doc):
                    extracted.extend(self.__extract_sorted_text_blocks(doc[p]))
        return extracted

    # =================== SID ===================
    
    def __resolve_page_index(self,pages_str: str, fitz: bool) -> str:
        pages_str = pages_str.strip()
        if not pages_str:
            return ""
        result_pages = set()
        for part in pages_str.split(','):
            part = part.strip()
            if '-' in part:
                start_str, end_str = part.split('-', 1)
                start, end = int(start_str), int(end_str)
                pages = range(start, end + 1)
            else:
                pages = [int(part)]

            for p in pages:
                # If fitz is True, convert 1-based to 0-based
                page_num = p - 1 if fitz else p
                result_pages.add(page_num)

        sorted_pages = sorted(result_pages)
        return ",".join(str(p) for p in sorted_pages)

    def parse_page_zero(self, pages: str) -> dict:
        print(f"Function Running: {inspect.currentframe().f_code.co_name}")
        self.FIELD_LOCATION["page_zero"] = int(pages)
        zero_params = self.PARAMS["page_zero"]
        
        path = self._ocr_pdf(self.PDF_PATH,pages) if zero_params["ocr"] else self.PDF_PATH
        
        fitz_pages = self.__resolve_page_index(pages,True)
        # print(fitz_pages, pages)
        final_dict = {
            "risk_bbox": self._get_text_from_pages_and_bboxes(path=path,pages_csv=fitz_pages, bboxes=zero_params["bbox"]),
            "other_text": self._get_full_text_from_pages(path=path,pages_csv=fitz_pages)
        }
        return final_dict

    def parse_scheme_table_data(self,pages:str)->dict:
        print(f"Function Running: {inspect.currentframe().f_code.co_name}")
        self.FIELD_LOCATION["page_table"] = pages.split(",")[0]
        table_params = self.PARAMS["table_data"]
        regex,tableparse = SidKimRegex(),TableParser()
        
        dfs = tableparse._extract_tables_from_pdf(path=self.PDF_PATH,pages=pages)
        col_start = tableparse._get_matching_col_indices(dfs,thresh=table_params["threshold"],keywords=table_params["keywords"])
        print(f"[COL START]: {col_start} _keys: {table_params["keywords"]}")
        
        dfs = tableparse._get_sub_dataframe(dfs,cs=col_start[0])
        dfs = tableparse._clean_dataframe(dfs, ["newline_to_space"])
        dfs.iloc[:, 0] = tableparse._clean_series(dfs.iloc[:, 0], ["str_to_pd_NA"]).ffill()
    
        dfs.columns = ['Title'] + [f'Data{i}' for i in range(1, dfs.shape[1])] #new col structure
        return tableparse._group_and_collect(dfs,group_col="Title")
    
    def parse_fund_manager_info(self, pages: str) -> dict:
        print(f"Function Running: {inspect.currentframe().f_code.co_name}")
        self.FIELD_LOCATION["page_manager"] = pages.split(",")[0]
        manager_params = self.PARAMS["manager_data"]
        regex,tableparse = SidKimRegex(),TableParser()

        dfs = tableparse._extract_tables_from_pdf(path=self.PDF_PATH,pages=pages)
        row_start = tableparse._get_matching_row_indices(dfs,thresh=manager_params["threshold"],keywords=manager_params["keywords"])
        print(f"[ROW START]: {row_start} _keys: {manager_params["keywords"]}")
        
        dfs = tableparse._get_sub_dataframe(dfs,rs=row_start[0])
        dfs = tableparse._clean_dataframe(dfs,steps=["newline_to_space","remove_extra_whitespace"])
        dfs = dfs.dropna(axis=1, how="all").dropna(axis=0, how="all") #drop NA cols

        match_order = manager_params["order"]
        # print(match_order)
        manager_list = []
        data_rows = [list(row) for _, row in dfs.iterrows()] #row_count gets NA sometimes  if row.count() >= manager_params["row_count"]
        # pprint.pprint(data_rows)
        for row in data_rows:
            manager = {
                key: regex._normalize_whitespace(row[col_idx])
                for key, col_idx in match_order.items()
            }
            manager_list.append(manager)
        return {"fund_manager": manager_list}
      
    # =================== KIM ===================
    
    def _get_kim_data(self,pages:str, instrument_count = 2)->dict:
        print(f"Function Running: {inspect.currentframe().f_code.co_name}")
        self.FIELD_LOCATION["kim"] = int(pages.split(",")[0])
        kim_params = self.PARAMS["kim"]
        regex,tableparse = SidKimRegex(),TableParser()
        
        dfs = tableparse._extract_tables_from_pdf(self.PDF_PATH,pages=pages,stack=True,padding=1)
        dfs = tableparse._clean_dataframe(dfs,['newline_to_space','str_to_pd_NA'])
        
        row_start = tableparse._get_matching_row_indices(dfs,keywords=kim_params["row_keywords"],thresh=kim_params["row_match_threshold"])
        print(f"[ROW START]: {row_start}" )
        
        dfs = tableparse._get_sub_dataframe(dfs,rs=row_start[0]+1, re=row_start[0]+ 2 + instrument_count)
        dfs = tableparse._clean_dataframe(dfs,['str_to_pd_NA','drop_all_na','NA_to_str'])
        # print(dfs)
        final_data = {}
        #fitz pages check params
        final_data["main_scheme_name"] = self._get_text_from_pages_and_bboxes(self.PDF_PATH,kim_params["initial_page"], kim_params["bbox"])

        asset_list = []
        for _, row in dfs.iterrows():
            row = list(row)
            values = " ".join(str(item) for item in row)
            values = regex._normalize_alphanumeric_and_symbol(values,"%&")
            asset_list.append(values)
        final_data["asset_allocation_pattern"] = asset_list
            
        return final_data
        # return dfs
    
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
            # print(matched)
            if matched:
                key, value = next(iter(matched.items()))
                primary_refine[raw_key] = value
            else:
                primary_refine[raw_key] = raw_values  # fallback to original
        # print("Primary keys:", list(primary_refine.keys()))
        primary_refine = regex._flatten_dict(primary_refine) #flat_primary
        primary_refine = regex._transform_keys(primary_refine)

        # print("After flatten:", list(primary_refine.keys()))
        # print("After transform:", list(primary_refine.keys()))
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
    
    def __map_json_ops(self,df, typez:str)->dict:
        return {SidKimRegex()._map_json_keys_to_dict(k,typez=typez) or k: v for k, v in df.items()}
    
    # def __map_asset_kim_ops(self,df:dict, order:list)->dict:
    #     pass
    #     asset_data = df.get("asset_allocation_data",[])
    #     if not isinstance(asset_data,list):
    #         print(f"Returning _load_ops -> Type Error")
    #         return df
    #     try:
    #         asset_allocation_pattern = []
    #         for data in df:
    #             asset = {"allocation":[],"instrument_type":"","risk_profile":""}
    #             for idx, loc in enumerate(order.split("|")):
    #                 if loc == "instr":
    #                     asset['instrument_type'] = data[idx]
    #                 if loc == "min":
    #                     asset["allocation"].append({"type":"min","value":data[idx]})
    #                 if loc == "max":
    #                     asset["allocation"].append({"type":"max","value":data[idx]})
    #                 if loc == "total":
    #                     asset["allocation"].append({"type":"total","value":data[idx]})
    #             asset_allocation_pattern.append(asset)
    #     except Exception as e:
    #         print(f"Error in _map_asset_kim_ops -> {e}")
    #     df["asset_allocation_pattern"] = asset_allocation_pattern
    #     return df
                        
    def merge_and_select_data(self, data:dict, sid_or_kim:str,special_func:bool):
        print(f"Function Running: {inspect.currentframe().f_code.co_name}")
        regex = SidKimRegex()
        
        temp = self._clone_fund_data(data)
        temp = self._merge_fund_data(temp)
        temp = self._clone_fund_data(temp)
        temp = self._select_by_regex(temp) #select
        
        #mapping typez:sid/kim
        if sid_or_kim == "sid":
            temp = self.__map_json_ops(temp,typez=sid_or_kim)
            temp = self.__min_add_ops(temp)
            temp = regex._populate_all_indices_in_json(data=temp,typez=sid_or_kim) #populate
            temp = self.__load_ops(temp)
        if sid_or_kim == "kim":
            # temp = self.__map_asset_kim_ops(temp,order=self.PARAMS["kim"]["row_order"])
            temp = self.__map_json_ops(temp,typez=sid_or_kim)
            temp = regex._populate_all_indices_in_json(data=temp,typez=sid_or_kim) #populate
        
        if special_func:
            temp = self._apply_special_handling(temp)
        
        temp = self._promote_key_from_dict(temp)
        temp = self._update_imp_data(temp, typez = sid_or_kim) #update default keys
        temp = regex._field_locations(temp,self.FIELD_LOCATION,typez=sid_or_kim)
        temp = self._delete_fund_data_by_key(temp) #delete keys
        temp = regex._final_json_construct(temp, self.DOCUMENT_NAME, typez=sid_or_kim)
        
        return dict(sorted(temp.items()))