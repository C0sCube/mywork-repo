import os, re, math, json, inspect,sys, ocrmypdf,time, tempfile # type: ignore
import fitz # type: ignore
from collections import defaultdict

from app.parse_regex import *
from app.fund_data import *
from app.utils import *

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.config_loader import *

conf = get_config() #path to paths.json
class Reader:
    def __init__(self,params:dict,amc_id:str,path:str):
    
        self.PARAMS = params #amc specific paramaters
        self.FILE_NAME = path.split("\\")[-1] # filename requried later for json
        self.OUTPUTPATH = conf["output_path"]
        self.PDF_PATH = path #amc factsheet pdf path
        self.DRYPATH = os.path.join(self.OUTPUTPATH, conf["output"]["dry"])
        self.REPORTPATH = os.path.join(self.OUTPUTPATH, conf["output"]["rep"])
        self.JSONPATH = os.path.join(self.OUTPUTPATH, conf["output"]["json"])
        self.TEXT_ONLY = {}
        
        for output_path in [self.DRYPATH, self.JSONPATH]: # self.REPORTPATH
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    #HIGHLIGHT
    def _get_normal_title(self, path:str,regex:str,bbox):
        print(f"Function Running: {inspect.currentframe().f_code.co_name}")
        print(f"Regex: {regex}")
        title_detected = {}
        with fitz.open(path) as doc:
            for pgn, page in enumerate(doc):
                title_text = " ".join(page.get_text("text", clip=bbox).split("\n"))
                title_text = re.sub(FundRegex().ESCAPE, "", title_text).strip()
                # print(title_text)
                title_match = re.findall(regex, title_text, re.DOTALL)
                title = " ".join([_ for _ in title_match[0].strip().split(" ") if _ ]) if title_match else ""
                # print(title)
                if title:
                    # print(f"{pgn:02d} -- {title}")
                    print(f"{pgn:02d} -- {title.encode('cp1252', 'replace').decode('cp1252')}")
                title_detected[pgn] = title
        return title_detected
                
    def _get_ocr_title(self,path:str,regex:str,bbox):
        print(f"Function Running: {inspect.currentframe().f_code.co_name}")
        clipped_pdf = path.replace(".pdf", "_clipped.pdf")
        ocr_pdf = path.replace(".pdf", "_ocr.pdf")
        
        try:
            with fitz.open(path) as doc:
                with fitz.open() as new_doc:
                    for page_num in range(len(doc)):
                        new_page = new_doc.new_page(width=bbox[2] - bbox[0], height=bbox[3] - bbox[1])
                        new_page.show_pdf_page(new_page.rect, doc, page_num, clip=bbox)
                    new_doc.save(clipped_pdf)
            
            # temp_clips = []
            # with fitz.open(path) as doc:
            #     for page_num in range(len(doc)):
            #         page = doc.load_page(page_num)
            #         clip_doc = fitz.open()
            #         new_page = clip_doc.new_page(width=bbox[2] - bbox[0], height=bbox[3] - bbox[1])
            #         new_page.show_pdf_page(new_page.rect, doc, page_num, clip=bbox)
            #         tmp_page_path = clipped_pdf.replace(".pdf", f"_{page_num}.pdf")
            #         clip_doc.save(tmp_page_path)
            #         clip_doc.close()
            #         temp_clips.append(tmp_page_path)
        
            # merged = fitz.open()
            # for p in temp_clips:
            #     with fitz.open(p) as clip_pdf:
            #         merged.insert_pdf(clip_pdf)
            # merged.save(clipped_pdf)
            # merged.close()

            # for p in temp_clips:
            #     os.remove(p)

            time.sleep(2)
            ocrmypdf.ocr(clipped_pdf, ocr_pdf, deskew=True, force_ocr=True)
            return self._get_normal_title(ocr_pdf,regex,bbox)
        
        except PermissionError as e:
            print(f"[ERROR] Permission denied: {e}")
            return {}
        finally: 
            # for temp_file in [clipped_pdf, ocr_pdf]:
            #     try:
            #         os.remove(temp_file)
            #     except Exception as e:
            #         print(f"[WARN] Could not delete temp file {temp_file}: {e}")
            pass
    
    def _ocr_pdf(self,path:str):
        print(f"Function Running: {inspect.currentframe().f_code.co_name}")
        ocr_path = path.replace(".pdf", "_all_ocr.pdf")
        time.sleep(2)
        ocrmypdf.ocr(path, ocr_path, deskew=True, force_ocr=True)
        return ocr_path
    
    def check_and_highlight(self, path: str):
        print(f"Function Running: {inspect.currentframe().f_code.co_name}")
        data = []
        output_path = path.replace(".pdf", "_hltd.pdf")
        regex = FundRegex()
        title_regex,bbox,ocr = self.PARAMS["title"]['pattern'],self.PARAMS["title"]['bbox'],self.PARAMS["title"]["ocr"]
        
        #detect title
        detected_titles = self._get_ocr_title(path,title_regex,bbox) if ocr else self._get_normal_title(path,title_regex,bbox)
        
        path_pdf = self._ocr_pdf(path) if self.PARAMS['pdf_ocr'] else path
        with fitz.open(path_pdf) as doc:
            indices = regex.FINANCIAL_TERMS
            for pgn, page in enumerate(doc):
                highlight_count,found_indices = 0,[]
                blocks = page.get_text("dict")["blocks"]
                for block in blocks:
                    if "lines" not in block:
                        continue
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text = regex._remove_non_word_space_chars(span["text"])
                            for indice in indices:
                                if re.search(rf"\b{re.escape(indice)}\b", text,re.IGNORECASE):
                                    if indice not in found_indices:
                                        found_indices.append(indice)
                                        highlight_count += 1
                                    page.add_highlight_annot(fitz.Rect(span["bbox"]))
                                    break
                data.append({"page": pgn,"title": detected_titles[pgn],"highlight_count": highlight_count,"indices": found_indices})
        #     doc.save(output_path)
        #     print(f"\tHighlighted PDF at: {output_path}")
        # Helper._save_pdf_data(data, self.REPORTPATH)

        return {
            d["page"]: d["title"]
            for d in data
            if d["title"] and d["highlight_count"] >= self.PARAMS["max_financial_index_highlight"]
        },path_pdf
    
    #EXTRACT 
    def _create_data_entry(self,*args)->dict:
        return {"page":args[0],"fundname":args[1],"block":args[2]}
                   
    def extract_clipped_data(self, path: str, title: dict, *args) -> list:
        print(f"Function Running: {inspect.currentframe().f_code.co_name}")
        finalData = []
        fund_seen = {}
        bboxes = self.PARAMS['clip_bbox'] if not args else args[0]

        with fitz.open(path) as doc:
            for pgn in title:
                fundName = title.get(pgn, "").strip()
                if not fundName:
                    continue

                page = doc[pgn]
                all_blocks = []
                for count,bbox in enumerate(bboxes): #count for dummy block
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
                    fontz = self.PARAMS['data']['font'][0]
                    colorz = self.PARAMS['data']['color'][0]
                    sorted_blocks.append(FundRegex()._dummy_block(fontz, colorz,count))
                    all_blocks.extend(sorted_blocks)

                if fundName in fund_seen:
                    fund_seen[fundName]["block"].extend(all_blocks)
                    fund_seen[fundName]["page"].append(pgn)
                else:
                    new_entry = {"page": [pgn], "fundname": fundName, "block": all_blocks}
                    finalData.append(new_entry)
                    fund_seen[fundName] = new_entry 

        return finalData

    def extract_data_relative_line(self, path: str,title: dict)->list:
        print(f"Function Running: {inspect.currentframe().f_code.co_name}")
        with fitz.open(path) as doc:
            finalData = []
            fund_seen = {}
            line_x = self.PARAMS['line_x']
            side = self.PARAMS['line_side']
            
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
                fontz = self.PARAMS['data']['font'][0]
                colorz = self.PARAMS['data']['color'][0]
                left_blocks.append(FundRegex()._dummy_block(fontz,colorz,1))
                right_blocks.append(FundRegex()._dummy_block(fontz,colorz,1))
                
                if side == "both":
                    left_blocks.extend(right_blocks)

                sorted_blocks = left_blocks if side != "right" else right_blocks
                
                if fundName in fund_seen:
                    fund_seen[fundName]["block"].extend(sorted_blocks)
                    fund_seen[fundName]["page"].append(pgn)
                else:
                    new_entry = {"page": [pgn], "fundname": fundName, "block": sorted_blocks}
                    finalData.append(new_entry)
                    fund_seen[fundName] = new_entry
        return finalData

    def extract_span_data(self, data: list,*args)->list:  # all
        print(f"Function Running: {inspect.currentframe().f_code.co_name}")
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
    def _random_suffix(self,length=4):
        return ''.join(random.choices(string.ascii_lowercase, k=length))
    
    def process_text_data(self, data: list)->list:
        print(f"Function Running: {inspect.currentframe().f_code.co_name}") 
        stop_words,finalData = FundRegex().STOP_WORDS,[]
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
                conditions = [
                    round(size) in range(size_checker[0], size_checker[1]),
                    color in color_checker,
                    font in font_checker,
                ]
                
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
        print(f"Function Running: {inspect.currentframe().f_code.co_name}")
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
            
            # print("Before block contents:", nested_dict['before'])
            if nested_dict['before'] == []:
                del nested_dict['before']    
            
            finalData.append(self._create_data_entry(pgn,fundName,nested_dict))

        return finalData
    
    # def get_data_via_line(self,path:str,pages:list, side:str, title:dict):
        
    #     data = self.extract_data_relative_line(path,pages,side,title)
    #     data = self.extract_span_data(data,[])
    #     clean_data = self.process_text_data(data)
    #     nested = self.create_nested_dict(clean_data)
    #     return nested
    
    # def get_data_via_clip(self,path:str,pages:list, title:dict, *args): #args bcz pass clip boox externally
        
    #     data = self.extract_clipped_data(path,pages,title, *args)
    #     data = self.extract_span_data(data,[])
    #     clean_data = self.process_text_data(data)
    #     nested = self.create_nested_dict(clean_data)
    #     return nested
    
    def get_data(self, path: str, titles:dict):
        print(f"Function Running: {inspect.currentframe().f_code.co_name}")
        method = self.PARAMS['method'] #clip/line/both
        sanitize_fund = self.PARAMS["sanitize_fund"]
        extracted_data = []
        
        regex = FundRegex()
        
        if method in ["line", "both"]:
            data = self.extract_data_relative_line(path, titles)
            extracted_data.extend(self.extract_span_data(data, []))
        
        if method in ["clip", "both"]:
            data = self.extract_clipped_data(path, titles)
            extracted_data.extend(self.extract_span_data(data, []))
        
        clean_data = self.process_text_data(extracted_data) #process & clean
        nested_data = self.create_nested_dict(clean_data)
        
        for page in nested_data:
            page_text = {}
            page_blocks,fundname = page['block'],page['fundname']
            
            if sanitize_fund: #map to clear fund names
                fundname = regex._sanitize_fund(fundname,self.FUND_NAME)
            page['fundname'] = fundname
            
            for key, content in page_blocks.items():
                page_text[key] = [txt[1] for txt in content]
            self.TEXT_ONLY[fundname] = page_text
        # print(self.TEXT_ONLY)
        return nested_data
    
    #PROCESS
    @staticmethod
    def _generate_pdf_from_data(data: dict, output_path: str) -> None:
        # print(f"Function Running: {inspect.currentframe().f_code.co_name}")
        regex = FundRegex()
        with fitz.open() as doc:
            TITLE_FONT_SIZE = 24
            TITLE_POSITION = 72
            TITLE_COLOR = (0, 0, 1)
            DEFAULT_FONT_NAME = "helv"
            LEFT_MARGIN = 32        # Left margin for alignment
            MIN_LINE_SPACING = 2     # Extra space between lines
            Y_SNAP_THRESHOLD = 3     # If two words are within 3 units, snap to same Y

            for header, content_blocks in data.items():
                page = doc.new_page()

                try:
                    page.insert_text(
                        (LEFT_MARGIN, TITLE_POSITION),
                        header,
                        fontsize=TITLE_FONT_SIZE,
                        fontname=DEFAULT_FONT_NAME,
                        color=TITLE_COLOR,
                    )
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
                               page.insert_text(
                                (LEFT_MARGIN+ orig_x, line_y),
                                text,
                                fontsize=size,
                                fontname=fontname,
                                color=regex._to_rgb_tuple(color), # _to_rgb_tuple shifted to class FundRegex()
                            )

                            except Exception:
                                page.insert_text(
                                    (LEFT_MARGIN+ orig_x, line_y),
                                    text,
                                    fontsize=size,
                                    fontname=DEFAULT_FONT_NAME,
                                    color=regex._to_rgb_tuple(color), #_to_rgb_tuple shifted to class FundRegex()
                                )
                        except Exception as e:
                            print(f"Error inserting text '{text}' at {(LEFT_MARGIN + orig_x, line_y)}: {e}")

            doc.save(output_path)
    
    def _extract_data_from_pdf(self,path: str, fund:str):
        # print(f"Function Running: {inspect.currentframe().f_code.co_name}")
        final_data = {}
        with fitz.open(path) as doc:
            for page in doc:
                lines = page.get_text("text").split("\n")
                if not lines:
                    continue

                header = lines[0]
                content_lines = lines[1:]

                if header not in final_data:
                    # Use TEXT_ONLY if _get_prev_text() returns True and key exists
                    if self._get_prev_text(header) and fund in self.TEXT_ONLY and header in self.TEXT_ONLY[fund]:
                        final_data[header] = self.TEXT_ONLY[fund][header]
                    else:
                        final_data[header] = content_lines
                else:
                    final_data[header].extend(content_lines)

        return final_data

    # def get_generated_content(self, data:list, is_table=[]):
    #     print(f"Function Running: {inspect.currentframe().f_code.co_name}")
    #     extracted_text = {}
    #     output_path  = self.DRYPATH
    #     try:
    #         for content in data:
    #             pgn,fund,blocks = content['page'],content['fundname'], content['block']
              
    #             Reader._generate_pdf_from_data(blocks, output_path)
    #             extracted_text[fund] = self._extract_data_from_pdf(output_path,fund)
    #             self._update_imp_data(extracted_text[fund],fund,pgn)
    #         print("\tParsing Completed, Refining Data.....")
            
    #         try:#section for tabular data DSP, BAJAJ, HDFC
    #             is_table = self.PARAMS.get("table","")
    #             if is_table: #non-empty string true
    #                 print(f"\tTable Data Present-> running: _generate_table_data")
    #                 table_data = self._generate_table_data(self.PDF_PATH,is_table)
    #                 extracted_text = FundRegex()._map_main_and_tabular_data(extracted_text,table_data,self.FUND_NAME)
    #         except Exception as e:
    #             print(f"[Error] _generate_table_data failed: {e}")
            
    #         try: #section to duplicate mutual_funds
    #             is_duplicate_fund = self.DUPLICATE_FUNDS
    #             if is_duplicate_fund:
    #                 extracted_text = self._update_duplicate_fund_data(extracted_text)
    #             pass
    #         except Exception as e:
    #             pass
                        
    #     except Exception as e:
    #         print(f"[Error] get_generated_content failed: {e}")
    #     return extracted_text
    
    def get_generated_content(self, data: list, is_table: str = ""):
        print(f"Function Running: {inspect.currentframe().f_code.co_name}")
        extracted_text = {}
        output_path = self.DRYPATH

        try:
            for content in data:
                pgn, fund, blocks = content['page'], content['fundname'], content['block']
                Reader._generate_pdf_from_data(blocks, output_path)
                extracted_text[fund] = self._extract_data_from_pdf(output_path, fund)
                self._update_imp_data(extracted_text[fund], fund, pgn)

            print("  Parsing Completed, Refining Data.....")

            # Section for tabular data (e.g., DSP, BAJAJ, HDFC)
            table_mode = is_table or self.PARAMS.get("table", "")
            if table_mode:
                print(f">>Table Data Present -> running: _generate_table_data")
                try:
                    table_data = self._generate_table_data(self.PDF_PATH, table_mode)
                    extracted_text = FundRegex()._map_main_and_tabular_data(
                        extracted_text, table_data, self.FUND_NAME
                    )
                except Exception as e:
                    print(f"[Error] _generate_table_data failed: {e}")

            # Section to duplicate mutual funds
            if isinstance(self.DUPLICATE_FUNDS, dict) and self.DUPLICATE_FUNDS:
                print(f">>Duplicate Mutual Fund Present -> running: _update_duplicate_fund_data")
                try:
                    extracted_text = self._update_duplicate_fund_data(extracted_text)
                except Exception as e:
                    print(f"[Error] _update_duplicate_fund_data failed: {e}")

        except Exception as e:
            print(f"[Error] get_generated_content failed: {e}")

        return extracted_text

    
    #REFINE
    def __get_unique_key(self,base_key:str, data:dict):
        for suffix in ["bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel", "india", "juliett", "kilo"]:
            new_key = f"{base_key}_{suffix}"
            if new_key not in data:
                return new_key
        return "exhausted"

    def refine_extracted_data(self, extracted_text: dict):
        print(f"Function Running: {inspect.currentframe().f_code.co_name}")
        primary_refine = {}
        regex = FundRegex()
        
        header_map = {} #keep track of headers after each iteration, its imp
        for fund, item in extracted_text.items():
            content_dict = {}
            header_map[fund] = {}
            for head, content in item.items():
                if clean_head:=  regex._header_mapper(head):
                    header_map[fund][head] = clean_head
                    
                    content = self._match_with_patterns(clean_head, content,level = "primary") # applies regex to clean data
                    content = regex._transform_keys(content) #dynamic dict + other -> lowercase
                    key, value = next(iter(content.items()))
        
                    if clean_head in content_dict:
                        unique_key = self.__get_unique_key(clean_head, content_dict)
                        content_dict[unique_key] = value
                    else:
                        content_dict[clean_head] = value
                        
            primary_refine[fund] = content_dict
        # if flatten: #Flatten the dict if true
        primary_refine = {fund: regex._flatten_dict(data) for fund, data in primary_refine.items()}
        
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
    def __load_ops(self,fund:str,df:dict):
        load_data = df.get("load", {})
        if not isinstance(load_data, dict):
            print(f"Returning _load_ops: {fund} -> Type Error")
            df["load"] = {"entry_load":"","exit_load":""}
            return df
        try:
            new_load = []
            for load_key, load_value in load_data.items():
                value = load_value if isinstance(load_value, str) else " ".join(load_value)
                if re.search(r"(entry|.*entry_load)", load_key, re.IGNORECASE) and value:
                    new_load.append({"comment": value,"type": "entry_load"})
                if re.search(r"(exit|.*exit_load)", load_key, re.IGNORECASE) and value:
                    new_load.append({"comment": value,"type": "exit_load"})
        except Exception as e:
            print(f"Error in _load_ops ->Load Error: {e}")
    
        df["load"] = new_load
        return df
    
    def __metric_ops(self,fund:str,df:dict):
        try:
            new_metrics = {}
            for metric_key,metric_value in df.get("metrics",{}).items():
                new_key = FundRegex()._map_metric_keys_to_dict(metric_key) or metric_key
                # print(f"new_key {new_key}, metric_key {metric_key}")
                new_metrics[new_key] = metric_value
        except Exception as e:
            print(f"Error in _metric_ops:{fund} ->Metric Error: {e}")
        df["metrics"] = FundRegex()._populate_all_metrics_in_json(new_metrics)
        return df

    def __min_add_ops(self,fund:str,df:dict):
        try:
                new_values = {}
                for key in ["min_amt", "min_addl_amt"]:
                    if key in df:
                        new_values[key] = df[key].get("amt", "")
                        new_values[f"{key}_multiple"] = df[key].get("thraftr", "")
                df.update(new_values)
        except Exception as e:
            # logger.error(e)
            print(f"Error in {fund} ->Min/Add Error: {e}")
        return df
    
    def __map_json_ops(self,df):
        return {FundRegex()._map_json_keys_to_dict(k) or k: v for k, v in df.items()}
    
    def merge_and_select_data(self, data: dict, select = False, map_keys = False,special_handling = False):
        print(f"Function Running: {inspect.currentframe().f_code.co_name}")
        finalData = {}
        regex = FundRegex()
        for fund, content in data.items():
            temp = content
            #imp: maintain order
            temp = self._clone_fund_data(temp)
            temp = self._merge_fund_data(temp)
            temp = self._clone_fund_data(temp)
            # if select:
            temp = self._select_by_regex(temp)
            
            if map_keys:
                temp = self.__map_json_ops(temp) #map proper keys
                
            temp = self.__min_add_ops(fund,temp)
            temp = regex._populate_all_indices_in_json(temp) #populate all keys
            temp = regex._transform_keys(temp) #lowercase
            temp = self.__load_ops(fund,temp)
            temp = self.__metric_ops(fund,temp)
            
            if special_handling:
                temp = self._apply_special_handling(temp)
                
            temp = self._promote_key_from_dict(temp)
            
            #format/type convert
            temp = regex._remove_rupee_symbol(temp)
            temp = regex._convert_date_format(temp) #scheme_launch_date yyyymmdd
            temp = regex._format_fund_manager(temp) #clean fund manager
            # temp = regex._format_amt_data(temp) #min/add formatter
            temp = regex._format_metric_data(fund,temp)
            finalData[fund] = temp
  
        final_data = regex._format_to_finstinct(finalData,self.FILE_NAME) #mapper to FinStinct
        return final_data
