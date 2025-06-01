import os, re, inspect,sys, ocrmypdf, camelot # type: ignore
import fitz # type: ignore
import pandas as pd
import numpy as np

from app.parse_sid_regex import *
from app.fund_sid_data import *
from logging_config import *
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.config_loader import *

conf = get_config() #path to paths.json

class TableParser:
    
    def __init__(self):
        self.pipeline = {
            'remove_extra_whitespace': lambda x: re.sub(r'\s+', ' ', x) if isinstance(x, str) else x,
            'strip_edges': lambda x: x.strip() if isinstance(x, str) else x,
            'lowercase': lambda x: x.lower() if isinstance(x, str) else x,
            'newline_to_space': lambda x: x.replace('\n', ' ') if isinstance(x, str) else x,
            'str_to_pd_NA': lambda x: pd.NA if isinstance(x, str) and re.match(r'^\s*$', x) else x
        }
    
    def _clean_dataframe(self, df, steps, columns=None):
        cols = columns or df.columns
        for step in steps:
            df[cols] = df[cols].map(self.pipeline[step])
        return df
    
    
    def _clean_series(self, series, steps):
        for step in steps:
            series = series.apply(self.pipeline[step])
        return series
    
    def _extract_tables_from_pdf(self,path, pages, flavor='lattice'):
        tables = camelot.read_pdf(path, pages=pages, flavor=flavor)
        return pd.concat([table.df for table in tables], ignore_index=True)
    
    def _get_matching_row_indices(self, df, keywords, thresh):
        regex = SidKimRegex()
        pattern = re.compile("|".join(keywords), re.IGNORECASE)
        matched_rows = []
        for idx, row in df.iterrows():
            match_count = 0
            for cell in row:
                cell_text = regex._normalize_alphanumeric(str(cell))
                if pattern.match(cell_text):  # use .match to anchor to start
                    match_count += 1
                    if match_count >= thresh:
                        matched_rows.append(idx)
                        break
        return matched_rows if matched_rows else [0]
    
    def _get_matching_col_indices(self, df, keywords, thresh=1, match_start_only=False):
        regex = SidKimRegex()
        pattern = re.compile(rf"({'|'.join(keywords)})", re.IGNORECASE)
        matched_cols = []
        for col in df.columns:
            col_text = regex._normalize_alphanumeric(" ".join(map(str, df[col].fillna("").astype(str))))
            match_count = 0
            for _ in pattern.finditer(col_text):
                match_count += 1
                if match_count >= thresh:
                    matched_cols.append(col)
                    break  # Stop scanning this column further

        return matched_cols if matched_cols else [0]


    
    # def _get_matching_row_indices(self,df, keywords, thresh):
    #     regex = SidKimRegex()
    #     pattern = re.compile("|".join(keywords), re.IGNORECASE)
    #     matched_rows = []
    #     for idx, row in df.iterrows():
    #         row_text = regex._normalize_alphanumeric(" ".join(map(str, row)))
    #         match_count = 0
    #         for _ in pattern.finditer(row_text):
    #             match_count += 1
    #             if match_count >= thresh:
    #                 matched_rows.append(idx)
    #                 break  # Stop scanning this row further
    #     # for idx, row in df.iterrows():
    #     #     row_text = regex._normalize_alphanumeric(" ".join(map(str, row)))
    #     #     if matches:=re.findall(pattern, row_text):
    #     #         if len(matches)>=thresh:
    #     #             matched_rows.append(idx)
    #     return matched_rows if matched_rows else [0]
    
    # def _get_matching_col_indices(self,df, keywords, thresh):
    #     regex = SidKimRegex()
    #     pattern = re.compile("|".join(keywords), re.IGNORECASE)
    #     matched_cols = []
    #     for col in df.columns:
    #         col_text = regex._normalize_alphanumeric(" ".join(map(str, df[col].fillna("").astype(str))))
    #         match_count = 0
    #         for _ in re.finditer(pattern, col_text):
    #             match_count += 1
    #             if match_count >= thresh:
    #                 matched_cols.append(col)
    #                 break
    #         # if matches:=re.findall(pattern, col_text):
    #         #     if len(matches)>=thresh:
    #         #         matched_cols.append(col)  # or df.columns.get_loc(col) if you want integer index
    #     return matched_cols if matched_cols else [0]
    
    
    def _get_sub_dataframe(self,df,rs=0,re=-1,cs=0,ce=-1):
        sub_df = df.iloc[rs:re,cs:ce]
        sub_df.columns = range(sub_df.shape[1])  # reset column names to integers
        sub_df = sub_df.reset_index(drop=True)   # reset row index
        return sub_df
    
    def _group_and_collect(self,df, group_col=""):
        final_dict = {}
        regex = SidKimRegex()
        data_cols = df.columns.drop(group_col)
        
        for title, group_df in df.groupby(group_col, sort=False):
            norm_title = regex._normalize_key(title)
            values = [
                cell
                for _, row in group_df.iterrows()
                for cell in row[data_cols]
                if isinstance(cell, str) and cell.strip()
            ]
            final_dict[norm_title] = values

        return final_dict