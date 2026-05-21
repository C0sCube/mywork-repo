#29-04-2026 CODE

import re
import random
import pandas as pd
import fitz #type:ignore



class FetchTable:
    
    def __init__(
            self,
            page,
            bbox,
            x_lines,
            mode:str = "word",
            row_sample_iter:int = 60,
            row_sample_thresh:int = 0.6,
            col_sample_iter:int = 60
        ):
        
        self.page = page
        self.bbox = bbox
        self.x_lines = x_lines
        
        self.r_iter = row_sample_iter
        self.c_iter = col_sample_iter
        self.r_thresh = row_sample_thresh

        
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

        # import pprint
        # pprint.pprint(items)
        
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

    def col_definite_assign(self, rows):

        #THE EUREKA FUNCTION
        table = []

        x0, _, x1, _ = self.bbox

        # add outer boundaries
        # | data | anything between two parallel y-lines is part of a column, EUREKA !!
        # x_lines = sorted(self.x_lines + [x0, x1])
        x_lines = self.x_lines
        
        for row in rows:

            # number of regions = gaps between lines
            cols = [[] for _ in range(len(x_lines) - 1)]

            for item in row:

                xc = item["x_center"]
                for idx in range(len(x_lines) - 1):

                    left = x_lines[idx]
                    right = x_lines[idx + 1]

                    if left <= xc < right: #left- leaning, a deliberate choice
                        cols[idx].append(item)
                        break

            # convert items -> text
            row_text = []

            for col in cols:
                col_sorted = sorted(col, key=lambda x: x["x0"])
                text = " ".join(i["text"] for i in col_sorted)

                row_text.append(text)

            table.append(row_text)

        return pd.DataFrame(table)
    
    def col_assign(self,rows, tol=10):
        """
        rows: [[item, item], ...]
        x_lines: [x1, x2, ...]
        """
        x_lines = self.x_lines
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
        
        # Further improvement is regular expressions
        # i.e 
        
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

    def cut_rows_above_anchor(self,rows, anchor_y):
        if anchor_y is None:
            return rows

        new_rows = []

        for row in rows:
            # keep row if ANY item is below anchor
            if any(item["y1"] >= anchor_y for item in row):
                new_rows.append(row)

        return new_rows
    
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

                    bbox = tuple(table["mask_bbox"]) if table.get("mask_bbox") else None
                    x_lines = table.get("column_lines", [])
                    anchor = table.get("anchor", "")

                    #skip if not there
                    if not bbox or not x_lines:
                        continue
                        
                    #call _init_
                    parser = FetchTable(page,bbox,x_lines)
                        
                    rows,rows_y = parser.row_detect_sampling()
                    if not rows:
                        continue

                    if anchor:
                        anchor_y = parser.find_anchor_y(anchor)
                        rows = parser.cut_rows_above_anchor(rows, anchor_y)  
                    df = parser.col_definite_assign(rows)

                # add extra data
                    df["page"] = page_no + 1
                    all_dfs.append(df)

            doc.close()
            
            if all_dfs:
                final_df = pd.concat(all_dfs, ignore_index=True)
            else:
                final_df = pd.DataFrame() 
            
            return final_df # final_df.to_csv(path.replace(".pdf",".csv"))

        except Exception:
            raise

        
    @staticmethod
    def renew_handler(path:str, config:dict) -> pd.DataFrame:

        doc = fitz.open(path)
        final_df = pd.DataFrame()

        try:

            for _, page_config in config.items():
                page_no = int(page_config["page_number"]) - 1
                bbox = page_config["table_rect"]
                x_lines = page_config["columns"]
                anchor = None

                page = doc[page_no]

                if not bbox or not x_lines:
                    continue

                parser = FetchTable(page, bbox, x_lines)
                rows, rows_y = parser.row_detect_sampling()

                if not rows:
                    continue

                if anchor:
                    anchor_y = parser.find_anchor_y(anchor)
                    rows = parser.cut_rows_above_anchor(
                        rows,
                        anchor_y
                    )

                final_df = parser.col_definite_assign(rows)
            return final_df

        finally:
            doc.close()