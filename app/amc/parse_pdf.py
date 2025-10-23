import os, re, math,ocrmypdf,time # type: ignore
from app.logger import get_global_logger, log_exceptions
import fitz # type: ignore
from collections import defaultdict
import pandas as pd

from app.amc.parse_regex import *
from app.amc.fund_data import *
from app.utils import Helper
from app.konstant import * #all constants

class Reader:
    def __init__(self,params:dict,path:str):
        
        self.logger = get_global_logger()
        self.PARAMS = params #amc specific
        self.PARAM_REGEX = FundRegex()
        self.UTILS = Helper()
        
        self.FILE_NAME = path.split("\\")[-1] # filename
        self.OUTPUTPATH = OUTPUT_PATH
        self.PDF_PATH = path
        self.DRYPATH = os.path.join(DUMMY_PDF_DIR,"dry.pdf")
        self.REPORTPATH = REPORT_DIR
        self.JSONPATH = JSON_DIR
        self.TEXT_ONLY = {}
        
    #HIGHLIGHT
    @log_exceptions()
    def _get_normal_title(self, path: str, title_regex: str, bbox):
        func = inspect.currentframe().f_code.co_name
        self.logger.trace(f"▶ Start {func} | file={self.FILE_NAME}")

        title_detected,escape_regex = {},self.PARAM_REGEX.ESCAPE

        with fitz.open(path) as doc:
            for pgn, page in enumerate(doc):
                try:
                    title_text = " ".join(page.get_text("text", clip=bbox).split("\n"))
                    title_text = re.sub(escape_regex, "", title_text).strip()
                    title_match = re.findall(title_regex, title_text, re.DOTALL)
                    title = (
                        " ".join([_ for _ in title_match[0].strip().split(" ") if _])
                        if title_match else ""
                    )

                    if title:self.logger.trace(f"Page {pgn} → Title Found: {title}")
                    else:self.logger.debug(f"Page {pgn} → No title detected in '{title_text[:50]}...'")
                    title_detected[pgn] = title

                except Exception as e:
                    self.logger.warning(f"Partial read failed on page {pgn}: {e}")
                    continue
        self.logger.debug(f"📄 {func} complete | {len(title_detected)} pages scanned")
        return title_detected

    @log_exceptions()
    def _get_ocr_title(self, path: str, title_regex: str, bbox):
        func = inspect.currentframe().f_code.co_name
        self.logger.info(f"▶ {func} | OCR processing for {self.FILE_NAME}")

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
            self.logger.warning(f"[Permission Denied] while writing: {ocr_pdf} | {e}")
            return {}
        except Exception:
            raise  # let decorator log unexpected issues

        self.logger.debug(f"OCR complete — passing to _get_normal_title()")
        return self._get_normal_title(ocr_pdf, title_regex, bbox)

    @log_exceptions()
    def _ocr_pdf(self, path: str):
        func = inspect.currentframe().f_code.co_name
        self.logger.info(f"▶ {func} | Performing full-page OCR on {self.FILE_NAME}")

        ocr_path = path.replace(".pdf", "_all_ocr.pdf")
        self.safe_ocr(path, ocr_path, timeout=90)
        self.logger.debug(f"OCR completed successfully: {ocr_path}")
        return ocr_path

    @log_exceptions()
    def check_and_highlight(self, path, save_htld_pdf=False, save_report=False):
        func = inspect.currentframe().f_code.co_name
        self.logger.trace(f"▶ Start {func} | file={self.FILE_NAME}")

        data,output_path = [],path.replace(".pdf", "_hltd.pdf")
        title_regex, bbox, ocr = self.PARAMS["title"]['pattern'], self.PARAMS["title"]['bbox'], self.PARAMS["title"]["ocr"]
        financial_terms = self.PARAM_REGEX.FINANCIAL_TERMS

        detected_titles = (
            self._get_ocr_title(path, title_regex, bbox)
            if ocr
            else self._get_normal_title(path, title_regex, bbox)
        )
        path_pdf = self._ocr_pdf(path) if self.PARAMS['pdf_ocr'] else path
        
        with fitz.open(path_pdf) as doc:
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
                data.append({
                    "page": pgn,
                    "title": detected_titles.get(pgn, ""),
                    "highlight_count": highlight_count,
                    "indices": found_indices
                })

            if save_htld_pdf:
                doc.save(output_path)

        df_report = pd.DataFrame(data)
        self.logger.debug(
            "\n📄 Highlight Report — %s\n%s\n%s",
            self.FILE_NAME,
            df_report.to_string(index=False, justify="center"),
            "-" * 80,
        )

        if save_report:
            Reader.__pdf_report(data, self.REPORTPATH, self.FILE_NAME)

        self.logger.save(f"{func} done | total_pages={len(data)}, highlights={sum(d['highlight_count'] for d in data)}")
        return {
            d["page"]: d["title"]
            for d in data
            if d["title"] and d["highlight_count"] >= self.PARAMS["max_financial_index_highlight"]
        }, path_pdf

    @staticmethod
    def __pdf_report(data, path: str, sheet_name:str):
        file_name = f"amc_report_{datetime.now().strftime('%Y%m%d%H%M')}.xlsx"
        excel_path = os.path.join(path,file_name)
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

        if os.path.exists(excel_path):
            with pd.ExcelWriter(excel_path, engine="openpyxl", mode='a', if_sheet_exists='replace') as writer:
                df_final.to_excel(writer, sheet_name=sheet_name, index=False)
        else:
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
            # self.logger.error(f"Error in 'extract_clipped_data'",exc_info=True)
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
        #     # self.logger.error(f"Error in 'extract_data_relative_line' ",exc_info=True)
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
        self.logger.trace(f"▶ Start {func} | file={self.FILE_NAME}")

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
    
    #PROCESS
    @staticmethod
    def _generate_pdf_from_data(data: dict, output_path: str) -> None:
      
        #constants imported from konstant.py
        
        def _to_rgb_tuple(color_int):
            c = color_int & 0xFFFFFF
            r = (c >> 16) & 0xFF
            g = (c >> 8) & 0xFF
            b = c & 0xFF
            return (r/255.0, g/255.0, b/255.0)
        
        with fitz.open() as doc:
            for header, content_blocks in data.items():
                if not content_blocks:continue
            
                page = doc.new_page()
                try:
                    page.insert_text((LEFT_MARGIN, TITLE_POSITION),header,fontsize=TITLE_FONT_SIZE,fontname=DEFAULT_FONT_NAME,color=TITLE_COLOR,)
                except Exception as e:
                    print(f"Error inserting header text: {e}")

                current_y = TITLE_POSITION + TITLE_FONT_SIZE * 2

                # Group words by approximate Y-line
                lines_dict = defaultdict(list)
                for block in content_blocks:
                    size, text, color, (orig_x, orig_y), bbox, fontname = block
                    
                    # Snap Y values that are close together to a single baseline
                    snapped_y = min(lines_dict.keys(), key=lambda y: abs(y - orig_y), default=orig_y)
                    if abs(snapped_y - orig_y) <= Y_SNAP_THRESHOLD:
                        orig_y = snapped_y
                    
                    lines_dict[orig_y].append((orig_x, size, text, color, fontname))

                # Sort lines by Y position
                sorted_lines = sorted(lines_dict.items(), key=lambda item: item[0])
                adjusted_lines = []
                last_line_bottom = current_y

                for line_y, line_blocks in sorted_lines:
                    # Sort words in line by their X position
                    line_blocks.sort(key=lambda b: b[0])

                    # Determine max font size for line spacing
                    max_font_size = max(b[1] for b in line_blocks)
                    line_height = max_font_size + MIN_LINE_SPACING
                    
                    if line_y < last_line_bottom + line_height:
                        line_y = last_line_bottom + line_height

                    adjusted_lines.append((line_y, line_blocks))
                    last_line_bottom = line_y

                # Insert text while ensuring proper alignment
                for line_y, line_blocks in adjusted_lines:
                    for orig_x, size, text, color, fontname in line_blocks:
                        try:
                            try:
                               page.insert_text((LEFT_MARGIN+ orig_x, line_y),text,fontsize=size,fontname=fontname,color=_to_rgb_tuple(color),)

                            except Exception:
                                page.insert_text((LEFT_MARGIN+ orig_x, line_y),text,fontsize=size,fontname=DEFAULT_FONT_NAME,color=_to_rgb_tuple(color),)
                        except Exception as e:
                            print(f"Error inserting text '{text}' at {(LEFT_MARGIN + orig_x, line_y)}: {e}")

            doc.save(output_path) #bytes
            
        
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
    def get_generated_content(self, data: list, is_table: str = ""):
        func = inspect.currentframe().f_code.co_name
        self.logger.trace(f"▶ Start {func} | file={self.FILE_NAME}")
        extracted_text = {}

        for content in data:
            pgn, fund, blocks = content['page'], content['fundname'], content['block']
            pdf_path = Reader._generate_pdf_from_data(blocks,self.DRYPATH)
            extracted_text[fund] = self._extract_data_from_pdf(pdf_path, fund)
            # extracted_text[fund] = self._extract_data_from_pdf(pdf_bytes, fund)
            
            self._update_imp_data(extracted_text[fund], fund, pgn)


        table_mode = is_table or self.PARAMS.get("table", "") # Section for tabular data (e.g., DSP, BAJAJ, HDFC)
        if table_mode:
            self.logger.info(f"Tabular Data Present. Running:{inspect.currentframe().f_code.co_name}")
            try:
                table_data = self._generate_table_data(self.PDF_PATH, table_mode)
                extracted_text = self.PARAM_REGEX._map_main_and_tabular_data(extracted_text, table_data, self.FUND_NAME)
            except Exception as e:
                self.logger.error(f"'_generate_table_data' Failed",exc_info=True)
                raise
        return extracted_text

    #REFINE
    @log_exceptions()
    def refine_extracted_data(self, extracted_text: dict):
        func = inspect.currentframe().f_code.co_name
        self.logger.trace(f"▶ Start {func} | file={self.FILE_NAME}")
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
    
    #MAP/SELECT
    def __load_ops(self, fund: str, df: dict):
        load_data = df.get("load", {})
        if not isinstance(load_data, dict):
            self.logger.warning(f"[{fund}] load_ops → Invalid type ({type(load_data)})")
            df["load"] = {"entry_load": "", "exit_load": ""}
            return df

        try:
            new_load = []
            for load_key, load_value in load_data.items():
                value = load_value if isinstance(load_value, str) else " ".join(map(str, load_value))
                if re.search(r"(entry|.*entry_load)", load_key, re.IGNORECASE) and value:
                    new_load.append({"comment": value, "type": "entry_load"})
                elif re.search(r"(exit|.*exit_load)", load_key, re.IGNORECASE) and value:
                    new_load.append({"comment": value, "type": "exit_load"})
            df["load"] = new_load
        except Exception as e:
            self.logger.error(f"__load_ops → {fund} Load Error: {e}", exc_info=True)

        return df

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

    def __min_add_ops(self, fund: str, df: dict):
        try:
            new_values = {}
            for key in ["min_amt", "min_addl_amt"]:
                val = df.get(key, {})
                if isinstance(val, str):
                    val = {"amt": val, "thraftr": ""}
                elif not isinstance(val, dict):
                    val = {"amt": "", "thraftr": ""}
                new_values[key] = val.get("amt", "")
                new_values[f"{key}_multiple"] = val.get("thraftr", "")

            df.update(new_values)
        except Exception as e:
            self.logger.error(f"__min_add_ops → {fund} Min/Add Error: {e}", exc_info=True)

        return df

    def __map_json_ops(self, df: dict):
        return {self.PARAM_REGEX._map_json_keys_to_dict(k) or k: v for k, v in df.items()}

    @log_exceptions()
    def merge_and_select_data(self, data: dict):
        func = inspect.currentframe().f_code.co_name
        self.logger.trace(f"▶ Start {func} | file={self.FILE_NAME}")
        
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
                
            temp = self.__min_add_ops(fund,temp)
            temp = regex._populate_all_indices_in_json(temp) #populate all keys
            temp = regex._transform_keys(temp) #lowercase
            temp = self.__load_ops(fund,temp)
            temp = self.__metric_ops(fund,temp)
            
            if self.MAIN_MAP['special']:
                temp = self._apply_special_handling(temp)
                
            temp = self._promote_key_from_dict(temp)
            
            #format/type convert
            temp = regex._remove_rupee_symbol(temp)
            temp = regex._convert_date_format(temp) #scheme_launch_date yyyymmdd
            temp = regex._format_fund_manager(temp) #clean fund manager
            temp = regex._format_amt_data(fund,temp) #min/add formatter
            temp = regex._format_metric_data(fund,temp) #metric
            
            # temp = regex._format_benchmark_data(temp) #str to list
            finalData[fund] = temp
  
        final_data = regex._format_to_finstinct(finalData,self.FILE_NAME) #mapper to FinStinct
        return final_data
