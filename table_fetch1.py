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
            mode:str = "span",
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

        
        # if mode == "word":
        #     self.items = self._extract_words()
        # elif mode =="span":
        # self.items = self._extract_spans()
        self.items = self._extract_lines()
        
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
                        # horizontal_overlap = not (x1 < bx0 or x0 > bx1)
                        # vertical_inside = (y0 >= by0 and y1 <= by1)

                        # if not (horizontal_overlap and vertical_inside):
                        #     continue


                        horizontal_overlap = not (x1 < bx0 or x0 > bx1)
                        vertical_overlap = not (y1 < by0 or y0 > by1)

                        if not (horizontal_overlap and vertical_overlap):
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
    
    
    def _extract_lines(self):

        items = []
        bbox = self.bbox

        for block in self.page.get_text("dict")["blocks"]:

            if "lines" not in block:
                continue

            for line in block["lines"]:

                x0, y0, x1, y1 = line["bbox"]
                text = " ".join(span["text"] for span in line["spans"]).strip()

                if not text:
                    continue

                # ✅ bbox filtering (OVERLAP — NOT strict)
                if bbox:
                    bx0, by0, bx1, by1 = bbox
                    horizontal_overlap = not (x1 < bx0 or x0 > bx1)
                    vertical_overlap = not (y1 < by0 or y0 > by1)

                    if not (horizontal_overlap and vertical_overlap):
                        continue

                # ✅ SPLIT into pseudo-words
                words = text.split()

                if not words:
                    continue

                # ✅ distribute words across line width
                total_width = x1 - x0
                word_width = total_width / len(words)

                for i, word in enumerate(words):

                    wx0 = x0 + i * word_width
                    wx1 = wx0 + word_width

                    items.append({
                        "x0": wx0, "y0": y0,
                        "x1": wx1, "y1": y1,
                        "text": word,
                        "x_center": (wx0 + wx1) / 2,
                        "y_center": (y0 + y1) / 2,
                        "height": y1 - y0
                    })

        print(f"LINE ITEMS CALC: {items}")

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
        
        print(f"ITEMS CALC: {items}")
        
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
        
        
        # print(items)
        
        if not items:
            print(f"No Items Found.")
            return [],[]

        # STEP 1: sample vertical lines

        page_width = self.page.rect.width
        y_hits = []
        
        bx0, _, bx1, _ = self.bbox
        
        for _ in range(iter):  # stable than 50
            # x = random.uniform(0, page_width)
            x = random.uniform(bx0, bx1)

            for item in items:
                if item["x0"] <= x <= item["x1"]:
                    y_hits.append(item["y_center"])

        if not y_hits: #yeah, no text
            print(f"No y_hits Found.")
            return [],[]

        # STEP 2: cluster y_hits into row anchors
        y_hits.sort()


        heights = [i["height"] for i in items]
        avg_height = sum(heights) / len(heights)
        threshold = avg_height * r_thresh   # adaptive

        rows_y = []
        current = [y_hits[0]]

        for i in range(1, len(y_hits)):
            if abs(y_hits[i] - current[-1]) < threshold:
                current.append(y_hits[i]) 
            else:
                rows_y.append(sum(current) / len(current))
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

        return rows, rows_y

    def col_definite_assign(self, rows):

        #THE EUREKA FUNCTION
        table = []

        x0, _, x1, _ = self.bbox

        # add outer boundaries
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
                row
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
                    return y0   

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
    
        
    # @staticmethod
    # def renew_handler(path:str, config:dict) -> pd.DataFrame:

    #     doc = fitz.open(path)
    #     final_df = pd.DataFrame()

    #     try:

    #         for _, page_config in config.items():
    #             page_no = int(page_config["page_number"]) - 1
    #             bbox = page_config["table_rect"]
    #             x_lines = page_config["columns"]
    #             anchor = None

    #             page = doc[page_no]

    #             if not bbox or not x_lines:
    #                 continue

    #             parser = FetchTable(page, bbox, x_lines)
    #             rows, rows_y = parser.row_detect_sampling()

    #             if not rows:
    #                 continue

    #             if anchor:
    #                 anchor_y = parser.find_anchor_y(anchor)
    #                 rows = parser.cut_rows_above_anchor(
    #                     rows,
    #                     anchor_y
    #                 )

    #             final_df = parser.col_definite_assign(rows)
    #         return final_df

    #     finally:
    #         doc.close()
            
      
      
    @staticmethod
    def bhonsle_handler(path: str, config: dict):

        doc = fitz.open(path)

        final_df = pd.DataFrame()

        # CELL MAP
        final_cell_map = []

        try:

            for _, page_config in config.items():

                page_no = int(page_config["page_number"]) - 1
                bbox = page_config["table_rect"]
                x_lines = page_config["columns"]    

                anchor = None

                page = doc[page_no]
                

                print("Page size:", page.rect)

                words = page.get_text("words")
                print("Sample words:", words[:10])
                
                
                print("PAGE TEXT:\n")
                print(page.get_text("text"))


                if not bbox or not x_lines:
                    continue
                
            
                parser = FetchTable(
                    page,
                    bbox,
                    x_lines
                )

                rows, rows_y = \
                    parser.row_detect_sampling()

                if not rows:
                    continue

                if anchor:
                    anchor_y = parser.find_anchor_y(anchor)
                    rows = parser.cut_rows_above_anchor(rows,anchor_y)

                page_df = parser.col_definite_assign(rows)
                final_df = pd.concat([final_df, page_df], ignore_index=True)
                

                # ADD CELL MAP
                for row_idx, row in enumerate(rows):

                    for col_idx, cell in enumerate(row):

                        if not cell:
                            continue

                        # WORD OBJECT LIST
                        if isinstance(cell, list):

                            texts = []

                            x0s = []
                            y0s = []

                            x1s = []
                            y1s = []

                            for word in cell:

                                if not isinstance(
                                        word,
                                        dict
                                ):
                                    continue

                                texts.append(

                                    str(
                                        word.get(
                                            "text",
                                            ""
                                        )
                                    )
                                )

                                x0s.append(
                                    word.get(
                                        "x0",
                                        0
                                    )
                                )

                                y0s.append(
                                    word.get(
                                        "top",
                                        0
                                    )
                                )

                                x1s.append(
                                    word.get(
                                        "x1",
                                        0
                                    )
                                )

                                y1s.append(
                                    word.get(
                                        "bottom",
                                        0
                                    )
                                )

                            cell_text = " ".join(
                                texts
                            ).strip()

                            if not cell_text:
                                continue

                            bbox = [

                                min(x0s)
                                if x0s else 0,

                                min(y0s)
                                if y0s else 0,

                                max(x1s)
                                if x1s else 0,

                                max(y1s)
                                if y1s else 0
                            ]

                        else:

                            cell_text = str(cell)

                            bbox = [0, 0, 0, 0]

                        # STORE CELL MAP
                        cell_id = f"r{row_idx}_c{col_idx}"

                        final_cell_map.append({

                            "id": cell_id,

                            "row": row_idx,

                            "col": col_idx,

                            "text": cell_text,

                            "bbox": bbox
                        })

            # RETURN BOTH
            return final_df, final_cell_map

        finally:

            doc.close()
           