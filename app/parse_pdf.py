import os, re, math, json,logging, subprocess
import fitz # type: ignore
from collections import defaultdict
import pdfplumber # type: ignore

from app.utils import Helper
from app.parse_regex import *
from logging_config import *

class Reader:
    def __init__(self, config_path: str,params:dict):
        
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file not found: {config_path}")
        with open(config_path,'r') as file:
            paths_data = json.load(file)
            
        self.PARAMS = params
                
        dirs = paths_data.get("dirs", {})
        paths = paths_data.get("paths", {})

        self.BASEPATH = dirs.get("base_path", "")
        self.DRYPATH = os.path.join(self.BASEPATH, paths.get("dry", ""))
        self.INDICEPATH = os.path.join(self.BASEPATH, paths.get("fin", ""))
        self.REPORTPATH = os.path.join(self.BASEPATH, paths.get("rep", ""))
        self.JSONPATH = os.path.join(self.BASEPATH, paths.get("json", ""))
        self.CSVPATH = os.path.join(self.BASEPATH, paths.get("csv", ""))
        
        #other instance initialize
        self.TEXT_ONLY = {}
        
    #HIGHLIGHT            
    def check_and_highlight(self, path: str, count: int):
        output_path = path.replace(".pdf", "_hltd.pdf")
        
        with fitz.open(path) as doc:
            page_count = doc.page_count
            indices = Helper._get_financial_indices(self.INDICEPATH)
    
            #checkers
            fund_cond = self.PARAMS['fund']
            flag_check = fund_cond['flag']
            amc_regex = fund_cond['regex']
            size_check = fund_cond['size']
            amc_block_max = fund_cond['countmax_header_check'] #First 15 blocks
                
            data = [{"title": "", "highlights": 0, "detect_idx": []} for _ in range(page_count)]

            for dpgn, page in enumerate(doc):
                page_blocks = page.get_text("dict")["blocks"]
                sorted_blocks = sorted(page_blocks, key=lambda x: (x["bbox"][1], x["bbox"][0]))

                for block_count, block in enumerate(sorted_blocks):
                    if "lines" not in block:
                        continue
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text, size, flag, color = (span["text"].strip().lower(), span["size"], span["flags"], span["color"])
                            
                            fund_conditions = [
                                flag in flag_check,
                                block_count < amc_block_max,
                                re.match(amc_regex, text, re.IGNORECASE),
                                round(size) in range( size_check[0],  size_check[1])
                            ]
                            if all(fund_conditions):
                                data[dpgn]["title"] = text
                                page.add_rect_annot(fitz.Rect(span["bbox"]))
                                print(text)
                            
                            for indice in indices:
                                pattern = rf"\b{re.escape(indice)}\b"
                                if re.search(pattern, text):
                                    if indice not in data[dpgn]['detect_idx']:
                                        data[dpgn]['detect_idx'].append(indice)
                                        data[dpgn]['highlights'] += 1
                                    page.add_highlight_annot(fitz.Rect(span["bbox"]))
                                    break

            doc.save(output_path)
        df = Helper._save_pdf_data(data, self.REPORTPATH, count) #imp
        return output_path, df
    
    #EXTRACT
    
    def _create_data_entry(self,*args)->dict:
        return {"page":args[0],"fundname":args[1],"block":args[2]}
                   
    def extract_clipped_data(self, input: str, pages: list, title: dict, *args)->list:
        
        with fitz.open(input) as doc:
            finalData = []
            fund_seen = {}

            bboxes = self.PARAMS['clip_bbox'] if not args else args[0]

            for pgn in pages:
                fundName = title.get(pgn, "").strip()
                if not fundName:
                    continue

                page = doc[pgn]
                all_blocks = []
                for bbox in bboxes:
                    blocks, seen_blocks = [], set()
                    page_blocks = page.get_text('dict', clip=bbox)['blocks']

                    for block in page_blocks:
                        if block['type'] == 0 and 'lines' in block:
                            block_key = (tuple(block['bbox']), tuple(tuple(line['spans'][0]['text'] for line in block['lines'])))
                            if block_key not in seen_blocks:
                                seen_blocks.add(block_key)
                                blocks.append(block)
                    sorted_blocks = sorted(blocks, key=lambda x: (x['bbox'][1], x['bbox'][0]))
                    
                    #add dummy data
                    fontz = self.PARAMS['data']['font'][0]
                    colorz = self.PARAMS['data']['color'][0]
                    sorted_blocks.append(FundRegex()._dummy_block(fontz,colorz))
                    all_blocks.extend(sorted_blocks)
                    
                if fundName in fund_seen:
                    fund_seen[fundName]["block"].extend(all_blocks)
                    fund_seen[fundName]["page"].append(pgn)
                else:
                    new_entry = {"page": [pgn], "fundname": fundName, "block": all_blocks}
                    finalData.append(new_entry)
                    fund_seen[fundName] = new_entry  # Store reference to modify later

        return finalData

    def extract_data_relative_line(self, input: str, pages: list, title: dict)->list:
    
        with fitz.open(input) as doc:
            finalData = []
            fund_seen = {}
            line_x = self.PARAMS['line_x']
            side = self.PARAMS['line_side']
            
            for pgn in pages:
                page, fundName = doc[pgn],title[pgn]
                
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
                left_blocks.append(FundRegex()._dummy_block(fontz,colorz))
                right_blocks.append(FundRegex()._dummy_block(fontz,colorz))
                
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

    def extract_pdf_data(self,input:str, pages:list, titles:dict)->list:
        with fitz.open(input) as doc:
            finalData = []
            for pgn in pages:
                page = doc[pgn]
                fundName = titles[pgn]
            
                blocks = page.get_text('dict')['blocks']
                filtered_blocks = [block for block in blocks if block['type'] == 0 and 'lines' in block] #type 0 are text
                sorted_blocks = sorted(filtered_blocks, key= lambda x: (x['bbox'][1], x['bbox'][0]))
                finalData.append(self._create_data_entry(pgn,fundName,sorted_blocks))
                
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
    def process_text_data(self, data: list)->list:
        
        stop_words,finalData = FundRegex().STOP_WORDS,[]
        #checkers
        data_cond = self.PARAMS['data']
        size_checker = data_cond['size']
        font_checker = data_cond['font']
        color_checker = data_cond['color']
        font_change = data_cond['update_size']
        
        amc_stop_words = self.PARAMS['stop_words']
        
        combined_stop_words = set(stop_words) | set(amc_stop_words)
        
        for content in data:
            pgn,fundName,blocks = content['page'],content['fundname'],content['block']
    
            cleaned_blocks = [] # Clean blocks
            for block in blocks:
                size, text, *_ = block
                if text.lower() not in combined_stop_words:
                    cleaned_blocks.append(block)

            processed_blocks = [] # Process blocks (adjust size based on conditions)
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
                        curr_head = "_".join([i for i in text.strip().split(" ") if i != '']).lower()
                        nested_dict[curr_head] = []
                    elif size<= content_size and curr_head:
                        nested_dict[curr_head].append(block)
                     
                if nested_dict['before'] == []:
                    del nested_dict['before']    
                
                finalData.append(self._create_data_entry(pgn,fundName,nested_dict))
    
            return finalData

    def get_data_via_line(self,path:str,pages:list, side:str, title:dict):
        
        data = self.extract_data_relative_line(path,pages,side,title)
        data = self.extract_span_data(data,[])
        clean_data = self.process_text_data(data)
        nested = self.create_nested_dict(clean_data)
        return nested
    
    def get_data_via_clip(self,path:str,pages:list, title:dict, *args): #args bcz pass clip boox externally
        
        data = self.extract_clipped_data(path,pages,title, *args)
        data = self.extract_span_data(data,[])
        clean_data = self.process_text_data(data)
        nested = self.create_nested_dict(clean_data)
        return nested
    
    
    def get_data(self, path: str, pages: list, title: dict):
        
        method = self.PARAMS['method'] #clip/line/both
        extracted_data = []
        
        if method in ["line", "both"]:
            data = self.extract_data_relative_line(path, pages, title)
            extracted_data.extend(self.extract_span_data(data, []))
        
        if method in ["clip", "both"]:
            data = self.extract_clipped_data(path, pages, title)
            extracted_data.extend(self.extract_span_data(data, []))
        
        clean_data = self.process_text_data(extracted_data) #process & clean
        nested_data = self.create_nested_dict(clean_data)
        
        for page in nested_data:
            page_text = {}
            page_blocks,fundname = page['block'],page['fundname']
            for key, content in page_blocks.items():
                page_text[key] = [txt[1] for txt in content]
            self.TEXT_ONLY[fundname] = page_text
        return nested_data
    
    #PROCESS
    @staticmethod
    # def _generate_pdf_from_data(data: dict, output_path: str) -> None:
    #     with fitz.open() as doc:
    #         TITLE_FONT_SIZE = 24
    #         TITLE_POSITION = 72
    #         TITLE_COLOR = (0, 0, 1)
    #         FONT_NAME = "helv"
            
    #         font = fitz.Font(FONT_NAME)  # Create a font object for measuring text

    #         for header, content in data.items():
    #             page = doc.new_page()
    #             text_position = TITLE_POSITION

    #             try:
    #                 page.insert_text(
    #                     (72, text_position),
    #                     header,
    #                     fontsize=TITLE_FONT_SIZE,
    #                     fontname=FONT_NAME,
    #                     color=TITLE_COLOR,
    #                 )
    #                 text_position += TITLE_FONT_SIZE * 2
    #             except Exception:
    #                 pass

    #             # Group content by approximate Y-position
    #             line_dict = defaultdict(list)
    #             for block in content:
    #                 size, text, color, origin, bbox, fontname = block
    #                 y_rounded = round(origin[1] / 2) * 2  # Normalize Y to prevent slight shifts
    #                 line_dict[y_rounded].append((origin[0], text, size, color, fontname))

    #             # Process lines
    #             for y_pos in sorted(line_dict.keys()):
    #                 line_dict[y_pos].sort()  # Sort text by X-position
                    
    #                 line_text = ""
    #                 prev_x = None

    #                 for x, text, size, color, fontname in line_dict[y_pos]:
    #                     if prev_x is not None:
    #                         text_width = font.text_length(text, fontsize=size)  # Correct way to get text width
    #                         if x - prev_x > text_width * 0.5:
    #                             line_text += " "
                        
    #                     line_text += text
    #                     prev_x = x + font.text_length(text, fontsize=size)

    #                 try:
    #                     page.insert_text(
    #                         (72, y_pos),
    #                         line_text,
    #                         fontsize=size,
    #                         fontname=FONT_NAME,
    #                         color=(color & 0xFFFFFF, color & 0xFFFFFF, color & 0xFFFFFF),
    #                     )
    #                 except Exception:
    #                     page.insert_text(
    #                         (72, y_pos),
    #                         line_text,
    #                         fontsize=size,
    #                         fontname=FONT_NAME,
    #                         color=(1, 0, 0),
    #                     )

    #         doc.save(output_path)
    def _to_rgb_tuple(color_int):
        c = color_int & 0xFFFFFF
        r = (c >> 16) & 0xFF
        g = (c >> 8) & 0xFF
        b = c & 0xFF
        return (r/255.0, g/255.0, b/255.0)
    
    def _generate_pdf_from_data(self,data: dict, output_path: str) -> None:
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
                                color=Reader._to_rgb_tuple(color),
                            )

                            except Exception:
                                page.insert_text(
                                    (LEFT_MARGIN+ orig_x, line_y),
                                    text,
                                    fontsize=size,
                                    fontname=DEFAULT_FONT_NAME,
                                    color=Reader._to_rgb_tuple(color),
                                )
                        except Exception as e:
                            print(f"Error inserting text '{text}' at {(LEFT_MARGIN + orig_x, line_y)}: {e}")

            doc.save(output_path)
   
 
    def _extract_data_from_pdf(self,path: str,fund:str):
        with pdfplumber.open(path) as pdf:
            final_data = {}

            for page in pdf.pages:
                content = page.extract_text().encode("ascii", "ignore").decode().split('\n')
                key,val = content[0], content[1:] #str, list
                if self._get_prev_text(key):
                    val = self.TEXT_ONLY[fund][key]
                final_data[key] = val #First text will he Header rest values

        return final_data

    def get_generated_content(self, data:list):
        extracted_text= {}
        output_path  = self.DRYPATH
        for content in data:
            pgn,fund,blocks = content['page'],content['fundname'], content['block']
        
            self._generate_pdf_from_data(blocks, output_path)
            print(f'\n---<<{fund}>>---at: {output_path}')
            extracted_text[fund] = self._extract_data_from_pdf(output_path, fund)
            self._update_imp_data(extracted_text[fund],fund,pgn)
        return extracted_text
    
    #REFINE
    
    def _get_unique_key(self,base_key:str, data:dict):
        phonetic_codes = ["bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel", "india", "juliett", "kilo"]

        for suffix in phonetic_codes:
            new_key = f"{base_key}_{suffix}"
            if new_key not in data:
                return new_key
        return "exhaust"
    
    def refine_extracted_data(self, extracted_text: dict,flatten = False):
        primary_refine = {}
        regex = FundRegex() 
        for fund, item in extracted_text.items():
            content_dict = {}
            for head, content in item.items():
                if clean_head:=  regex.header_mapper(head):
                    content = self._match_regex_to_content(clean_head, content) # applies regex to clean data
                    content = regex.transform_keys(content) #lowercase
                    key, value = next(iter(content.items()))  # Extract key-value once

                    if clean_head in content_dict:
                        unique_key = self._get_unique_key(clean_head, content_dict)
                        content_dict[unique_key] = value
                    else:
                        content_dict[clean_head] = value
                        
            primary_refine[fund] = content_dict
        if flatten: #Flatten the dict if true
            primary_refine = {fund: regex.flatten_dict(data) for fund, data in primary_refine.items()}
        
        secondary_refine = {}
        for fund, item in primary_refine.items():
            content_dict = {}
            for head, content in item.items():
                content = self._secondary_match_regex_to_content(head, content)
                content_dict.update(content)

            secondary_refine[fund] = content_dict
            
        tertiary_refine = {}
        for fund, item in secondary_refine.items():
            content_dict = {}
            for head, content in item.items():
                content = self._tertiary_match_regex_to_content(head, content)
                content_dict.update(content)

            tertiary_refine[fund] = content_dict
        return tertiary_refine
    
    #SELECT/MERGE
    def merge_and_select_data(self, data: dict, select = False, map = False,special = False):
        finalData = {}
        regex = FundRegex()
        for fund, content in data.items():
            temp = content
            temp = self._merge_fund_data(temp)
            
            temp = self._clone_fund_data(temp)
            
            if select:
                temp = self._select_by_regex(temp)
            
            if map:
                mappend_data = {}
                for key, value in temp.items():
                    new_key = regex._map_json_keys_to_dict(key) or key
                    mappend_data[new_key] = value
                temp = mappend_data
            
            #flatten min/add data
            new_values = {}
            for key in ["min_amt", "min_addl_amt"]:
                if key in temp:
                    new_values[key] = temp[key].get("amt", "")
                    new_values[f"{key}_multiple"] = temp[key].get("thraftr", "")
            temp.update(new_values)
            
            #populate and lowercase
            temp = regex._populate_all_indices_in_json(temp)
            temp = regex.transform_keys(temp) #lowercase
            
            #regex load data
            new_load = {"entry_load": None,"exit_load": None}
            # print(temp.get("load",{}))

            for load_key, load_value in temp.get("load", {}).items():
                if re.search(r"(entry|.*entry_load)", load_key, re.IGNORECASE):
                    new_load["entry_load"] = load_value
                elif re.search(r"(exit|.*exit_load)", load_key, re.IGNORECASE):
                    new_load["exit_load"] = load_value
                else:
                    new_load[load_key] = load_value

            temp["load"] = new_load

                
            #metrics convert
            new_metrics = {}
            for metric_key,metric_value in temp['metrics'].items():
                new_key = regex._map_metric_keys_to_dict(metric_key) or metric_key
                new_metrics[new_key] = metric_value
            #populate metrics
            temp["metrics"] = regex._populate_all_metrics_in_json(new_metrics)
            
            if special:
                for head, content in temp.items():
                    updated_content = self._special_match_regex_to_content(head, content)
                    if updated_content:
                        temp.update(updated_content)

            finalData[fund] = dict(sorted(temp.items()))
            

        return finalData