import os, re,sys, camelot # type: ignore
import pandas as pd
import fitz #type:ignore
import random

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.utils import Helper

# TableParser handles PDF table extraction, cleaning, and formatting.
# It uses Camelot for extracting tables and includes utilities to clean text,
# normalize data, match keywords, and extract meaningful sections from DataFrames.
# Designed to support parsing SID/KIM mutual fund documents.

class TableParser:
    
    def __init__(self):
        
        
        self.utils = Helper()
        
        self.pipeline = {
            'remove_extra_whitespace': lambda x: re.sub(r'\s+', ' ', x) if isinstance(x, str) else x,
            'strip_edges': lambda x: x.strip() if isinstance(x, str) else x,
            'lowercase': lambda x: x.lower() if isinstance(x, str) else x,
            'newline_to_space': lambda x: x.replace('\n', ' ') if isinstance(x, str) else x,
            'str_to_pd_NA': lambda x: pd.NA if isinstance(x, str) and re.match(r'^\s*$', x) else x,
            'normalize_alphanumeric': lambda x: re.sub(r'\s+', ' ', re.sub(r'[^a-zA-Z0-9]+', ' ', x)).strip().lower() if isinstance(x, str) else x,
            'NA_to_str': lambda x: "" if x is pd.NA or pd.isna(x) else x,
            'drop_all_na': lambda df: df.dropna(axis=0, how='all').dropna(axis=1, how='all') if isinstance(df, pd.DataFrame) else df
        }
        
        
    
    def clean_dataframe(self, df, steps, columns=None):
        """Apply a sequence of cleaning functions to specified columns in a DataFrame.
        Args:   df (pd.DataFrame): The input DataFrame to clean.
                steps (list): List of function names (as keys in self.pipeline) to apply.
                columns (list, optional): List of column names to clean. If None, all columns are used.
        Returns: pd.DataFrame: Cleaned DataFrame."""
        
        cols = columns or df.columns
        for step in steps:
            df[cols] = df[cols].map(self.pipeline[step])
        return df
    
    def clean_series(self, series, steps):
        """Apply a sequence of cleaning functions to a pandas Series.
        Args:   series (pd.Series): The input Series to clean.
                steps (list): List of function names (as keys in self.pipeline) to apply.
        Returns:pd.Series: Cleaned Series."""
        
        for step in steps:
            series = series.apply(self.pipeline[step])
        return series
    
    # def extract_tables_from_pdf(self,path, pages, flavor='lattice',stack= True, padding = 1):
    #     """Extract tables from a PDF file using Camelot and return combined DataFrame.
    #     Args:   path (str): Path to the PDF file.
    #             pages (str): Pages to extract (e.g., '1,2' or '1-3').
    #             flavor (str): Camelot flavor to use ('lattice' or 'stream').
    #             stack (bool): Whether to stack all tables vertically.
    #             padding (int): Number of empty rows to add between stacked tables.
    #     Returns:pd.DataFrame: Combined DataFrame of extracted tables."""
        
    #     tables = camelot.read_pdf(path, pages=pages, flavor=flavor)
    #     dfs = [t.df for t in tables]
    #     return self._concat_padding_vertical(*dfs,padding_rows=padding) if stack else self._concat_padding_horizontal(*dfs,padding_rows=padding)
    
    def extract_tables_from_pdf(self, path, pages,flavour = "lines", stack=True, padding=1):

        dfs = []
        if not pages:
            page_count = fitz.open(path).page_count
            pages = [ i for i in range(0,page_count)]
        else:
            pages = [int(p) - 1 for p in pages.split("-") if p.strip()]
        
        

        with fitz.open(path) as doc:
            for p in pages:
                page = doc[p]
                tables = page.find_tables(strategy=flavour)
                for table in tables:
                    df = pd.DataFrame(table.extract())
                    dfs.append(df)

        if not dfs:
            return pd.DataFrame()

        return (
            self._concat_padding_vertical(*dfs, padding_rows=padding)
            if stack
            else self._concat_padding_horizontal(*dfs)
        )

    
    def get_matching_row_indices(self, df, keywords, thresh):
        """Find row indices in a DataFrame that match a set of keywords in at least 'thresh' cells.
        Args:   df (pd.DataFrame): DataFrame to search.
                keywords (list): List of keyword strings to match.
                thresh (int): Minimum number of matching cells required per row.
        Returns:list: List of matching row indices. Returns [0] if none found."""
        
        pattern = re.compile("|".join(keywords), re.IGNORECASE)
        # print(pattern)
        matched_rows = []
        for idx, row in df.iterrows():
            match_count = 0
            for cell in row:
                cell_text =self.utils._normalize_alphanumeric(str(cell))
                # print(cell_text)
                if pattern.search(cell_text):  # use .match to anchor to start
                    match_count += 1
                    if match_count >= thresh:
                        matched_rows.append(idx)
                        break
        return matched_rows if matched_rows else [0]
    
    def get_matching_col_indices(self, df, keywords, thresh=1):
        """Find column names where content matches the given keywords at least 'thresh' times.
        Args:   df (pd.DataFrame): DataFrame to search.
                keywords (list): List of keyword strings to match.
                thresh (int): Minimum number of matches required per column.
                match_start_only (bool): (Unused currently) If True, match only at the start of text.
        Returns:list: List of matching column names. Returns [0] if none found."""
    
        pattern = re.compile(rf"({'|'.join(keywords)})", re.IGNORECASE)
        matched_cols = []
        for col in df.columns:
            col_text = self.utils._normalize_alphanumeric(" ".join(map(str, df[col].fillna("").astype(str))))
            match_count = 0
            for _ in pattern.finditer(col_text):
                match_count += 1
                if match_count >= thresh:
                    matched_cols.append(col)
                    break  # Stop scanning this column further

        return matched_cols if matched_cols else [0]

    def _concat_padding_vertical(self,*dfs, padding_rows=1)->pd.DataFrame:
        result = pd.DataFrame()
        padding = pd.DataFrame([[""] * dfs[0].shape[1]] * padding_rows, columns=dfs[0].columns)
        for i, df in enumerate(dfs):
            result = pd.concat([result, df], ignore_index=True)
            if i < len(dfs) - 1:
                result = pd.concat([result, padding], ignore_index=True)
        return result

    def _concat_padding_horizontal(self,*dfs, padding_cols=1)->pd.DataFrame:
        result = pd.DataFrame()
        num_rows = dfs[0].shape[0]
        padding = pd.DataFrame([[""] * padding_cols] * num_rows)
        for i, df in enumerate(dfs):
            result = pd.concat([result, df], axis=1)
            if i < len(dfs) - 1:
                result = pd.concat([result, padding], axis=1)
        return result
    
    def get_sub_dataframe(self, df, rs=0, re=None, cs=0, ce=None): 
        """Extract a sub-section of the DataFrame with optional row and column slicing.
        Args:
            df (pd.DataFrame): The input DataFrame.
            rs (int): Starting row index (default is 0).
            re (int or None): Ending row index (exclusive). If None, goes till the end.
            cs (int): Starting column index (default is 0).
            ce (int or None): Ending column index (exclusive). If None, goes till the end.
        Returns:pd.DataFrame: A sub-DataFrame with reset index and re-numbered columns."""
        
        max_row, max_col = df.shape

        # Clip indices to valid bounds
        rs = min(rs, max_row - 1) if max_row > 0 else 0
        cs = min(cs, max_col - 1) if max_col > 0 else 0
        re = min(re, max_row) if re is not None else None
        ce = min(ce, max_col) if ce is not None else None

        sub_df = df.iloc[rs:re, cs:ce]
        sub_df.columns = range(sub_df.shape[1])
        sub_df = sub_df.reset_index(drop=True)
        return sub_df
 
    def _drop_na_all(self,dfs,row = True, col = True):
        if row:
            dfs = dfs.dropna(axis=0,how="all")
        if col:
            dfs = dfs.dropna(axis=1,how="all")
        return dfs
    
    def _group_and_collect(self,df, group_col=""):
        final_dict = {}
        data_cols = df.columns.drop(group_col)
        
        for title, group_df in df.groupby(group_col, sort=False):
            norm_title = self.utils._normalize_key(title)
            values = [
                cell
                for _, row in group_df.iterrows()
                for cell in row[data_cols]
                if isinstance(cell, str) and cell.strip()
            ]
            final_dict[norm_title] = values

        return final_dict
    
    

class PDFTablExtract:
    
    def __init__(self,page,bbox, mode = "word"):
        
        self.page = page
        self.bbox = bbox
        if mode == "word":
            self.items = self._extract_words()
        elif mode =="span":
            self.items = self._extract_spans()
        
    def _extract_spans(self):
        
        items = []
        bbox = self.bbox
        
        for block in self.page.get_text("dict")["blocks"]:
            if "lines" not in block:
                continue

            for line in block["lines"]:
                for span in line["spans"]:
                    x0, y0, x1, y1 = span["bbox"]
                    text = span["text"].strip()

                    if not text:
                        continue

                    if bbox:
                        bx0, by0, bx1, by1 = bbox
                        if not (x0 >= bx0 and y0 >= by0 and x1 <= bx1 and y1 <= by1):
                            continue

                    items.append({
                        "x0": x0, "y0": y0,
                        "x1": x1, "y1": y1,
                        "text": text,
                        "x_center": (x0 + x1) / 2,
                        "y_center": (y0 + y1) / 2,
                        "height": y1 - y0
                    })
        
        return items


    def _extract_words(self):
        items = []
        bbox = self.bbox
        words = self.page.get_text("words")  # KEY CHANGE
        for w in words:
            x0, y0, x1, y1, text = w[:5]

            text = text.strip()
            # print(text)

            if not text:
                continue

            if bbox:
                bx0, by0, bx1, by1 = bbox
                if not (x0 >= bx0 and y0 >= by0 and x1 <= bx1 and y1 <= by1):
                    continue

            items.append({
                "x0": x0, "y0": y0,
                "x1": x1, "y1": y1,
                "text": text,
                "x_center": (x0 + x1) / 2,
                "y_center": (y0 + y1) / 2,
                "height": y1 - y0
            })

        return items


    def extract_rows_sampling(self, iteration = 60, y_thresh = 0.6):
        """
        Sampling-based row detection
        Returns DataFrame with 1 column (each row = full text)
        """

        # items = _extract_spans(page,bbox)
        items = self.items
        
        if not items:
            # return pd.DataFrame()
            return []

        # STEP 1: sample vertical lines
        page_width = self.page.rect.width
        y_hits = []

        for _ in range(iteration):  # stable than 50
            x = random.uniform(0, page_width)

            for item in items:
                if item["x0"] <= x <= item["x1"]:
                    y_hits.append(item["y_center"])

        if not y_hits:
            # There is no text data avalaible
            return []

        # STEP 2: cluster y_hits into row anchors
        y_hits.sort()

        heights = [i["height"] for i in items]
        avg_height = sum(heights) / len(heights)
        threshold = avg_height * y_thresh   # adaptive

        rows_y = []
        current = [y_hits[0]]

        for i in range(1, len(y_hits)):
            if abs(y_hits[i] - current[-1]) < threshold:
                current.append(y_hits[i])
            else:
                rows_y.append(sum(current) / len(current))
                current = [y_hits[i]]

        rows_y.append(sum(current) / len(current))

        # STEP 3: assign spans to nearest row
        rows = [[] for _ in rows_y]

        for item in items:
            distances = [abs(item["y_center"] - y) for y in rows_y]
            idx = distances.index(min(distances))
            rows[idx].append(item)

        # STEP 4: convert rows → text
        table = []

        for row in rows:
            row_sorted = sorted(row, key=lambda x: x["x0"])
            text = " ".join(i["text"] for i in row_sorted)
            table.append([text])
            table.extend([""]*4)
            # print([i["text"] for i in row]) <- shows output as it is 

        # return as single column df
        # df = pd.DataFrame(table, columns=["row_text"])
        # return df
        return rows

    def assign_columns_from_rows(self,rows, x_lines, tol=10):
        """
        rows: [[item, item], ...]
        x_lines: [x1, x2, ...]
        """

        table = []

        for row in rows:
            cols = [[] for _ in range(len(x_lines))]

            for item in row:
                assigned = False

                # pass-through check
                for idx, lx in enumerate(x_lines):
                    if item["x0"] - tol <= lx <= item["x1"] + tol: # +/-
                        cols[idx].append(item)
                        assigned = True
                        break

                # proximity fallback
                if not assigned:
                    dists = [abs(item["x_center"] - lx) for lx in x_lines]
                    idx = dists.index(min(dists))
                    cols[idx].append(item)

            # join text per column
            row_text = []
            for col in cols:
                col_sorted = sorted(col, key=lambda x: x["x0"])
                text = " ".join(i["text"] for i in col_sorted)
                row_text.append(text)

            table.append(row_text)

        return pd.DataFrame(table)

    def find_anchor_y(self, keyword):
        def norm(s):
            return re.sub(r"\s+", " ", s).strip().lower()

        keyword = norm(keyword)
        bbox = self.bbox
        
        for block in self.page.get_text("dict")["blocks"]:
            if "lines" not in block:
                continue

            for line in block["lines"]:
                x0, y0, x1, y1 = line["bbox"]

                if bbox:
                    bx0, by0, bx1, by1 = bbox
                    if not (x0 >= bx0 and y0 >= by0 and x1 <= bx1 and y1 <= by1):
                        continue

                line_text = " ".join(span["text"] for span in line["spans"])

                if keyword in norm(line_text):
                    return y0   # top of anchor line

        return None

    def cut_rows_above_anchor(rows, anchor_y):
        if anchor_y is None:
            return rows

        new_rows = []

        for row in rows:
            # keep row if ANY item is below anchor
            if any(item["y1"] >= anchor_y for item in row):
                new_rows.append(row)

        return new_rows
    
    
    
    @staticmethod
    def page_handler(page,config)->pd.DataFrame:
        
        try:
            df = pd.DataFrame()
            
            bbox = tuple(config["bbox"]) if config.get("bbox") else None
            x_lines = config.get("support_lines", [])
            anchor = config.get("anchor_t", None)
            if not bbox or not x_lines:
                return df
            parser = PDFTablExtract(page,bbox)
                
            rows = parser.extract_rows_sampling()
            if not rows:
                return df

            if anchor:
                anchor_y = parser.find_anchor_y(anchor)
                rows = parser.cut_rows_above_anchor(rows, anchor_y)  
            df = parser.assign_columns_from_rows(rows, x_lines)            
            return df
            
        except Exception:
            raise    
    
    
    @staticmethod
    def handler(path:str,config:dict, pages = None)->pd.DataFrame:
        try:
            doc = fitz.open(path)
            fetch_pages = range(doc.page_count)
            all_dfs = []
            
            if pages:
                fetch_pages = pages

            for page_no in fetch_pages:
                page = doc[page_no]

                for table in config["tables"]:

                    bbox = tuple(table["bbox"]) if table.get("bbox") else None
                    x_lines = table.get("support_lines", [])
                    anchor = table.get("anchor_t", None)

                    #skip if not there
                    if not bbox or not x_lines:
                        continue
                        
                    #call _init_
                    parser = PDFTablExtract(page,bbox)
                        
                    rows = parser.extract_rows_sampling()
                    if not rows:
                        continue

                    if anchor:
                        anchor_y = parser.find_anchor_y(anchor)
                        rows = parser.cut_rows_above_anchor(rows, anchor_y)  
                    df = parser.assign_columns_from_rows(rows, x_lines)

                # add extra data
                    df["page"] = page_no + 1
                    # all_dfs[page_no] = df
                    all_dfs.append(df)

            doc.close()
            
            if all_dfs:
                final_df = pd.concat(all_dfs, ignore_index=True)
            else:
                final_df = pd.DataFrame() 
            
            return final_df # final_df.to_csv(path.replace(".pdf",".csv"))

        except Exception:
            raise


#legacy 19-05-2026
# class PDFTablExtract:

#     def __init__(self, page, bbox=None):
#         self.page = page
#         self.bbox = bbox
#         self.items = self._extract_spans()

#     # -------------------------
#     # STEP 0: Extract all spans
#     # -------------------------
#     def _extract_spans(self):
#         items = []

#         for block in self.page.get_text("dict")["blocks"]:
#             if "lines" not in block:
#                 continue

#             for line in block["lines"]:
#                 for span in line["spans"]:
#                     x0, y0, x1, y1 = span["bbox"]
#                     text = span["text"].strip()

#                     if not text:
#                         continue

#                     if self.bbox:
#                         bx0, by0, bx1, by1 = self.bbox
#                         if not (x0 >= bx0 and y0 >= by0 and x1 <= bx1 and y1 <= by1):
#                             continue

#                     items.append({
#                         "x0": x0, "y0": y0,
#                         "x1": x1, "y1": y1,
#                         "text": text,
#                         "x_center": (x0 + x1) / 2,
#                         "y_center": (y0 + y1) / 2,
#                         "height": y1 - y0
#                     })

#         return items

#     # -------------------------
#     # STEP 1 + 2: Detect row anchors
#     # -------------------------

#     def extract_rows_sampling(self,iter = 60):
#         """
#         Sampling-based row detection
#         Returns DataFrame with 1 column (each row = full text)
#         """

#         items = self.items
#         page = self.page
        
#         if not items:
#             return pd.DataFrame()

#         # --- STEP 1: sample vertical lines ---
#         page_width = page.rect.width
#         y_hits = []

#         for _ in range(iter):  # stable than 50
#             x = random.uniform(0, page_width)

#             for item in items:
#                 if item["x0"] <= x <= item["x1"]:
#                     y_hits.append(item["y_center"])

#         if not y_hits:
#             return pd.DataFrame()

#         # --- STEP 2: cluster y_hits into row anchors ---
#         y_hits.sort()

#         heights = [i["height"] for i in items]
#         avg_height = sum(heights) / len(heights)
#         threshold = avg_height * 0.6   # adaptive

#         rows_y = []
#         current = [y_hits[0]]

#         for i in range(1, len(y_hits)):
#             if abs(y_hits[i] - current[-1]) < threshold:
#                 current.append(y_hits[i])
#             else:
#                 rows_y.append(sum(current) / len(current))
#                 current = [y_hits[i]]

#         rows_y.append(sum(current) / len(current))

#         # --- STEP 3: assign spans to nearest row ---
#         rows = [[] for _ in rows_y]

#         for item in items:
#             distances = [abs(item["y_center"] - y) for y in rows_y]
#             idx = distances.index(min(distances))
#             rows[idx].append(item)

#         # --- STEP 4: convert rows → text ---
#         table = []

#         for row in rows:
#             row_sorted = sorted(row, key=lambda x: x["x0"])
#             text = " ".join(i["text"] for i in row_sorted)
#             table.append([text])
#             table.extend([""]*4)

#         # --- return as single column df ---
#         # df = pd.DataFrame(table, columns=["row_text"])
#         # return df
#         return rows
    


#     # -------------------------
#     # COLUMN ASSIGNMENT
#     # -------------------------
#     @staticmethod
#     def assign_columns(rows, x_lines, tol=10):
#         table = []

#         for row in rows:
#             cols = [[] for _ in range(len(x_lines))]

#             for item in row:
#                 assigned = False

#                 # pass-through
#                 for idx, lx in enumerate(x_lines):
#                     if item["x0"] - tol <= lx <= item["x1"] + tol:
#                         cols[idx].append(item)
#                         assigned = True
#                         break

#                 # fallback
#                 if not assigned:
#                     dists = [abs(item["x_center"] - lx) for lx in x_lines]
#                     idx = dists.index(min(dists))
#                     cols[idx].append(item)

#             # join text
#             row_text = []
#             for col in cols:
#                 col_sorted = sorted(col, key=lambda x: x["x0"])
#                 text = " ".join(i["text"] for i in col_sorted)
#                 row_text.append(text)

#             table.append(row_text)

#         return pd.DataFrame(table)

#     # -------------------------
#     # ANCHOR DETECTION
#     # -------------------------
#     def find_anchor_y(self, keyword):
#         def norm(s):
#             return re.sub(r"\s+", " ", s).strip().lower()

#         keyword = norm(keyword)

#         for block in self.page.get_text("dict")["blocks"]:
#             if "lines" not in block:
#                 continue

#             for line in block["lines"]:
#                 x0, y0, x1, y1 = line["bbox"]

#                 if self.bbox:
#                     bx0, by0, bx1, by1 = self.bbox
#                     if not (x0 >= bx0 and y0 >= by0 and x1 <= bx1 and y1 <= by1):
#                         continue

#                 line_text = " ".join(span["text"] for span in line["spans"])

#                 if keyword in norm(line_text):
#                     return y0

#         return None

#     # -------------------------
#     # REMOVE ROWS ABOVE ANCHOR
#     # -------------------------
#     @staticmethod
#     def cut_rows_above_anchor(rows, anchor_y):
#         if anchor_y is None:
#             return rows

#         new_rows = []

#         for row in rows:
#             if any(item["y1"] >= anchor_y for item in row):
#                 new_rows.append(row)

#         return new_rows

#     # -------------------------
#     # FULL PIPELINE
#     # -------------------------
#     def extract(self, keyword=None):
#         rows_y = self.detect_rows()
#         rows = self.build_rows(rows_y)

#         if keyword:
#             anchor_y = self.find_anchor_y(keyword)
#             rows = self.cut_rows_above_anchor(rows, anchor_y)

#         return rows
    
    
    

    # def detect_rows(self):
    #     if not self.items:
    #         return []

    #     page_width = self.page.rect.width
    #     y_hits = []

    #     # sampling
    #     for _ in range(60):
    #         x = random.uniform(0, page_width)

    #         for item in self.items:
    #             if item["x0"] <= x <= item["x1"]:
    #                 y_hits.append(item["y_center"])

    #     if not y_hits:
    #         return []

    #     # clustering
    #     y_hits.sort()
    #     heights = [i["height"] for i in self.items]
    #     avg_height = sum(heights) / len(heights)
    #     threshold = avg_height * 0.6

    #     rows_y = []
    #     current = [y_hits[0]]

    #     for i in range(1, len(y_hits)):
    #         if abs(y_hits[i] - current[-1]) < threshold:
    #             current.append(y_hits[i])
    #         else:
    #             rows_y.append(sum(current) / len(current))
    #             current = [y_hits[i]]

    #     rows_y.append(sum(current) / len(current))

    #     return rows_y

    # -------------------------
    # STEP 3: Assign spans to rows
    # -------------------------
    # def build_rows(self, rows_y):
    #     rows = [[] for _ in rows_y]

    #     for item in self.items:
    #         distances = [abs(item["y_center"] - y) for y in rows_y]
    #         idx = distances.index(min(distances))
    #         rows[idx].append(item)

    #     return rows

    # -------------------------
    # STEP 4: Convert rows to text
    # -------------------------
    # def rows_to_text(self, rows):
    #     table = []

    #     for row in rows:
    #         row_sorted = sorted(row, key=lambda x: x["x0"])
    #         text = " ".join(i["text"] for i in row_sorted)
    #         table.append(text)

    #     return pd.DataFrame(table, columns=["row_text"])