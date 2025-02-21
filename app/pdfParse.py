import os, re, math, json
import fitz
from collections import defaultdict
import pdfplumber
import pandas as pd
import numpy as np
import subprocess

from app.fundRegex import *
class Reader:
    
    BASEPATH  = ''
    DRYPATH = ''
    INDICEPATH  = ''
    REPORTPATH = ''
    JSONPATH  = ''
    PARAMS = {}
    
    def __init__(self, config_path: str,params:dict):
        
        self.PARAMS = params
        
        try:
            if not os.path.exists(config_path):
                raise FileNotFoundError(f"Config file not found: {config_path}")
            
            with open(config_path,'r') as file:
                paths_data = json.load(file)
                
        except Exception as e:
            print(f'Error: {e}')

        dirs = paths_data.get("dirs", {})
        paths = paths_data.get("paths", {})

        self.BASEPATH = dirs.get("base_path", "")
        self.DRYPATH = os.path.join(self.BASEPATH, paths.get("dry", ""))
        self.INDICEPATH = os.path.join(self.BASEPATH, paths.get("fin", ""))
        self.REPORTPATH = os.path.join(self.BASEPATH, paths.get("rep", ""))
        self.JSONPATH = os.path.join(self.BASEPATH, paths.get("json", ""))
        
    
    def get_file_path(self, path: str):
        return self.BASEPATH + path
    
    
    #HIGHLIGHT
    @staticmethod
    def __get_financial_indices(path:str):
        
        df = pd.read_excel(path)
        financial_indexes = df['indexes'].tolist()
        return set(financial_indexes)

    @staticmethod
    def __save_pdf_data(df,path:str, threshold: int):
        excel_path = path
        
    
        df_expanded = df["detect_idx"].apply(pd.Series)
        df_expanded.columns = [f"idx_{i+1}" for i in range(df_expanded.shape[1])]
        df_final = pd.concat([df.drop(columns=["detect_idx"]), df_expanded], axis=1)
        df_final.to_excel(excel_path, engine="openpyxl", index=True)

        # Filter pages based on the threshold
        pages = df.loc[ (df["highlights"] >= threshold) & (df["title"].str.contains(r"\w+", na=False, regex=True))].index.to_list()
               
        print(f"\nDoc Saved At: {excel_path}")
        print(f"\nPages to Extract: {pages}")

        # Open the file on the screen
        # subprocess.Popen([excel_path], shell=True)
                
    def check_and_highlight(self, path: str, count: int):
        
        try:
            document = fitz.open(path)
            page_count = document.page_count
            indices = Reader.__get_financial_indices(self.INDICEPATH)
            fund_data = self.PARAMS['fund']
            
        except Exception as e:
            # logging.error(e)
            return
            
        

        # Initialize datasets
        df = pd.DataFrame({
            "title": np.full(page_count,"", dtype = object),
            "highlights": np.zeros(page_count, dtype = int),
            "detect_idx": [[] for _ in range(page_count)]
        })
        

        for dpgn, page in enumerate(document):
            
            pageBlocks = page.get_text("dict")['blocks']
            sortedPageTexts = sorted(pageBlocks, key=lambda x: (x["bbox"][1], x["bbox"][0]))

            for block_count, block in enumerate(sortedPageTexts):
                if "lines" not in block:
                    continue

                for line in block["lines"]:
                    for span in line["spans"]:
                        text, size, flag, color = (span["text"].strip().lower(),span["size"],span["flags"],span["color"],)

                        if flag in fund_data[0]:
                            fund_conditions = [
                                block_count in range(0, 15),  # Check first 15 blocks only
                                re.match(fund_data[1], text, re.IGNORECASE),
                                round(size) in range(fund_data[2][0], fund_data[2][1]),
                                # color in fund_data[3]
                            ]

                            # Check if the page contains fund data   
                            if all(fund_conditions):
                                df.loc[dpgn,"title"] = text
                                print(text)
                                # Highlight
                                page.add_rect_annot(fitz.Rect(span["bbox"]))

                            # Check if indices exist in the page and count
                            for indice in indices:
                                pattern = rf"\b{re.escape(indice)}\b"
                                if match:= re.search(pattern, text):
                                    df.loc[dpgn, 'highlights'] += 1
                                    df.loc[dpgn, 'detect_idx'].append(match.group())
                                    # Highlight
                                    rect = fitz.Rect(span["bbox"])
                                    page.add_highlight_annot(rect)
                                    break  # One highlight per span

        if any(df['highlights']):
            output_path = path.replace(".pdf", "_hltd.pdf")
            document.save(output_path)
            # subprocess.Popen([output_path], shell=True)

        document.close()
        # Save PDF data
        Reader.__save_pdf_data(df, self.REPORTPATH, count)
        return output_path, df
                            
    #EXTRACT
    def __extract_clipped_data(self,input:str, pages:list, title:dict, *args:list):
        
        try:
            document = fitz.open(input)
            final_list = []
            bboxes = self.PARAMS['clip_bbox'] if not args else args[0] #bbox provided externally
            fund_names = title
            
        except Exception as e:
            # logging.error(e)
            return

        for pgn in pages:
            page = document[pgn]
            fundName = fund_names[pgn]

            blocks = []
            seen_blocks = set()  # To store unique blocks based on content and bbox

            for bbox in bboxes:
                page_blocks = page.get_text('dict', clip=bbox)['blocks']
                for block in page_blocks:
                    if block['type'] == 0 and 'lines' in block:
                        #hash_key
                        block_key = (tuple(block['bbox']), tuple(tuple(line['spans'][0]['text'] for line in block['lines'])))
                        if block_key not in seen_blocks:
                            seen_blocks.add(block_key)
                            blocks.append(block)

            sorted_blocks = sorted(blocks, key=lambda x: (x['bbox'][1], x['bbox'][0]))

            final_list.append({
                "pgn": pgn,
                "fundname": fundName,
                "block": sorted_blocks
            })

        document.close()
        return final_list
    
    def __extract_data_relative_line(self,path: str,pageSelect:list, side: str, titles:dict):
        
        try:
            doc = fitz.open(path)
            final_list = []
            line_x = self.PARAMS['line_x']
            fund_names = titles
            
        except Exception as e:
            # logging.error(e)
            return
        
        for pgn in pageSelect:
            page = doc[pgn]
            fundname = fund_names[pgn]

            blocks = page.get_text("dict")["blocks"]
            filtered_blocks = [block for block in blocks if block['type']==0 and 'lines' in block]
            extracted_blocks = []

            # Keep track of blocks
            added_blocks = set()

            for block in filtered_blocks:
                block_id = id(block)  # Unique identifier

                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        origin = span["origin"]
                        x0, _ = origin

                        #left or right
                        if side == "left" and x0 < line_x and block_id not in added_blocks:
                            extracted_blocks.append(block)
                            added_blocks.add(block_id)  #added
                        elif side == "right" and x0 > line_x and block_id not in added_blocks:
                            extracted_blocks.append(block)
                            added_blocks.add(block_id)  #

            # Sort extracted blocks
            sorted_blocks = sorted(extracted_blocks, key=lambda x: (x["bbox"][1], x["bbox"][0]))

            final_list.append({
                "pgn": pgn,
                "fundname": fundname,
                "block": sorted_blocks
            })

        doc.close()

        return final_list

    def __extract_pdf_data(self,input:str, pageSelect:list, fund_names:dict):
    
        document = fitz.open(input)
        finalData = []
        
        for pgn in pageSelect:
            #get the page
            page = document[pgn]
            fundName = fund_names[pgn]
        
            blocks = page.get_text('dict')['blocks'] #get all blocks
            filtered_blocks = [block for block in blocks if block['type'] == 0 and 'lines' in block] #type 0 are text
            sorted_blocks = sorted(filtered_blocks, key= lambda x: (x['bbox'][1], x['bbox'][0]))
            
            finalData.append({
                "page": pgn,
                "fundname": fundName,
                "block": sorted_blocks,
            })
                
        return finalData

    def __extract_span_data(self, data: list,*args):  # all
        final_data = {}

        for page in data:
            seen_entries = set()
            pgn_content = [
                [round(span['size']), span['text'].strip(), span['color'], span['origin'], tuple(span['bbox']), span['font']]
                for block in page['block']
                for line in block['lines']
                for span in line.get('spans', [])
                if (entry := (round(span['size']), span['text'].strip(), span['color'], span['origin'], tuple(span['bbox']), span['font'])) not in seen_entries and not seen_entries.add(entry)
            ]

            final_data[page['fundname']] = pgn_content

        return final_data

    #CLEAN 
    def __process_text_data(self,text_data: dict):
        
        stop_words = FundRegex().STOP_WORDS
        updated_text_data = {}
        data_conditions = self.PARAMS['data']

        for fund, data in text_data.items():
            blocks = data

            # Clean blocks
            cleaned_blocks = []
            for block in blocks:
                size, text, color, origin, bbox,font = block
                if text not in stop_words:
                    cleaned_blocks.append(block)

            # Process blocks (adjust size based on conditions)
            processed_blocks = []
            for block in cleaned_blocks:
                size, text, color, origin, bbox, font = block
                text = text.strip()
                
                if round(size) in range(data_conditions[0][0], data_conditions[0][1]) and color in data_conditions[1] and font in data_conditions[3]:
                    size = data_conditions[2]  # Update size
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
                if key[1] == data_conditions[2]:
                    combined_text = " ".join(item[1] for item in group).strip()
                    if combined_text:  # Ignore whitespace-only text
                        size, color, origin, bbox,font = group[0][0], group[0][2], group[0][3], group[0][4], group[0][5]
                        combined_blocks.append([size, combined_text, color, origin, bbox,font])
                else:
                    for item in group:
                        combined_blocks.append(item)

            updated_text_data[fund] = combined_blocks

        return updated_text_data

    def __create_nested_dict(self,cleaned_data:dict,*args):
            final_text_data = dict()
            final_matrix = dict()

            header_size, content_size = self.PARAMS['content_size']
            for fund, items in cleaned_data.items(): #ech fund
                
                # #step 1 extract size, coord
                # coordinates = list()
                # sizes = set()
                
                # for item in items: #size,text,color,origin
                #     origin = tuple(item[3])
                #     coordinates.append(origin)
                #     sizes.add(item[0])
                
                # coordinates = sorted(set(coordinates), key=lambda c: (c[1], c[0]))  # Sort by y, then x
                # sizes = sorted(sizes, reverse=True)  
                
                # #step 2 create matrix
                # coord_to_index = {coord: idx for idx, coord in enumerate(coordinates)}  # (x,y) at pos 0 etc. ROWS
                # size_to_index = {font: idx for idx, font in enumerate(sizes)}  # COLUMNS
                # matrix = np.zeros((len(coordinates), len(sizes)), dtype=object)
                
                
                #step 3
                nested_dict = {}
                current_header = "before"
                
                if current_header not in nested_dict:
                    nested_dict[current_header] = []
                    
                for item in items:
                    origin = tuple(item[3])
                    size = item[0]
                    text = item[1].strip()
                    
                    #populate the matrix
                    # if origin in coord_to_index and size in size_to_index:
                    #     row = coord_to_index[origin]
                    #     col = size_to_index[size]
                        
                    #     if matrix[row,col] == 0:
                    #         matrix[row,col] ==r"nil"
                    #     matrix[row,col] == text
                    
                    #build nested dict
                    if size == header_size:
                        current_header = "_".join([i for i in text.split(" ") if i != '']).lower()
                        nested_dict[current_header] = []
                    elif size<= content_size and current_header:
                        nested_dict[current_header].append(item)
                
                #remove if before is empty       
                if nested_dict['before'] == []:
                    del nested_dict['before']    
                final_text_data[fund] = nested_dict        
                # matrix_df = pd.DataFrame(matrix, index=coordinates, columns=sizes)
                # final_matrix[fund] = matrix_df
            
            return final_text_data, final_matrix

    def get_data_via_line(self,path:str,pages:list, side:str, title:dict):
        
        data = self.__extract_data_relative_line(path,pages,side,title)
        data = self.__extract_span_data(data,[])
        clean_data = self.__process_text_data(data)
        nested, matrix = self.__create_nested_dict(clean_data)
        return nested
    
    def get_data_via_clip(self,path:str,pages:list, title:dict, *args):
        
        data = self.__extract_clipped_data(path,pages,title, *args)
        data = self.__extract_span_data(data,[])
        clean_data = self.__process_text_data(data)
        nested, matrix = self.__create_nested_dict(clean_data)
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
               logging.error(e)
               continue      
        return extracted_text
    
    #REFINE
    def refine_extracted_data(self, extracted_text: dict):
        final_text = {}
        regex = FundRegex() 
        for fund, items in extracted_text.items():
            content_dict = {}
            for head, content in items.items():
                clean_head = regex.header_mapper(head) #normalizes headers
                if clean_head: 
                    content = self.match_regex_to_content(clean_head, content) # applies regex to clean data
                    content = regex.transform_keys(content) #lowercase all keys
                    content_dict.update(content)
            final_text[fund] = content_dict
            
        return final_text



