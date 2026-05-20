import os, re, json, string, shutil, json5, random
import fitz #type:ignore
from datetime import datetime
from collections import defaultdict
import pandas as pd #type:ignore
from typing import List
from uuid import uuid4
from app.logger import get_global_logger

class Helper:
    def __init__(self):
        self.logger = get_global_logger()
    
    @staticmethod
    def delete_file_by_suffix(base_folder: str, suffixes=[ "_clipped.pdf","_ocr.pdf","_all_ocr.pdf","_hltd.pdf"]):
        deleted_files = []

        for dirpath, _, filenames in os.walk(base_folder):
            for file in filenames:
                if any(file.endswith(suffix) for suffix in suffixes):
                    full_path = os.path.join(dirpath, file)
                    try:
                        os.remove(full_path)
                        deleted_files.append(full_path)
                    except Exception as e:
                        print(f"[ERROR] Could not delete {full_path}: {e}")
        return deleted_files
    
    @staticmethod
    def delete_all_files(folder_path):
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            if os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"Failed to delete {file_path}: {e}")



    @staticmethod
    def generate_uid():
        return uuid4().hex

    
    @staticmethod
    def clear_folder(folder_path):
        """Delete all files (not subfolders) inside the given folder."""
        logger = get_global_logger()

        if not os.path.exists(folder_path):
            logger.warning(f"[clear_folder] Folder not found: {folder_path}")
            return

        deleted = 0
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            if os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                    deleted += 1
                except PermissionError:
                    logger.warning(f"Permission denied deleting {file_path}")
                except Exception as e:
                    logger.error(f"Failed to delete {file_path}: {e}")
        logger.info(f"Cleared {deleted} file(s) from {folder_path}")
        
    @staticmethod
    def delete_files(data):
        """Delete all files (not subfolders) inside the given folder."""
        logger = get_global_logger()

        if isinstance(data, dict):
            file_paths = list(data.values())
        elif isinstance(data, list):
            file_paths = data
        elif isinstance(data, str):
            file_paths = [data]
        else:
            logger.error(f"[archive_files] Invalid data type: {type(data)}")
            return

        for filepath in file_paths:
            if os.path.isfile(filepath):
                try:
                    os.remove(filepath)
                except PermissionError:
                    logger.warning(f"Permission denied deleting {filepath}")
                except Exception as e:
                    logger.error(f"Failed to delete {filepath}: {e}")

    @staticmethod
    def archive_files(dest_folder: str, data):
        """Copy one or more files to a destination folder (e.g., processed/ or failed/)."""
        logger = get_global_logger()

        if not os.path.exists(dest_folder):
            os.makedirs(dest_folder, exist_ok=True)
            logger.info(f"Created destination folder: {dest_folder}")

        if isinstance(data, dict):
            file_paths = list(data.values())
        elif isinstance(data, list):
            file_paths = data
        elif isinstance(data, str):
            file_paths = [data]
        else:
            logger.error(f"[archive_files] Invalid data type: {type(data)}")
            return

        copied = 0
        for path in file_paths:
            if not os.path.isfile(path):
                logger.warning(f"File not found, skipping: {path}")
                continue
            try:
                file_name = os.path.basename(path)
                dest_path = os.path.join(dest_folder, file_name)
                shutil.copy2(path, dest_path)
                copied += 1
            except Exception as e:
                logger.error(f"Failed to copy '{path}' → {dest_folder}: {e}")

        logger.info(f"Archived {copied} file(s) to {dest_folder}")

    @staticmethod
    def archive_and_delete_files(dest_folder: str, data):
        """Move one or more files to a destination folder."""
        logger = get_global_logger()

        if not os.path.exists(dest_folder):
            os.makedirs(dest_folder, exist_ok=True)
            logger.info(f"Created destination folder: {dest_folder}")

        if isinstance(data, dict):
            file_paths = list(data.values())
        elif isinstance(data, list):
            file_paths = data
        elif isinstance(data, str):
            file_paths = [data]
        else:
            logger.error(f"[archive_and_delete_files] Invalid data type: {type(data)}")
            return

        moved = 0
        for path in file_paths:
            if not os.path.isfile(path):
                logger.warning(f"File not found, skipping: {path}")
                continue
            try:
                file_name = os.path.basename(path)
                dest_path = os.path.join(dest_folder, file_name)
                shutil.move(path, dest_path)  # atomic move
                moved += 1
                logger.info(f"Moved: {path} → {dest_path}")
            except Exception as e:
                logger.error(f"Failed to move '{path}' → {dest_folder}: {e}")

        logger.info(f"Archived {moved} file(s) to {dest_folder}")


    #JSON UN/LOAD
    @staticmethod
    def create_dir(base_path, *folders):
        dir_path = os.path.join(base_path, *folders)
        os.makedirs(dir_path, exist_ok=True)
        return dir_path
    
    @staticmethod
    def save_json(data: dict, path: str, indent: int = 2):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent)

    @staticmethod
    def load_json(file_path: str):
        if not os.path.exists(file_path):
            return
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
        
    @staticmethod
    def save_json5(data: dict, path: str, indent: int = 2):
        with open(path, "w", encoding="utf-8") as f:
            json5.dump(data, f, indent=indent)

    @staticmethod
    def load_json5(file_path: str):
        if not os.path.exists(file_path):
            return
        with open(file_path, "r", encoding="utf-8") as f:
            return json5.load(f)
        
    @staticmethod
    def load_json_as_string(path: str, indent: int = None) -> str:
        with open(path, "r", encoding="utf-8") as f:
            return json.dumps(json.load(f), indent=indent, ensure_ascii=False)

    @staticmethod
    def load_json5_as_string(path: str, indent: int = None) -> str:
        with open(path, "r", encoding="utf-8") as f:
            return json5.dumps(json5.load(f), indent=indent)

    
    #WRITE TEXT
    @staticmethod
    def save_text(data,path:str):
        if not data:
            print("Empty Data")
            return
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'a', encoding='utf-8') as f:
            if isinstance(data,dict):
                f.writelines(f"{k}:{v}\n" for k,v in data.items())
            elif isinstance(data,list):
                f.writelines(f"{k}\n" for k in data)
            elif isinstance(data,str):
                f.writelines(data)
            else: print("Invalid type")
           
    def debug_save(pdf_bytes: bytes, filename="debug.pdf"):
        """Save in-memory PDF bytes to disk for debugging purposes."""
        with open(filename, "wb") as f:
            f.write(pdf_bytes)
        print(f"[debug] PDF saved to {filename}")
    
    def _clean_leading_noise(self,text: str) -> str:
        if not isinstance(text,str):
            return text
        return re.sub(r'^[\s\n\r\t\\:;\-–—•|]+', '', text).strip()
    
    def _normalize_key(self,text: str) -> str:
        if not isinstance(text,str):
            return text
        text = re.sub(r"[^\w\s\.]", "", text)
        text = re.sub(r"\s+", "_", text)
        return text.strip().lower()
    
    def _normalize_key_to_alnum_underscore(self, text: str) -> str:
        if not isinstance(text, str):
            return text
        text = text.strip().lower()
        text = re.sub(r"[^\w]", "_", text)
        text = re.sub(r"__+", "_", text)
        return text.strip("_")

    def _remove_duplicates(self,text):
        if not text:
            return text
        seen = []
        text = text.split(" ")
        for word in text:
            word = word.lower().strip()
            if word not in seen:
                seen.append(word)
        return " ".join(seen)

    #match type
    def is_numeric(self,text):
        return bool(re.fullmatch(r'[+-]?(\d+(\.\d*)?|\.\d+)', text))

    def is_alphanumeric(self,text):
        return bool(re.fullmatch(r'[A-Za-z0-9]+', text))

    def is_alpha(self,text):
        return bool(re.fullmatch(r'[A-Za-z]+', text))
        
    def _remove_non_word_space_chars(self,text:str)->str:
        if not isinstance(text,str):
            return text
        text = re.sub("[^\\w\\s]", "", text).strip()
        return text
    
    def _normalize_whitespace(self,text:str)->str:
        if not isinstance(text,str):
            return text
        return re.sub(r"\s+", " ", text).strip()
    
    def _normalize_date(self,text:str)->str:
        if not isinstance(text,str):
            return text
        text = re.sub(r"[^A-Za-z0-9\s\.\/\,\-\\]+"," ",text).strip()
        return self._normalize_whitespace(text)
    
    def _normalize_ascii(self, text: str) -> str:
        if not isinstance(text, str):
            return text
        text = re.sub(r"[^\x20-\x7E]+", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    def _normalize_alphanumeric(self, text: str) -> str:
        if not isinstance(text,str):
            return text
        text = re.sub(r"[^a-zA-Z0-9]+", " ", str(text))
        return re.sub(r"\s+", " ", text).strip().lower()
    
    def _normalize_alpha(self, text: str) -> str:
        if not isinstance(text,str):
            return text
        text = re.sub(r"[^a-zA-Z]+", " ", str(text))
        return re.sub(r"\s+", " ", text).strip().lower()

    def _normalize_numeric(self, text: str) -> str:
        if not isinstance(text,str):
            return text
        text = re.sub(r"[^0-9\.]+", " ", str(text))
        return re.sub(r"\s+", " ", text).strip().lower()
    
    #PYMUPDF/FITZ HELPERS
    
    @staticmethod
    def get_pdf_text(path:str):
    
        doc = fitz.open(path)
        text_data = {}
        for pgn in range(doc.page_count):
            page = doc[pgn]
            text = page.get_text("text")
            text = text.encode('utf-8', 'ignore').decode('utf-8')
            data = text.split('\n')
            text_data [pgn] = data
        return text_data
    
    @staticmethod
    def get_clipped_data(input:str, bboxes:list[set]):
    
        document = fitz.open(input)
        final_list = []
        
        for pgn in range(document.page_count):
            page = document[pgn]

            blocks = []
            for bbox in bboxes:
                blocks.extend(page.get_text('dict', clip = bbox)['blocks']) #get all blocks
            
            filtered_blocks = [block for block in blocks if block['type']== 0 and 'lines' in block]
            sorted_blocks = sorted(filtered_blocks, key= lambda x: (x['bbox'][1], x['bbox'][0]))
            
            final_list.append({
            "pgn": pgn,
            "block": sorted_blocks
            })
            
            
        document.close()
        return final_list
    
    @staticmethod
    def get_all_pdf_data(path:str):
    
        doc = fitz.open(path)
        count = doc.page_count
        all_blocks = list()

        for pgn in range(count):
            page = doc[pgn]
            
            blocks = page.get_text('dict')['blocks']
            for line in blocks["lines"]:
                line.update({
                    "uid": Helper.generate_uid()
                })
            images = page.get_images()
            filtered_blocks = [block for block in blocks if block['type']== 0]
            sorted_blocks = sorted(filtered_blocks, key=lambda x: x['bbox'][1])
            all_blocks.append({
                "pgn":pgn,
                "blocks":sorted_blocks,
                "images": images
            })
            
            #draw lines
            
            lines = fitz.Rect()
            
        doc.close()
        
        return all_blocks
    
    @staticmethod
    def draw_lines_on_pdf(pdf_path: str, lines: list, rects:list, pages:list,output_path: str):
        """Open the pdf , draw lines on the mentioned pages
        Args:pdf_path(str) , output_pdf_path (str)
        Returns: nothing, a new pdf created"""
        doc = fitz.open(pdf_path)
        for page_number, page in enumerate(doc, start=1):
            
            height = page.rect.height
            width  = page.rect.width
            if page_number in pages:
                
                # Start drawing on the page
                for line in lines:
                    start, end = line
                    x1, y1 = start
                    x2, y2 = end
                    page.draw_line((x1, y1), (x2, y2))
                    #page.draw_rect((0,20,250,1000))
                
                # Start drawing on the page
                for rec in rects:
                    x0, y0, x1, y1 = rec  
                    rect = fitz.Rect(x0, y0, x1, height) 

                    # Set the rectangle's fill and stroke color
                    shape = page.new_shape()
                    shape.draw_rect(rect)  
                    shape.finish(color=(0.4,0,0), fill=(1, 0.75, 0.8), width=0.8, fill_opacity = .3)  # Pink fill, no border color
                    shape.commit()
            


        doc.save(output_path)
        print(f"Modified PDF saved to: {output_path}")
        #open the file on screen
        import subprocess
        subprocess.Popen([output_path],shell=True)

    @staticmethod
    def draw_boundaries_on_lines(pdf_path: str):
        doc = fitz.open(pdf_path)

        for page in doc:
            blocks = page.get_text("dict")["blocks"]

            for block in blocks:
                if block.get("lines"):
                    for line in block["lines"]:
                        bbox = line["bbox"]

                        page.draw_rect(
                            bbox,
                            color=(0, 1, int(64/255)),  # red
                            width=0.5,
                            overlay=True
                        )

        output_path = pdf_path.replace('.pdf', '_line_hltd.pdf')
        doc.save(output_path)
        doc.close()
        return output_path
    

    @staticmethod
    def fill_boundaries_on_lines(pdf_path: str):

        doc = fitz.open(pdf_path)
        for page in doc:
            shape = page.new_shape() 
            blocks = page.get_text("dict")["blocks"]

            for block in blocks:
                if block.get("lines"):
                    for line in block["lines"]:
                        bbox = fitz.Rect(line["bbox"])
                        shape.draw_rect(bbox)

            shape.finish(
                fill=(0.8, 1, 0.2),      # light red fill
                stroke_opacity=0,        # no border
                fill_opacity=0.7        # transparency
            )

            shape.commit(overlay=True)   # MUST

        output_path = pdf_path.replace(
            '.pdf',
            '_line_filled.pdf'
        )

        doc.save(output_path)
        doc.close()

        return output_path

        
    @staticmethod
    def draw_boundaries_on_pdf(pdf_path: str):
        doc = fitz.open(pdf_path)

        for page in doc:
            blocks = page.get_text("dict")["blocks"]

            for block in blocks:
                bbox = block.get("bbox")

                if bbox:
                    page.draw_rect(
                        bbox,
                        color=(1.0, 0.647, 0.0),
                        width=1.5,
                        overlay=True
                    )

        output_path = pdf_path.replace('.pdf', '_block_hltd.pdf')
        doc.save(output_path)
        doc.close()
        return output_path
        
    @staticmethod
    def draw_span_boundaries(pdf_path: str):
        doc = fitz.open(pdf_path)

        for page in doc:
            blocks = page.get_text("dict")["blocks"]

            for block in blocks:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):

                        bbox = span["bbox"]

                        page.draw_rect(
                            bbox,
                            color=(0, 1, 0),  # green
                            width=1,
                            overlay=True
                        )

        output_path = pdf_path.replace('.pdf', '_span_hltd.pdf')
        doc.save(output_path)
        doc.close()
        return output_path
    
    
    @staticmethod
    def draw_word_boundaries(pdf_path: str):
        doc = fitz.open(pdf_path)

        for page in doc:
            words = page.get_text("words")

            for w in words:
                x0, y0, x1, y1, text = w[:5]

                page.draw_rect(
                    (x0, y0, x1, y1),
                    color=(int(191/255), 0, 1),  # red
                    width=.6,
                    overlay=True
                )

        output_path = pdf_path.replace('.pdf', '_word_hltd.pdf')
        doc.save(output_path)
        doc.close()
        return output_path


    @staticmethod
    def compare_span_vs_word(pdf_path: str):
        doc = fitz.open(pdf_path)

        for page in doc:

            # SPANS → green
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        page.draw_rect(
                            span["bbox"],
                            color=(0, 1, 0),
                            width=1,
                            overlay=True
                        )

            # WORDS → red
            words = page.get_text("words")
            for w in words:
                x0, y0, x1, y1 = w[:4]
                page.draw_rect(
                    (x0, y0, x1, y1),
                    color=(1, 0, 0),
                    width=1,
                    overlay=True
                )

        out = pdf_path.replace(".pdf", "_compare.pdf")
        doc.save(out)
        doc.close()
        return out

    @staticmethod
    def draw_bboxes_on_pdf(pdf_path:str, bbox:tuple):
        
        doc = fitz.open(pdf_path)
        for page in doc:
            page.draw_rect(bbox, color = (1.0,0,1.0), width = 1.5, overlay = False)

        output_path = pdf_path.replace('.pdf', '_bbox_hltd.pdf')
        doc.save(output_path)
        doc.close()
        return output_path
    
    @staticmethod
    def draw_pink_lines(pdf_path:str, gap:int=5):

        doc = fitz.open(pdf_path)
        for page in doc:

            page_width  = page.rect.width
            page_height = page.rect.height

            shape = page.new_shape()

            y = 0
            while y <= page_height:

                shape.draw_line(fitz.Point(0, y),fitz.Point(page_width, y))

                y += gap   # EXACT STEP

            shape.finish(
                color=(1, 0, 0.5),    # pink
                width=0.2
            )

            shape.commit(overlay=True)

        
        output_path = pdf_path.replace('.pdf', '_x_axis_line.pdf')
        doc.saveIncr()
        doc.save(output_path)
        doc.close()
        return output_path


    @staticmethod
    def mask_outside_bboxes(input_pdf, bboxes):
        doc = fitz.open(input_pdf)

        for page in doc:
            page_rect = page.rect

            for bbox in bboxes:
                x0, y0, x1, y1 = bbox

                # Top
                if y0 > page_rect.y0:
                    page.add_redact_annot(
                        fitz.Rect(page_rect.x0, page_rect.y0, page_rect.x1, y0),
                        fill=(1, 1, 1)
                    )

                # Bottom
                if y1 < page_rect.y1:
                    page.add_redact_annot(
                        fitz.Rect(page_rect.x0, y1, page_rect.x1, page_rect.y1),
                        fill=(1, 1, 1)
                    )

                # Left
                if x0 > page_rect.x0:
                    page.add_redact_annot(
                        fitz.Rect(page_rect.x0, y0, x0, y1),
                        fill=(1, 1, 1)
                    )

                # Right
                if x1 < page_rect.x1:
                    page.add_redact_annot(
                        fitz.Rect(x1, y0, page_rect.x1, y1),
                        fill=(1, 1, 1)
                    )

            # Apply AFTER all annots are added
            page.apply_redactions()


        output_path = input_pdf.replace('.pdf', '_bbox_mask.pdf')
        doc.save(output_path)
        doc.close()
        return output_path
    
    
    
    import random

import fitz
import pandas as pd
import random


class PDFTableExtractor:
    def __init__(self, pdf_path):
        self.doc = fitz.open(pdf_path)

    def get_items(self, page, mode="span", bbox=None):
        """
        Extract items from page with optional bbox filtering
        """

        text_dict = page.get_text("dict")
        items = []

        for block in text_dict["blocks"]:
            if "lines" not in block:
                continue

            for line in block["lines"]:

                if mode == "line":
                    x0, y0, x1, y1 = line["bbox"]

                    if bbox and not self._in_bbox((x0, y0, x1, y1), bbox):
                        continue

                    text = " ".join(span["text"] for span in line["spans"])

                    items.append(self._build_item(x0, y0, x1, y1, text))

                elif mode == "span":
                    for span in line["spans"]:
                        x0, y0, x1, y1 = span["bbox"]
                        text = span["text"]

                        if not text.strip():
                            continue

                        if bbox and not self._in_bbox((x0, y0, x1, y1), bbox):
                            continue

                        items.append(self._build_item(x0, y0, x1, y1, text))

        return items

    def _build_item(self, x0, y0, x1, y1, text):
        return {
            "x0": x0,
            "y0": y0,
            "x1": x1,
            "y1": y1,
            "text": text,
            "x_center": (x0 + x1) / 2,
            "y_center": (y0 + y1) / 2,
            "height": y1 - y0
        }

    # def _in_bbox(self, item_bbox, target_bbox):
    #     ix0, iy0, ix1, iy1 = item_bbox
    #     tx0, ty0, tx1, ty1 = target_bbox

    #     return not (ix1 < tx0 or ix0 > tx1 or iy1 < ty0 or iy0 > ty1)
    def _in_bbox(self, item_bbox, target_bbox):
        ix0, iy0, ix1, iy1 = item_bbox
        tx0, ty0, tx1, ty1 = target_bbox

        return (
            ix0 >= tx0 and
            iy0 >= ty0 and
            ix1 <= tx1 and
            iy1 <= ty1
        )

    # =========================================================
    # SIMPLE EXTRACTION (PER PAGE)
    # =========================================================
    def extract_simple_page(self, page, bbox=None, x_thresh = 0.4):
        items = self.get_items(page, mode="span", bbox=bbox)

        if not items:
            return []

        avg_height = sum(i["height"] for i in items) / len(items)
        y_threshold = avg_height * 0.5

        items.sort(key=lambda x: x["y_center"])

        rows = []
        current_row = [items[0]]

        for i in range(1, len(items)):
            if abs(items[i]["y_center"] - current_row[-1]["y_center"]) < y_threshold:
                current_row.append(items[i])
            else:
                rows.append(current_row)
                current_row = [items[i]]

        rows.append(current_row)

        page_width = page.rect.width
        x_threshold = x_thresh * page_width

        table = []

        for row in rows:
            col1, col2 = [], []

            for item in row:
                if item["x_center"] < x_threshold:
                    col1.append(item)
                else:
                    col2.append(item)

            col1.sort(key=lambda x: x["x0"])
            col2.sort(key=lambda x: x["x0"])

            text1 = " ".join(i["text"] for i in col1)
            text2 = " ".join(i["text"] for i in col2)

            table.append([text1, text2])

        df = pd.DataFrame(table)
        # return [df]
        return df

    # =========================================================
    # SAMPLING EXTRACTION (PER PAGE)
    # =========================================================
    def extract_sampling_page(self, page, bbox=None):
        items = self.get_items(page, mode="span", bbox=bbox)

        if not items:
            return []

        page_width = page.rect.width
        y_hits = []

        for _ in range(50):
            x = random.uniform(0, page_width)

            for item in items:
                if item["x0"] <= x <= item["x1"]:
                    y_hits.append(item["y_center"])

        if not y_hits:
            return []

        y_hits.sort()
        rows_y = []
        current = [y_hits[0]]

        threshold = 5

        for i in range(1, len(y_hits)):
            if abs(y_hits[i] - current[-1]) < threshold:
                current.append(y_hits[i])
            else:
                rows_y.append(sum(current) / len(current))
                current = [y_hits[i]]

        rows_y.append(sum(current) / len(current))

        rows = [[] for _ in rows_y]

        for item in items:
            distances = [abs(item["y_center"] - y) for y in rows_y]
            idx = distances.index(min(distances))
            rows[idx].append(item)

        x_threshold = 0.66 * page_width
        table = []

        for row in rows:
            col1, col2 = [], []

            for item in row:
                if item["x_center"] < x_threshold:
                    col1.append(item)
                else:
                    col2.append(item)

            col1.sort(key=lambda x: x["x0"])
            col2.sort(key=lambda x: x["x0"])

            text1 = " ".join(i["text"] for i in col1)
            text2 = " ".join(i["text"] for i in col2)

            table.append([text1, text2])

        df = pd.DataFrame(table)
        # return [df]
        return df

    # =========================================================
    # HANDLER (PDF LEVEL)
    # =========================================================
    def extract(self, page_numbers=None, bboxes=None, method="simple", x_thresh = 0.4):
        """
        MAIN HANDLER

        INPUT:
        - page_numbers: list[int]
        - bbox: (x0, y0, x1, y1)
        - method: "simple" or "sampling"

        OUTPUT:
        {
            page_no: [df1, df2, ...]
        }
        """

        results = {}

        if page_numbers is None:
            page_numbers = range(len(self.doc))
            
        results = {k:[] for k in page_numbers}

        for page_no in page_numbers:
            page = self.doc[page_no]
            for bbox in bboxes:
                if method == "simple":
                    dfs = self.extract_simple_page(page, bbox, x_thresh=x_thresh)
                else:
                    dfs = self.extract_sampling_page(page, bbox)

                results[page_no].append(dfs)

        return results