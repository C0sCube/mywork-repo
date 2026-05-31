#29-04-2026 CODE

import re
import random
import pandas as pd
import fitz #type:ignore
import numpy as np
from sklearn.cluster import DBSCAN



class FetchTable:
    
    def __init__(
            self,
            page,
            bbox,
            x_lines = None,
            row_sample_iter:int = 60,
            row_sample_thresh:int = 0.7,
        ):
        
        self.page = page
        self.bbox = bbox
        self.x_lines = x_lines
        
        self.r_iter = row_sample_iter
        self.r_thresh = row_sample_thresh

        self.items = self._extract_words()

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
                # legacy: take only text inside the bbox
                # if not (x0 >= bx0 and y0 >= by0 and x1 <= bx1 and y1 <= by1):
                #     continue
                
                # latest: x-axis overlap allowed
                # further improvement - not x0,x1 or y0,y1 but x_center,y_center
                horizontal_overlap = not (x1 < bx0 or x0 > bx1)
                vertical_inside = (y0 >= by0 and y1 <= by1)

                if not (horizontal_overlap and vertical_inside):
                    continue

            items.append({
                "x0": x0, "y0": y0,
                "x1": x1, "y1": y1,
                "text": text,
                "x_center": (x0 + x1) / 2,
                "y_center": (y0 + y1) / 2,
                "height": y1 - y0
            })

        print(f"THE ITEMS:{items[:5]}")
        
        return items

    def row_detect_sampling(self):
        """
        Sampling-based row detection
        Returns DataFrame with 1 column (each row = full text)
        """

        # items = _extract_spans(page,bbox)
        items = self.items
        iter = self.r_iter
        r_thresh = self.r_thresh
        
        if not items:
            return []

        # STEP 1: sample vertical lines
        # Simple Explanation: Just collect what are the y_coord of each "encased texts (bbox)" containing a text
        # Iteration introduces randomness and 60-70 cover almost all the "encased texts (bbox)"
        # One Word Explanation, "Dimensionality Reduction"
        page_width = self.page.rect.width
        y_hits = []

        for _ in range(iter):  # stable than 50
            x = random.uniform(0, page_width)

            for item in items:
                if item["x0"] <= x <= item["x1"]:
                    y_hits.append(item["y_center"])

        if not y_hits: #yeah, no text
            return []

        # STEP 2: cluster y_hits into row anchors
        y_hits.sort()

        # Above steps tell us how our text is located on a y-axis  we use this to find our lines(rows) parallel to x-axis.
        # Those lines eventually become rows or define rows
        # Do we really need a threshold ??
        heights = [i["height"] for i in items]
        avg_height = sum(heights) / len(heights) # i.e average height of text abs(y1-y0) 
        threshold = avg_height * r_thresh   # adaptive

        rows_y = []
        current = [y_hits[0]]

        for i in range(1, len(y_hits)):
            if abs(y_hits[i] - current[-1]) < threshold:
                current.append(y_hits[i]) #this value is not the candidate of n+1 row
            else:
                rows_y.append(sum(current) / len(current)) #this one is so lets calcuate the average 
                current = [y_hits[i]] #reset

        rows_y.append(sum(current) / len(current)) #last line

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
            # table.extend([""]*4)
            # print([i["text"] for i in row]) <- shows output as it is 

        # return as single column df: remove in production
        # df = pd.DataFrame(table, columns=["row_text"])
        # return df
        return rows, rows_y

    def auto_column_assign(self,rows, bbox, eps=15, min_samples=5):

        # ---- flatten all items ----
        items = [item for row in rows for item in row]

        if not items:
            print("There are no items.")
            return pd.DataFrame(), []

        # ---- extract x_centers ----
        xs = np.array([i["x_center"] for i in items])

        # ---- DBSCAN clustering ----
        X = xs.reshape(-1, 1)
        model = DBSCAN(eps=eps, min_samples=min_samples).fit(X)
        labels = model.labels_

        # ---- build clusters ----
        clusters = {}
        for item, label in zip(items, labels):
            if label == -1:
                continue
            clusters.setdefault(label, []).append(item)

        # ---- compute percentile spreads ----
        col_spans = []

        for label, cluster_items in clusters.items():
            c_xs = np.array([i["x_center"] for i in cluster_items])

            left = np.percentile(c_xs, 5)
            right = np.percentile(c_xs, 95)
            center = np.mean(c_xs)

            col_spans.append({
                "center": center,
                "left": left,
                "right": right
            })

        # ---- sort columns left → right ----
        col_spans = sorted(col_spans, key=lambda x: x["center"])

        # ---- build x_lines using bbox ----
        x0, _, x1, _ = bbox

        x_lines = [x0]

        for i in range(len(col_spans) - 1):
            right_current = col_spans[i]["right"]
            left_next = col_spans[i + 1]["left"]

            boundary = (right_current + left_next) / 2
            x_lines.append(boundary)

        x_lines.append(x1)

        # ---- assign items into columns ----
        table = []

        for row in rows:
            cols = [[] for _ in range(len(x_lines) - 1)]

            for item in row:
                xc = item["x_center"]

                for i in range(len(x_lines) - 1):
                    if x_lines[i] <= xc < x_lines[i+1]:
                        cols[i].append(item)
                        break

            # convert to text
            row_text = []
            for col in cols:
                col_sorted = sorted(col, key=lambda x: x["x0"])
                text = " ".join(i["text"] for i in col_sorted)
                row_text.append(text)

            table.append(row_text)

        df = pd.DataFrame(table)

        items = self.items
        #set correct lines
        self.x_lines = x_lines
        
        return df, x_lines, col_spans, items
    

    def col_assign_debug(self, rows):
        """
        Column-first debug structure:
        {
            col_index: [
                { row_index: i, items: [...] },
                ...
            ]
        }
        """

        x_lines = self.x_lines
        n_cols = len(x_lines) - 1

        # initialize column container
        debug_cols = {
            c_idx: [] for c_idx in range(n_cols)
        }

        for r_idx, row in enumerate(rows):

            # temporary storage for this row per column
            row_cols = [[] for _ in range(n_cols)]

            for item in row:
                xc = item["x_center"]

                for c_idx in range(n_cols):
                    left = x_lines[c_idx]
                    right = x_lines[c_idx + 1]

                    if left <= xc < right:
                        row_cols[c_idx].append(item)
                        break

            # push row-wise data into column-wise structure
            for c_idx in range(n_cols):
                col_items = sorted(row_cols[c_idx], key=lambda x: x["x0"])

                debug_cols[c_idx].append({
                    "row_index": r_idx,
                    "items": col_items
                })

        return debug_cols
            
    @staticmethod
    def excel_handler(path:str, config:dict) -> pd.DataFrame:

        doc = fitz.open(path)
        final_data = {}    

        try:

            for _, conf in config.items():
                
                for tbl, page_config in enumerate(conf):
                    
                    print(f"CONFIG DUDE: {page_config}")
                    # final_df = pd.DataFrame()
                    page_no = int(page_config["page_number"]) - 1
                    bbox = page_config["table_rect"]
                    x_lines = page_config["columns"]
                    

                    page = doc[page_no]
                    print(f"PAGE NO: {page_no}, TBLE: {tbl}")
                    print(f"BBOX: {bbox}")
                    # print(f"X_LINES: {x_lines}")
                    
            
                    if not bbox or not x_lines:
                        continue

                    parser = FetchTable(page, bbox, x_lines)
                    rows, rows_y = parser.row_detect_sampling()
                    # # rows = parser.row_detect_sampling()
                    
                    if not rows:
                        print("There are no ROWS.")
                        continue
                    
                        
                    # final_df, items = parser.col_definite_assign(rows)
                    
                    print("USING AUTO COLUMN")
                    final_df, x_lines, col_spans, items = parser.auto_column_assign(
                        rows,
                        bbox,
                        eps=15
                    )

                    
                    print(f"X_LINES FOUND: {x_lines}")
                    print(f"COLSPANS FOUND: {col_spans}")
                    
                    
                    debug_c = parser.col_assign_debug(rows)
                    print(f"DEBUG: {debug_c}")
                    
                    if page_no not in final_data:
                        final_data[page_no] = [
                            {   
                                "page":page_no,
                                "table":tbl+1,
                                "df": final_df,
                                "debug_c":debug_c,
                                "items":items
                            }
                        ]
                    else:
                        final_data[page_no].append(
                            {   
                                "page":page_no,
                                "table":tbl+1,
                                "df": final_df,
                                "debug_c":debug_c,
                                "items":items
                            }
                        )
                                    
            return final_data
        finally:
            doc.close()

            
        