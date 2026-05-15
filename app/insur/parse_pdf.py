from os import path
import random
import os, re, math,ocrmypdf,time, os # type: ignore
import fitz # type: ignore
from collections import defaultdict
import pandas as pd
from pathlib import Path


from app.insur.parse_regex import *
from app.insur.fund_data import *
from app.utils import Helper
from app.parse_table import PDFTablExtract
from app.logger import get_global_logger, log_exceptions
from app.konstant import (
    get_output_path, get_report_dir,
    get_json_dir
)

class ReadrIns:
    
    
    def __init__(self,params:dict,regex:dict, path:str):
        
        self.log = get_global_logger()
        self.PARAMS = params
        self.PARAM_REGEX = InstrRegex(regex)
        self.EXTRACT_PORTFOLIO = None
        self.UTILS = Helper()
        
        #paths & name
        self.FILE_NAME = Path(path).name
        self.OUTPUT_PATH = get_output_path()
        self.PDF_PATH = path
        self.DRYPATH = os.path.join("app","temp","dry.pdf")
        self.REPORT_PATH = get_report_dir()
        self.JSON_PATH = get_json_dir()
        self.TEXT_ONLY = {}
        
        self.CURR_PDF_PATH = None #str
        self.CURR_WORKING_PAGES = None #dict
    
    #HIGHLIGHT
    @log_exceptions()
    def _get_normal_title(self, path: str, title_regex: str, bbox):
        func = inspect.currentframe().f_code.co_name
        self.log.info(f"▶ Start {func} | file={path}")
        # print(f"▶ Start {func} | file={path}")

        title_detected,escape_regex = {},self.PARAM_REGEX.ESCAPE

        with fitz.open(path) as doc:
            for pgn, page in enumerate(doc):
                try:
                    if path.endswith("_ocr.pdf"):
                        title_text = " ".join(page.get_text("text").split("\n"))
                    else:
                        title_text = " ".join(page.get_text("text", clip=bbox).split("\n"))
                    title_text = re.sub(escape_regex, "", title_text).strip()
                    title_match = re.findall(title_regex, title_text, re.DOTALL)
                    title = (
                        " ".join([_ for _ in title_match[0].strip().split(" ") if _])
                        if title_match else ""
                    )

                    if title:self.log.info(f"Page {pgn} → Title Found: {title}")
                    else:self.log.debug(f"Page {pgn} → No title detected in '{title_text[:50]}...'")
                    title_detected[pgn] = title

                except Exception as e:
                    self.log.warning(f"Partial read failed on page {pgn}: {e}")
                    continue
        self.log.debug(f"{func} complete | {len(title_detected)} pages scanned")
        
        # if path.endswith("FS_ocr.pdf"): 
        #     os.remove(path)
        return title_detected

    @log_exceptions()
    def _get_ocr_title(self, path: str, title_regex: str, bbox):
        func = inspect.currentframe().f_code.co_name
        self.log.info(f"▶ {func} | OCR processing for {self.FILE_NAME}")

        clipped_pdf = path.replace(".pdf", "_clipped.pdf")
        ocr_pdf = path.replace(".pdf", "_ocr.pdf")

        with fitz.open(path) as doc, fitz.open() as new_doc:
            for page_num in range(len(doc)):
                new_page = new_doc.new_page(width=bbox[2] - bbox[0], height=bbox[3] - bbox[1])
                new_page.show_pdf_page(new_page.rect, doc, page_num, clip=bbox)
            new_doc.save(clipped_pdf)

        try:
            # run OCR externally
            time.sleep(1)
            ocrmypdf.ocr(clipped_pdf, ocr_pdf, deskew=True, force_ocr=True)
        except PermissionError as e:
            self.log.warning(f"[Permission Denied] while writing: {ocr_pdf} | {e}")
            return {}
        except Exception:
            raise  # let decorator log unexpected issues
        
        # os.remove(clipped_pdf)
        self.log.debug(f"OCR complete — passing to _get_normal_title()")
        print(ocr_pdf)
        return self._get_normal_title(ocr_pdf, title_regex, bbox)

    @log_exceptions()  
    def _ocr_pdf(self,path:str):
        func = inspect.currentframe().f_code.co_name
        self.log.info(f"▶ {func} | Performing full-page OCR on {self.FILE_NAME}")
        ocr_path = path.replace(".pdf", "_all_ocr.pdf")
        time.sleep(2)
        ocrmypdf.ocr(path, ocr_path, deskew=True, force_ocr=True)
        return ocr_path
    # def _ocr_pdf(self, path: str):
    #     func = inspect.currentframe().f_code.co_name
    #     self.log.info(f"▶ {func} | Performing full-page OCR on {self.FILE_NAME}")

    #     ocr_path = path.replace(".pdf", "_all_ocr.pdf")
    #     self.safe_ocr(path, ocr_path, timeout=90)
    #     self.log.debug(f"OCR completed successfully: {ocr_path}")
    #     return ocr_path

    @log_exceptions()
    def check_and_highlight(self, path, save_htld_pdf=False, save_report=False):
        func = inspect.currentframe().f_code.co_name
        self.log.info(f"▶ Start {func} | file={self.FILE_NAME}")

        data,output_path = [],path.replace(".pdf", "_hltd.pdf")
        title_regex, bbox, ocr = self.PARAMS["title"]['pattern'], self.PARAMS["title"]['bbox'], self.PARAMS["title"]["ocr"]
        financial_terms = self.PARAM_REGEX.FINANCIAL_TERMS

        detected_titles = (
            self._get_ocr_title(path, title_regex, bbox)
            if ocr
            else self._get_normal_title(path, title_regex, bbox)
        )
        self.CURR_PDF_PATH = self._ocr_pdf(path) if self.PARAMS['pdf_ocr'] else path
        
        with fitz.open(self.CURR_PDF_PATH) as doc:
            for pgn, page in enumerate(doc):
                highlight_count, found_indices = 0, []
                for block in page.get_text("dict")["blocks"]:
                    if "lines" not in block:
                        continue
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text = self.UTILS._remove_non_word_space_chars(span["text"])
                            for indice in financial_terms:
                                if re.search(rf"\b{re.escape(indice)}\b", text, re.IGNORECASE):
                                    if indice not in found_indices:
                                        found_indices.append(indice)
                                        highlight_count += 1
                                    page.add_highlight_annot(fitz.Rect(span["bbox"]))
                                    break
                
                # self.log.info("|".join(found_indices))
                
                data.append({
                    "page": pgn,
                    "title": detected_titles.get(pgn, ""),
                    "highlight_count": highlight_count,
                    "indices": found_indices
                })

            if save_htld_pdf:
                doc.save(output_path)

        df_report = pd.DataFrame(data)
        self.log.debug(
            "\n Highlight Report — %s\n%s\n%s",
            self.FILE_NAME,
            df_report.to_string(index=False, justify="center"),
            "-" * 80,
        )

        if save_report:
            ReadrIns.__pdf_report(data, self.REPORTPATH, self.FILE_NAME)

        self.log.info(f"{func} done | total_pages={len(data)}, highlights={sum(d['highlight_count'] for d in data)}")
        
        
        self.CURR_WORKING_PAGES = {
            d["page"]: d["title"]
            for d in data
            if d["title"] and d["highlight_count"] >= self.PARAMS["max_financial_index_highlight"]
        }
        
        # print(self.CURR_WORKING_PAGES)
        
        return self.CURR_WORKING_PAGES, self.CURR_PDF_PATH

    @staticmethod
    def __pdf_report(data, path: str, sheet_name:str):

        excel_path = os.path.join(path, f"{sheet_name.replace(".pdf","")}_REPORT.xlsx")
        df = pd.DataFrame(data)

        if 'indices' in df.columns:
            try:
                df_exp = df["indices"].apply(lambda x: pd.Series(x) if isinstance(x, list) else pd.Series())
                df_exp.columns = [f"idx_{i+1}" for i in range(df_exp.shape[1])]
                df_exp = df_exp.dropna(axis=1, how='all')
                df_final = pd.concat([df.drop(columns=["indices"]), df_exp], axis=1)
            except Exception as e:
                print(f"[ERROR] Expanding indices failed: {e}")
                df_final = df
        else:
            df_final = df

        # if os.path.exists(excel_path):
        #     with pd.ExcelWriter(excel_path, engine="openpyxl", mode='a', if_sheet_exists='replace') as writer:
        #         df_final.to_excel(writer, sheet_name=sheet_name, index=False)
        # else:
        #     with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        #         df_final.to_excel(writer, sheet_name=sheet_name, index=False)
        with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
            df_final.to_excel(writer, sheet_name=sheet_name, index=False)

        return df_final
    
    #EXTRACT 
    def _create_data_entry(self,*args)->dict: 
        return {
            "page":args[0],
            "fundname":args[1],
            "block":args[2]
        }
    
    @log_exceptions()              
    def extract_clipped_data(self, path: str, title: dict, *args) -> list:
        finalData,fund_seen = [],{}
        bboxes = self.PARAMS['clip_bbox'] if not args else args[0]
      
        # try:
        with fitz.open(path) as doc:
            for pgn in title:
                fundName = title.get(pgn, "").strip()
                if not fundName:continue

                page,all_blocks = doc[pgn],[]
                page_bboxes = bboxes.get(str(pgn),[]) if isinstance(bboxes,dict) else bboxes
                for count,bbox in enumerate(page_bboxes): #count for dummy block
                    blocks, seen_blocks = [], set()
                    page_blocks = page.get_text('dict', clip=bbox)['blocks']

                    for block in page_blocks:
                        if block['type'] == 0 and 'lines' in block:
                            block_key_text = []
                            for line in block['lines']:
                                spans = line.get('spans', [])
                                if spans:
                                    block_key_text.append(spans[0]['text'])
                                else:
                                    block_key_text.append("")

                            block_key = (tuple(block['bbox']), tuple(block_key_text))
                            if block_key not in seen_blocks:
                                seen_blocks.add(block_key)
                                blocks.append(block)

                    sorted_blocks = sorted(blocks, key=lambda x: (x['bbox'][1], x['bbox'][0]))

                    # dummy data
                    fontz,colorz = self.PARAMS['data']['font'][0],self.PARAMS['data']['color'][0]
                    sorted_blocks.append(self.PARAM_REGEX._dummy_block(fontz, colorz,count+1))
                    all_blocks.extend(sorted_blocks)

                if fundName in fund_seen:
                    fund_seen[fundName]["block"].extend(all_blocks)
                    fund_seen[fundName]["page"].append(pgn)
                else:
                    new_entry = {"page": [pgn], "fundname": fundName, "block": all_blocks}
                    finalData.append(new_entry)
                    fund_seen[fundName] = new_entry
                        
        # except Exception as e:
            # self.log.error(f"Error in 'extract_clipped_data'",exc_info=True)
            # pass

        return finalData

    @log_exceptions()
    def extract_data_relative_line(self, path: str,title: dict)->list:
      
        finalData,fund_seen = [],{}
        line_x,side = self.PARAMS['line_x'],self.PARAMS['line_side']
        # try:
        with fitz.open(path) as doc:
            
            for pgn in title:
                page, fundName = doc[pgn],title.get(pgn,"")
                left_blocks, right_blocks, seen_blocks = [],[], set()
                page_blocks = page.get_text("dict")["blocks"]
                
                for block in page_blocks:
                    if block['type'] == 0 and 'lines' in block:
                        block_key = id(block) #hash_key

                        for line in block["lines"]:
                            for span in line["spans"]:
                                x0, _ = span["origin"]

                                if side in ["left", "both"] and x0 < line_x and block_key not in seen_blocks:
                                    seen_blocks.add(block_key)
                                    left_blocks.append(block)

                                if side in ["right", "both"] and x0 > line_x and block_key not in seen_blocks:
                                    seen_blocks.add(block_key)
                                    right_blocks.append(block)

                left_blocks.sort(key=lambda x: (x["bbox"][1], x["bbox"][0]))  
                right_blocks.sort(key=lambda x: (x["bbox"][1], x["bbox"][0]))
                
                #adding dummy data
                fontz,colorz = self.PARAMS['data']['font'][0],self.PARAMS['data']['color'][0]
                left_blocks.append(self.PARAM_REGEX._dummy_block(fontz,colorz,1))
                right_blocks.append(self.PARAM_REGEX._dummy_block(fontz,colorz,1))
                
                if side == "both": left_blocks.extend(right_blocks)
                sorted_blocks = left_blocks if side != "right" else right_blocks
                
                if fundName in fund_seen:
                    fund_seen[fundName]["block"].extend(sorted_blocks)
                    fund_seen[fundName]["page"].append(pgn)
                else:
                    new_entry = {"page": [pgn], "fundname": fundName, "block": sorted_blocks}
                    finalData.append(new_entry)
                    fund_seen[fundName] = new_entry
                        
        # except Exception as e:
        #     # self.log.error(f"Error in 'extract_data_relative_line' ",exc_info=True)
        #     pass
            
        return finalData

    def extract_span_data(self, data: list,*args)->list:  # all
      
        finalData = []
        for page in data:
            seen_entries = set()
            pgn, fundName = page['page'], page['fundname']
            all_blocks = [
                [round(span['size']), span['text'].strip(), span['color'], span['origin'], tuple(span['bbox']), span['font']]
                for block in page['block']
                for line in block['lines']
                for span in line.get('spans', [])
                if (entry := (round(span['size']), span['text'].strip(), span['color'], span['origin'], tuple(span['bbox']), span['font'])) not in seen_entries and not seen_entries.add(entry)
            ]
            finalData.append(self._create_data_entry(pgn,fundName,all_blocks))

        return finalData

    #CLEAN
    def _random_suffix(self,length=4): return ''.join(random.choices(string.ascii_lowercase, k=length))
    
    def process_text_data(self, data: list)->list:
      
        stop_words,finalData = self.PARAM_REGEX.STOP_WORDS,[]
        #checkers
        data_cond = self.PARAMS['data']
        size_checker = data_cond['size']
        font_checker = data_cond['font']
        color_checker = data_cond['color']
        font_change = data_cond['update_size']
        
        amc_stop_words = self.PARAMS['stop_words']
        combined_stop_words = set(stop_words) | set(amc_stop_words) #set union
        
        for content in data:
            pgn,fundName,blocks = content['page'],content['fundname'],content['block']
    
            cleaned_blocks = [] #remove stop words
            for block in blocks:
                size, text, *_ = block
                if text.lower() not in combined_stop_words:
                    cleaned_blocks.append(block)

            processed_blocks = [] #update size
            for block in cleaned_blocks:
                size, text, color, origin, bbox, font = block
                conditions = [round(size) in range(size_checker[0], size_checker[1]),color in color_checker,font in font_checker]
                
                if all(conditions):
                    size = font_change  # Update size
                processed_blocks.append([size, text.strip(), color, origin, bbox,font])

            
            temp_nested_blocks, seperate_blocks = [], [] #nest list based on dummy
            for block in processed_blocks:
                size, text, *rest = block
                seperate_blocks.append(block)

                if text.startswith("DUMMY"): 
                    temp_nested_blocks.append(seperate_blocks[:])
                    seperate_blocks = []

            if seperate_blocks:
                temp_nested_blocks.append(seperate_blocks)

            grand_combined_blocks = [] #group & combine
            for select_blocks in temp_nested_blocks:
                grouped_blocks = defaultdict(list)

                for block in select_blocks:
                    y_coord = math.ceil(block[3][1])
                    size = block[0]
                    grouped_blocks[(y_coord, size)].append(block)

                combined_blocks = []
                for key, group in grouped_blocks.items():
                    if key[1] == font_change:
                        combined_text = " ".join(item[1] for item in group).strip()
                        if combined_text: 
                            size, _, color, origin, bbox, font = group[0]
                            combined_blocks.append([size, combined_text, color, origin, bbox, font])
                    else:
                        combined_blocks.extend(group)

                grand_combined_blocks.append(combined_blocks)
            
            flatten_blocks = [block for group in grand_combined_blocks for block in group]
            finalData.append(self._create_data_entry(pgn,fundName,flatten_blocks))

        return finalData

    def create_nested_dict(self,data: list,*args)->list:
      
        header_size, content_size = self.PARAMS['content_size']
        finalData = []
        for content in data:
            pgn,fundName,blocks = content['page'],content['fundname'], content['block']
            nested_dict = {}
            curr_head = "before"
            
            if curr_head not in nested_dict:
                nested_dict[curr_head] = []
                
            for block in blocks:
                size,text, *open = block
                if size == header_size:
                # if  abs(size - header_size) <= 1:
                    base_head = "_".join([i for i in text.strip().split(" ") if i != '']).lower()
                    
                    # Protect reserved key "before"
                    # if base_head in ["before"]:
                    #     base_head = f"{base_head}_{self._random_suffix()}"
                    
                    curr_head = base_head
                    while curr_head in nested_dict:
                        curr_head = f"{base_head}_{self._random_suffix()}"
                    nested_dict[curr_head] = []
                elif size<= content_size and curr_head:
                    nested_dict[curr_head].append(block)
            
            if nested_dict['before'] == []: del nested_dict['before']    
            finalData.append(self._create_data_entry(pgn,fundName,nested_dict))
        return finalData
    
    @log_exceptions()
    def get_data(self, path: str, titles:dict, *args):
        func = inspect.currentframe().f_code.co_name
        self.log.info(f"▶ Start {func} | file={self.FILE_NAME}")

        sanitize_fund,method = self.PARAMS["sanitize_fund"],self.PARAMS['method']
        extracted_data = []
        
        if method in ["line", "both"]:
            data = self.extract_data_relative_line(path, titles)
            extracted_data.extend(self.extract_span_data(data, []))
        
        if method in ["clip", "both"]:
            data = self.extract_clipped_data(path, titles,*args)
            extracted_data.extend(self.extract_span_data(data, []))
        
        clean_data = self.process_text_data(extracted_data) #process & clean
        nested_data = self.create_nested_dict(clean_data)
        
        for page in nested_data:
            page_text = {}
            page_blocks,fundname = page['block'],page['fundname']
            
            if sanitize_fund: #map to clear fund names
                fundname = self.PARAM_REGEX._sanitize_fund(fundname,self.FUND_NAME)
            page['fundname'] = fundname
            
            for key, content in page_blocks.items():
                page_text[key] = [txt[1] for txt in content]
            self.TEXT_ONLY[fundname] = page_text
        return nested_data
    

    def _generate_pdf_from_data(self, data: dict, output_path: str) -> None:
        """Generate PDF from extracted data, page-wise left normalization + safe font fallback."""

        def _to_rgb_tuple(color_int):
            c = color_int & 0xFFFFFF
            r = (c >> 16) & 0xFF
            g = (c >> 8) & 0xFF
            b = c & 0xFF
            return (r / 255.0, g / 255.0, b / 255.0)
        
        pdf_conf = self.PARAM_REGEX.PDF_CONF

        with fitz.open() as doc:
            for header, content_blocks in data.items():
                if not content_blocks:
                    continue

                page = doc.new_page()

                try:
                    page.insert_text(
                        (int(pdf_conf["LEFT_MARGIN"]),int(pdf_conf["TITLE_POSITION"])),
                        header,
                        fontsize=int(pdf_conf["TITLE_FONT_SIZE"]),
                        fontname=str(pdf_conf["DEFAULT_FONT_NAME"]),
                        color=tuple(pdf_conf["TITLE_COLOR"]),
                    )
                except Exception as e:
                    print(f"Error inserting header text: {e}")

                current_y = int(pdf_conf["TITLE_POSITION"]) + int(pdf_conf["TITLE_FONT_SIZE"]) * 2

                # Group words by Y
                lines_dict = defaultdict(list)
                for block in content_blocks:
                    size, text, color, (orig_x, orig_y), bbox, fontname = block
                    snapped_y = min(lines_dict.keys(), key=lambda y: abs(y - orig_y), default=orig_y)
                    if abs(snapped_y - orig_y) <= int(pdf_conf["Y_SNAP_THRESHOLD"]):
                        orig_y = snapped_y
                    lines_dict[orig_y].append((orig_x, size, text, color, fontname))

                sorted_lines = sorted(lines_dict.items(), key=lambda item: item[0])
                adjusted_lines = []
                last_line_bottom = current_y

                for line_y, line_blocks in sorted_lines:
                    line_blocks.sort(key=lambda b: b[0])
                    max_font_size = max(b[1] for b in line_blocks)
                    line_height = max_font_size + int(pdf_conf["MIN_LINE_SPACING"])
                    if line_y < last_line_bottom + line_height:
                        line_y = last_line_bottom + line_height
                    adjusted_lines.append((line_y, line_blocks))
                    last_line_bottom = line_y

                # --- Compute per-page offset dynamically ---
                all_x = [b[0] for _, line_blocks in adjusted_lines for b in line_blocks]
                min_x = min(all_x) if all_x else 0
                target_left = page.rect.width * 0.15   # about 15% in from left edge
                x_offset = target_left - min_x

                # --- Write with page-wise offset ---
                for line_y, line_blocks in adjusted_lines:
                    for orig_x, size, text, color, fontname in line_blocks:
                        x = orig_x + x_offset
                        try:
                            page.insert_text(
                                (x, line_y),
                                text,
                                fontsize=size,
                                fontname=fontname,
                                color=_to_rgb_tuple(color),
                            )
                        except Exception:
                            # fallback font
                            page.insert_text(
                                (x, line_y),
                                text,
                                fontsize=size,
                                fontname=str(pdf_conf["DEFAULT_FONT_NAME"]),
                                color=_to_rgb_tuple(color),
                            )

            doc.save(output_path)
        return output_path

    def _extract_data_from_pdf(self, pdf_path: str, fund: str):
        final_data = {}
        with fitz.open(pdf_path) as doc:  # open from path
            for page in doc:
                lines = page.get_text("text").split("\n")
                if not lines:
                    continue

                header,content_lines = lines[0],lines[1:]
                if header not in final_data:
                    if self._get_prev_text(header) and fund in self.TEXT_ONLY and header in self.TEXT_ONLY[fund]:final_data[header] = self.TEXT_ONLY[fund][header]
                    else:final_data[header] = content_lines
                else:final_data[header].extend(content_lines)
        return final_data
    
    @log_exceptions()
    def get_generated_content(self, data: list):
        func = inspect.currentframe().f_code.co_name
        self.log.info(f"▶ Start {func} | file={self.FILE_NAME}")
        extracted_text = {}

        for content in data:
            pgn, fund, blocks = content['page'], content['fundname'], content['block']
            pdf_path = self._generate_pdf_from_data(blocks,self.DRYPATH)
            extracted_text[fund] = self._extract_data_from_pdf(pdf_path, fund)
            # extracted_text[fund] = self._extract_data_from_pdf(pdf_bytes, fund)
            
            self._update_imp_data(extracted_text[fund], fund, pgn)



        is_portfolio = self.PARAMS.get("port_bbox",None)
        if is_portfolio:
            
            cfg = self.PARAMS["port_bbox"]     
            pth = self.CURR_PDF_PATH
            wrk_pgs = self.CURR_WORKING_PAGES
            
            print(f"WORKING PAGES: {wrk_pgs}")
            
            port_data = ReadrIns.extract_portfolio(wrk_pgs,cfg,pth)
            
            for fund_n, value in extracted_text.items():
                value["portfolio_data"] = port_data[fund_n]
            
        return extracted_text

    @staticmethod
    def extract_portfolio(working_pages:dict,cfg:dict,path:str):
        """
        Full pipeline:
        - Opens PDF
        - Extracts tables using config
        - Returns JSON output (list of dicts)

        Args:
            configs (dict): full JSON config
            key (str): config key (e.g., "star_health")

        Returns:
            list[dict]
        """
        doc = fitz.open(path)
        final_content = {}

        for page_no, fund_name in working_pages.items():
            page = doc[page_no]
            all_dfs = []
            
            for idx,table in enumerate(cfg):

                bbox = tuple(table["bbox"]) if table.get("bbox") else None
                x_lines = table.get("support_lines", [])
                anchor = table.get("anchor_t", "")

                # skip invalid config
                if not bbox or not x_lines:
                    continue

                # --- extract rows ---
                extractor = PDFTablExtract(page, bbox)
                rows = extractor.extract()

                if not rows:
                    continue

                # --- apply anchor ---
                if anchor:
                    anchor_y = extractor.find_anchor_y(anchor)
                    rows = extractor.cut_rows_above_anchor(rows, anchor_y)

                # --- assign columns ---
                df = PDFTablExtract.assign_columns(rows, x_lines)

                df["table"] = f"tbl_{idx}"
                # df["mutual_fund_name"] = fund_name
                all_dfs.append(df)

            # --- combine ---
            if all_dfs:
                final_df = pd.concat(all_dfs, ignore_index=True)
            else:
                final_df = pd.DataFrame()

            #convert to JSON
            result_json = final_df.to_dict(orient="records")
            
            final_content[fund_name] = result_json
            
        doc.close()

        return final_content



    #REFINE
    @log_exceptions()
    def refine_extracted_data(self, extracted_text: dict):
        func = inspect.currentframe().f_code.co_name
        self.log.info(f"▶ Start {func} | file={self.FILE_NAME}")
        primary_refine,header_map = {},{} #keep track of headers after each iteration, its imp
        
        def get_unique_key(base_key: str, data: dict):
            return next((f"{base_key}_{s}" for s in [
                "bravo","charlie","delta","echo","foxtrot","golf","hotel","india","juliett","kilo"
            ] if f"{base_key}_{s}" not in data), "exhausted")

        
        for fund, item in extracted_text.items():
            content_dict = {}
            header_map[fund] = {}
            for head, content in item.items():
                if clean_head:=  self.PARAM_REGEX._header_mapper(head):
                    header_map[fund][head] = clean_head
                    
                    content = self._match_with_patterns(clean_head, content,level = "primary") # applies regex to clean data
                    content = self.PARAM_REGEX._transform_keys(content) #dynamic dict + other -> lowercase
                    key, value = next(iter(content.items()))
        
                    if clean_head in content_dict:
                        unique_key = get_unique_key(clean_head, content_dict)
                        content_dict[unique_key] = value
                    else:
                        content_dict[clean_head] = value
                        
            primary_refine[fund] = content_dict
        # if flatten: #Flatten the dict if true
        primary_refine = {fund: self.PARAM_REGEX._flatten_dict(data) for fund, data in primary_refine.items()}
        
        secondary_refine = {}
        for fund, item in primary_refine.items():
            content_dict = {}
            for head, content in item.items():
                clean_head = header_map[fund].get(head, head)
                content = self._match_with_patterns(clean_head, content,level = "secondary")
                if content is not None:
                    content_dict.update(content)

            secondary_refine[fund] = content_dict
            
        tertiary_refine = {}
        for fund, item in secondary_refine.items():
            content_dict = {}
            for head, content in item.items():
                clean_head = header_map[fund].get(head, head)
                content = self._match_with_patterns(clean_head, content,level = "tertiary")
                if content is not None:
                    content_dict.update(content)
            tertiary_refine[fund] = content_dict
        return tertiary_refine


    #REFINE

    def __metric_ops(self, fund: str, df: dict):
        try:
            new_metrics = {}
            metrics = df.get("metrics", {})
            for metric_key, metric_value in metrics.items():
                new_key = self.PARAM_REGEX._map_metric_keys_to_dict(metric_key) or metric_key
                new_metrics[new_key] = metric_value

            df["metrics"] = self.PARAM_REGEX._populate_all_metrics_in_json(new_metrics)
        except Exception as e:
            self.logger.error(f"__metric_ops → {fund} Metric Error: {e}", exc_info=True)

        return df
    
    def __map_json_ops(self, df: dict):
        return {self.PARAM_REGEX._map_json_keys_to_dict(k) or k: v for k, v in df.items()}
    
    
    
    @log_exceptions()
    def merge_and_select_data(self, data: dict):
        func = inspect.currentframe().f_code.co_name
        self.log.info(f"▶ Start {func} | file={self.FILE_NAME}")
        
        finalData = {}
        regex = self.PARAM_REGEX
        for fund, content in data.items():
            temp = content
            #imp: maintain order
            temp = self._clone_fund_data(temp)
            temp = self._merge_fund_data(temp)
            temp = self._clone_fund_data(temp)
            temp = self._select_by_regex(temp)
            
            if self.MAIN_MAP['map']:
                temp = self.__map_json_ops(temp) #map proper keys
            
            temp = regex._populate_all_indices_in_json(temp) #populate all keys
            temp = regex._transform_keys(temp) #lowercase
            temp = self.__metric_ops(fund,temp)
            
            if self.MAIN_MAP['special']:
                temp = self._apply_special_handling(temp)
                
            temp = self._promote_key_from_dict(temp)
                        
            #format/type convert keep same format
            temp = regex._convert_date_format(temp) #scheme_launch_date yyyymmdd
            temp = regex._format_fund_manager(temp) #clean fund manager
            temp = regex._format_metric_data(fund,temp) #metric
            
            # temp = regex._format_benchmark_data(temp) #str to list
            
            # print(f"->{len(temp["portfolio_data"])}")
            
            finalData[fund] = temp
  
        final_data = regex._format_to_finstinct(finalData,self.FILE_NAME) #mapper to FinStinct
        trim_data = regex.trim_data(final_data)
        return trim_data
