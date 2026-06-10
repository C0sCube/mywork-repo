import re
import random
import fitz # type: ignore
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN #type: ignore

class PDFTablExtract:
    
    def __init__(
        self,
        page,
        bbox,
        x_lines,
        row_iter:int = 60,
        row_thresh:float = 0.7
        
    ):
        
        self.page = page
        self.bbox = bbox
        self.x_lines = x_lines
        self.r_iter = row_iter
        self.r_thresh = row_thresh
        
        self.items = self._extract_words()

    
    def _extract_words(self):
        items = []
        bbox = self.bbox
        words = self.page.get_text("words")
        for w in words:
            x0, y0, x1, y1, text = w[:5]

            text = text.strip()
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

    def extract_row(self)->list[list[dict]]:
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
        # Simple Explanation: Just collect what are the y_coord of each "encased texts (bbox)" containing a text
        # Iteration introduces randomness and 60-70 cover almost all the "encased texts (bbox)"
        # One Word Explanation, "Dimensionality Reduction"
        
        page_width = self.page.rect.width
        y_hits = []

        for _ in range(self.r_iter):  # stable than 50
            x = random.uniform(0, page_width)

            for item in items:
                if item["x0"] <= x <= item["x1"]:
                    y_hits.append(item["y_center"])

        if not y_hits:
            return []

        # STEP 2: cluster y_hits into row anchors
        y_hits.sort()

        # goal: group nearby y coords into same cluster
        #threshold: average text height * intensity decides tolderance, vvimp
               
        heights = [i["height"] for i in items]
        # i.e average height of text abs(y1-y0) 
        avg_height = sum(heights) / len(heights)
        threshold = avg_height * self.r_thresh   #alterable

        
        rows_y = []
        current = [y_hits[0]]

        for i in range(1, len(y_hits)):
            if abs(y_hits[i] - current[-1]) < threshold:
                current.append(y_hits[i])
            else:
                rows_y.append(sum(current) / len(current))
                current = [y_hits[i]]

        rows_y.append(sum(current) / len(current)) # last line

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
            table.extend([""]*4) #just empty space remove later
            # print([i["text"] for i in row]) <- shows output as it is 

        # return as single column df
        # df = pd.DataFrame(table, columns=["row_text"])
        # return df
        return rows


    def extract_col(self,rows, eps=15, min_samples=5):

        
        items = [item for row in rows for item in row]
        if not items:
            print("There are no items.")
            return pd.DataFrame(), []

        
        xs = np.array([i["x_center"] for i in items])
        X = xs.reshape(-1, 1)
        model = DBSCAN(eps=eps, min_samples=min_samples).fit(X)
        labels = model.labels_

        
        clusters = {} # create clusters
        for item, label in zip(items, labels):
            if label == -1:
                continue
            clusters.setdefault(label, []).append(item)

        
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

        col_spans = sorted(col_spans, key=lambda x: x["center"])

        x0, _, x1, _ = self.bbox
        x_lines = [x0] # start
        for i in range(len(col_spans) - 1):
            right_current = col_spans[i]["right"]
            left_next = col_spans[i + 1]["left"]

            boundary = (right_current + left_next) / 2
            x_lines.append(boundary)

        x_lines.append(x1) # end

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

        # items = self.items
        # print(f"COL_SPANS: {col_spans}")
                
        return df


    def col_assign(self, rows):

        #THE EUREKA FUNCTION
        table = []

        x0, _, x1, _ = self.bbox

        # add outer boundaries
        lines = self.x_lines
        x_lines = sorted(lines + [x0, x1])

        
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
                row
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
    
    def find_anchor(self, pattern:str, bottom:bool =False):
        import re

        regex = re.compile(pattern, re.IGNORECASE)
        bbox = self.bbox

        lines_data = []
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

                lines_data.append({
                    "y0": y0,
                    "y1": y1,
                    "text": line_text
                })

        lines_data.sort(key=lambda x: x["y0"], reverse=bottom)

        #STOP AT FIRST SIGHT
        for line in lines_data:
            # print(line)
            if regex.search(line["text"]):
                return line["y1"] if bottom else line["y0"]

        return None


    def cut_rows(self, rows, anchor_y, mode="below"):
        """
        mode:
            "below" → keep rows below anchor (cut above)
            "above" → keep rows above anchor (cut below)
        """
        if anchor_y is None:
            return rows

        new_rows = []
        for row in rows:
            if mode == "below":
                # keep row if ANY part is below anchor
                if any(item["y1"] >= anchor_y for item in row):
                    new_rows.append(row)

            elif mode == "above":
                # keep row if ANY part is above anchor
                if any(item["y0"] <= anchor_y for item in row):
                    new_rows.append(row)

        return new_rows


    def cut_rows_above_anchor(self,rows, anchor_y):
        if anchor_y is None:
            return rows

        new_rows = []

        for row in rows:
            # keep row if ANY item is below anchor
            if any(item["y1"] >= anchor_y for item in row):
                new_rows.append(row)

        return new_rows
    
    def cut_rows_below_anchor(self,rows, anchor_y):
        
        if anchor_y is None:
            return rows

        new_rows = []

        for row in rows:
            # keep row if ANY item is above anchor (excluding the anchor)
            if any(item["y1"] < anchor_y for item in row):
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

                for idx, table in enumerate(config["tables"]):

                    bbox = tuple(table["bbox"]) if table.get("bbox") else None
                    # x_lines = table.get("support_lines", [])
                    anchor = table.get("anchor_t", None)

                    #skip if not there
                    # if not bbox or not x_lines:
                    #     continue
                    
                    if not bbox:
                        continue
                        
                    #call _init_
                    parser = PDFTablExtract(page,bbox)
                        
                    rows = parser.extract_row()
                    if not rows:
                        continue
                        
                    # This is a temp solution, needs robust cuz config
                    # If masking is good then this solves itself
                    if anchor:
                        #Note: search text, if found get y coord, anything above it is waste so remove
                        anchor_y = parser.find_anchor_y(anchor)
                        rows = parser.cut_rows_above_anchor(rows, anchor_y)
                    
                    df = parser.extract_col(rows)

                # add extra data
                    df["page"] = page_no + 1
                    df["table"] = f"tbl_{idx+1}"
                    # all_dfs[page_no] = df
                    all_dfs.append(df)

            doc.close()
            final_df = pd.DataFrame()
            if all_dfs:
                final_df = pd.concat(all_dfs, ignore_index=True)

            return final_df

        except Exception:
            raise
        
        
    