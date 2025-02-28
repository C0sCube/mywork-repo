import os, re, math, json,logging, subprocess
import fitz # type: ignore
from collections import defaultdict
import pdfplumber # type: ignore

from app.utils import Helper
from app.fund_regex import *
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
        
    #HIGHLIGHT            
    def check_and_highlight(self, path: str, count: int):
        
        document = fitz.open(path)
        page_count = document.page_count
        indices = Helper._get_financial_indices(self.INDICEPATH)
        fund_params = self.PARAMS['fund']
        
        #checkers
        flag_check = fund_params[0] #flags to check
        amc_regex = fund_params[1] #fund regex
        size_check = fund_params[2] #check size in range high,low
        amc_block_max = self.PARAMS['amc_check_xount'] #only first 15 blocks
             
        data = [{"title": "", "highlights": 0, "detect_idx": []} for _ in range(page_count)]

        for dpgn, page in enumerate(document):
            page_blocks = page.get_text("dict")["blocks"]
            sorted_page_texts = sorted(page_blocks, key=lambda x: (x["bbox"][1], x["bbox"][0]))

            for block_count, block in enumerate(sorted_page_texts):
                if "lines" not in block:
                    continue
                for line in block["lines"]:
                    for span in line["spans"]:
                        text, size, flag, color = (
                            span["text"].strip().lower(), span["size"], span["flags"], span["color"]
                        )
                        if flag in flag_check:
                            fund_conditions = [
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

        output_path = path.replace(".pdf", "_hltd.pdf")
        document.save(output_path)
        document.close()
        
        df = Helper._save_pdf_data(data, self.REPORTPATH, count) #imp
        return output_path, df
                            
    #EXTRACT
    def extract_clipped_data(self,input:str, pages:list, title:dict, *args:list):
        
        document = fitz.open(input)
        final_list = []
        bboxes = self.PARAMS['clip_bbox'] if not args else args[0] #bbox provided externally
    
        for pgn in pages:
            page = document[pgn]
            fundName = title[pgn]
            
            all_blocks = [] #store every data from bboxes
            
            for bbox in bboxes:
                blocks, seen_blocks = [], set()  #store unique blocks based on content and bbox
                
                page_blocks = page.get_text('dict', clip=bbox)['blocks']
                for block in page_blocks:
                    if block['type'] == 0 and 'lines' in block: #type 0 means text block
                        #hash_key
                        block_key = (tuple(block['bbox']), tuple(tuple(line['spans'][0]['text'] for line in block['lines'])))
                        if block_key not in seen_blocks:
                            seen_blocks.add(block_key)
                            blocks.append(block)

                sorted_blocks = sorted(blocks, key=lambda x: (x['bbox'][1], x['bbox'][0]))
                all_blocks.extend(sorted_blocks)

            final_list.append({
                "pgn": pgn,
                "fundname": fundName,
                "block": all_blocks
            })

        document.close()
        return final_list
    
    def extract_data_relative_line(self, input: str, pages: list, side: str, title: dict):
    
        doc = fitz.open(input)
        final_list = []
        line_x = self.PARAMS['line_x']
        
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

            if side == "both":
                left_blocks.extend(right_blocks)
            sorted_blocks = sorted(left_blocks if side != "right" else right_blocks, key=lambda x: (x["bbox"][1], x["bbox"][0]))

            final_list.append({"pgn": pgn,"fundname": fundName,"block": sorted_blocks})

        doc.close()
        return final_list

    def extract_pdf_data(self,input:str, pageSelect:list, fund_names:dict):
    
        doc = fitz.open(input)
        final_list = []
        
        for pgn in pageSelect:
            #get the page
            page, fundName = doc[pgn], fund_names[pgn]
        
            page_blocks = page.get_text('dict')['blocks'] #get all blocks
            filtered_blocks = [block for block in page_blocks if block['type'] == 0 and 'lines' in block] #type 0 are text
            sorted_blocks = sorted(filtered_blocks, key= lambda x: (x['bbox'][1], x['bbox'][0]))
            
            final_list.append({"pgn": pgn,"fundname": fundName,"block": sorted_blocks,})
        doc.close()      
        return final_list

    def extract_span_data(self, data: list,*args):  # all
        final_data = {}

        for page in data:
            seen_entries = set()
            all_blocks = [
                [round(span['size']), span['text'].strip(), span['color'], span['origin'], tuple(span['bbox']), span['font']]
                for block in page['block']
                for line in block['lines']
                for span in line.get('spans', [])
                if (entry := (round(span['size']), span['text'].strip(), span['color'], span['origin'], tuple(span['bbox']), span['font'])) not in seen_entries and not seen_entries.add(entry)
            ]

            final_data[page['fundname']] = all_blocks

        return final_data


    #CLEAN 
    def process_text_data(self,text_data: dict):
        
        stop_words = FundRegex().STOP_WORDS
        updated_text_data = {}
        
        data_cond = self.PARAMS['data']
        size_min,size_max = data_cond[0]
        color_check = data_cond[1]
        header_font = data_cond[2]
        font_check = data_cond[3]

        for fund, blocks in text_data.items():
            # Clean blocks
            cleaned_blocks = []
            for block in blocks:
                size, text, *open = block
                if text not in stop_words:
                    cleaned_blocks.append(block)

            # Process blocks (adjust size based on conditions)
            processed_blocks = []
            for block in cleaned_blocks:
                size, text, color, origin, bbox, font = block
                text = text.strip()
                
                if round(size) in range(size_min, size_max) and color in color_check and font in font_check:
                    size = header_font  # Update size
                processed_blocks.append([size, text, color, origin, bbox,font])

            # Group blocks by rounded y-coordinate
            grouped_blocks = defaultdict(list)
            for block in processed_blocks:
                y_coord = math.ceil(block[3][1])
                size = block[0]
                grouped_blocks[(y_coord, size)].append(block)

            # Combine blocks with the same y-coordinate
            combined_blocks = []
            for key, group in grouped_blocks.items():
                if key[1] == header_font:
                    combined_text = " ".join(item[1] for item in group).strip()
                    if combined_text:  # Ignore whitespace-only text
                        size, color, origin, bbox,font = group[0][0], group[0][2], group[0][3], group[0][4], group[0][5]
                        combined_blocks.append([size, combined_text, color, origin, bbox,font])
                else:
                    for item in group:
                        combined_blocks.append(item)

            updated_text_data[fund] = combined_blocks

        return updated_text_data

    def create_nested_dict(self,cleaned_data:dict,*args):
            final_text_data = dict()
            final_matrix = dict()

            header_size, content_size = self.PARAMS['content_size']
            for fund, data in cleaned_data.items(): #ech fund
                nested_dict = {}
                current_header = "before"
                
                if current_header not in nested_dict:
                    nested_dict[current_header] = []
                    
                for item in data:
                    size = item[0]
                    text = item[1].strip()
                    if size == header_size:
                        current_header = "_".join([i for i in text.split(" ") if i != '']).lower()
                        nested_dict[current_header] = []
                    elif size<= content_size and current_header:
                        nested_dict[current_header].append(item)
                
                #remove if before is empty       
                if nested_dict['before'] == []:
                    del nested_dict['before']    
                final_text_data[fund] = nested_dict        
            
            return final_text_data, final_matrix

    def get_data_via_line(self,path:str,pages:list, side:str, title:dict):
        
        data = self.extract_data_relative_line(path,pages,side,title)
        data = self.extract_span_data(data,[])
        clean_data = self.process_text_data(data)
        nested, matrix = self.create_nested_dict(clean_data)
        return nested
    
    def get_data_via_clip(self,path:str,pages:list, title:dict, *args): #args bcz pass clip boox externally
        
        data = self.extract_clipped_data(path,pages,title, *args)
        data = self.extract_span_data(data,[])
        clean_data = self.process_text_data(data)
        nested, matrix = self.create_nested_dict(clean_data)
        return nested
    
    #PROCESS
    @staticmethod
    def __generate_pdf_from_data(data: dict, output_path: str) -> None:
        pdf_doc = fitz.open()
        TITLE_FONT_SIZE = 24
        TITLE_POSITION = 72
        TITLE_COLOR = (0, 0, 1)

        for header, items in data.items():
            page = pdf_doc.new_page()
            text_position = TITLE_POSITION

            try:
                page.insert_text(
                    (72, text_position), #initalizor
                    header,
                    fontsize=TITLE_FONT_SIZE,
                    fontname="helv",
                    color= TITLE_COLOR,
                )        
            except Exception as e:
                pass
                
            for item in items:
                size,text,color,origin,bbox,font = item
    
                #Errror in fitz font 
                try:
                    page.insert_text(
                        (origin[0], origin[1]),
                        text,
                        fontsize=size,
                        fontname="helv",
                        color=tuple(int(color & 0xFFFFFF) for _ in range(3)))#unsigned int value so (0,0,0)
                    
                except Exception as e:
                    page.insert_text(
                        (origin[0], origin[1]),
                        text,
                        fontsize=size,
                        fontname="helv",
                        color=(1, 0, 0),
                    )


        pdf_doc.save(output_path)
        pdf_doc.close()

    @staticmethod
    def __extract_data_from_pdf(path: str):

        with pdfplumber.open(path) as pdf:
            final_data = {}

            for page in pdf.pages:
                content = page.extract_text().encode("ascii", "ignore").decode().split('\n')
                key,val = content[0], content[1:]
                final_data[key] = val #First text will he Header rest values

        return final_data

    def get_generated_content(self, data:dict):
        extracted_text,unextracted_text  = {}, {}
        output_path  = self.DRYPATH
        for fund, items in data.items():
           try:
                Reader.__generate_pdf_from_data(items, output_path)
                print(f'\n---<<{fund}>>---at: {output_path}')
                extracted_text[fund] = Reader.__extract_data_from_pdf(output_path)
                
           except Exception as e:
               print(f"\nError while processing '{fund}': {e}")
               continue      
        return extracted_text
    
    #REFINE
    def refine_extracted_data(self, extracted_text: dict,flatten = False):
        final_text = {}
        regex = FundRegex() 
        for fund, items in extracted_text.items():
            content_dict = {}
            for head, content in items.items():
                clean_head = regex.header_mapper(head) #normalizes headers
                if clean_head: 
                    content = self._match_regex_to_content(clean_head, content) # applies regex to clean data
                    content = regex.transform_keys(content) #lowercase all keys
                    content_dict.update(content)
                    # scheme fund name
                    content_dict["main_scheme_name"] = fund #hardcoded as common for all
            final_text[fund] = content_dict
        
        if flatten: #Flatten the dict if true
            final_text = {fund: regex.flatten_dict(data) for fund, data in final_text.items()}
            
        return final_text
    
    def refine_secondary_data(self, extracted_text: dict):
        final_text = {}
        regex = FundRegex() 
        for fund, items in extracted_text.items():
            content_dict = {}
            for head, content in items.items():
                # clean_head = regex.header_mapper(head) #normalizes headers
                # if clean_head: 
                content = self._secondary_match_regex_to_content(head, content) # applies regex to clean data
                # content = regex.transform_keys(content) #lowercase all keys
                content_dict.update(content)
            final_text[fund] = content_dict
        
        # if flatten: #Flatten the dict if true
        #     final_text = {fund: regex.flatten_dict(data) for fund, data in final_text.items()}
            
        return final_text

    #SELECT

