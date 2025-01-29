import os, re, math, pprint
import fitz
from collections import defaultdict
import pdfplumber
import pandas as pd
import subprocess


class Reader:
    
    BASEPATH  = ''
    DRYPATH = ''
    INDICEPATH  = ''
    REPORTPATH = ''
    
    def __init__(self, path: str, dry:str, fin:str, rep:str):
        self.BASEPATH = path
        self.DRYPATH = self.BASEPATH + dry
        self.INDICEPATH = self.BASEPATH + fin
        self.REPORTPATH = self.BASEPATH + rep
    
    def get_file_path(self, path: str):
        return self.BASEPATH + path
    
    
    #HIGHLIGHT
    @staticmethod
    def get_financial_indices(path:str):
        
        if not os.path.exists(path):
            print('File does not exists')
            return
        
        df = pd.read_excel(path)
        financial_indexes = df['indexes'].tolist()
        return set(financial_indexes)
    
    def check_and_highlight(self, path: str, fund_data: list, count: int):
        document = fitz.open(path)
        document_page_count = document.page_count

        indices = Reader.get_financial_indices(self.INDICEPATH)

        # Initialize datasets
        pages = [i for i in range(document_page_count)]
        important_pages = dict.fromkeys(pages, 0)
        fund_titles = dict.fromkeys(pages, "")
        detected_indices = dict.fromkeys(pages,set())

        for dpgn, page in enumerate(document):
            pageBlocks = page.get_text("dict")
            pageTexts = pageBlocks["blocks"]

            sortedPageTexts = sorted(pageTexts, key=lambda x: (x["bbox"][1], x["bbox"][0]))

            for block_count, block in enumerate(sortedPageTexts):
                if "lines" not in block:
                    continue

                for line in block["lines"]:
                    for span in line["spans"]:
                        text, size, flag, color = (
                            span["text"].strip().lower(),
                            span["size"],
                            span["flags"],
                            span["color"],
                        )

                        # Check if the page contains fund data
                        if flag in fund_data[0]:
                            fund_conditions = [
                                block_count in range(0, 15),  # Check first 15 blocks only
                                re.match(fund_data[1], text, re.IGNORECASE),
                                round(size) in range(fund_data[2][0], fund_data[2][1]),
                                # color in fund_data[3]
                            ]

                            if all(fund_conditions):
                                fund_titles[dpgn] = text
                                print(text)
                                # Highlight
                                page.add_rect_annot(fitz.Rect(span["bbox"]))

                        # Check if indices exist in the page and count
                        for indice in indices:
                            pattern = rf"\b{re.escape(indice)}\b"
                            if match:= re.search(pattern, text):
                                important_pages[dpgn] += 1
                                detected_indices[dpgn].add(match.group())
                                # Highlight
                                rect = fitz.Rect(span["bbox"])
                                page.add_highlight_annot(rect)
                                break  # One highlight per span

        output_path = None
        if any(important_pages.values()):
            output_path = path.replace(".pdf", "_highlighted.pdf")
            document.save(output_path)
        document.close()

        # Save PDF data
        def save_pdf_data(highlights: dict, fund_names: dict, detected:dict, threshold: int):
            # Create a DataFrame
            df = pd.DataFrame({"title": fund_names.values(), "highlights": highlights.values(),"detected_indices":detected.values()})
            excel_path = self.REPORTPATH
            df.to_excel(excel_path)

            # Filter pages based on the threshold
            pages = df.loc[(df.highlights > threshold) & (df.title.str.contains(r"\w+"))].index.to_list()

            print(f"\nDoc saved at: {excel_path}")
            print(f"\nPages to extract: {pages}")

            # Open the file on the screen
            subprocess.Popen([excel_path], shell=True)

        save_pdf_data(important_pages, fund_titles, detected_indices, count)

        if output_path:
            subprocess.Popen([output_path], shell=True)

        return output_path, important_pages, fund_titles

                            
     #EXTRACT
    
    
    def get_clipped_data(self,input:str, pageSelect:list, bboxes:list[set], fund_names:dict):
    
        document = fitz.open(input)
        final_list = []
        
        for pgn in pageSelect:
            page = document[pgn]
            fundName = fund_names[pgn]

            blocks = []
            for bbox in bboxes:
                blocks.extend(page.get_text('dict', clip = bbox)['blocks']) #get all blocks
            
            filtered_blocks = [block for block in blocks if block['type']== 0 and 'lines' in block]
            sorted_blocks = sorted(filtered_blocks, key= lambda x: (x['bbox'][1], x['bbox'][0]))
            
            final_list.append({
            "pgn": pgn,
            "fundname": fundName,
            "block": sorted_blocks
            })
            
            
        document.close()
        return final_list
    
    def extract_data_relative_line(self,path: str,pageSelect:list, line_x: float, side: str, fund_names:dict):
        doc = fitz.open(path)
        final_list = []

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

    def get_pdf_data(self,input:str, pageSelect:list, fund_names:dict):
    
        document = fitz.open(input)
        finalData = []
        
        for pgn in pageSelect:
            #get the page
            page = document[pgn]
            fundName = fund_names[pgn]
        
            blocks = page.get_text('dict')['blocks'] #get all blocks
            filtered_blocks = [block for block in blocks if block['type']==0 and 'lines' in block] #type 0 are text
            sorted_blocks = sorted(filtered_blocks, key= lambda x: (x['bbox'][1], x['bbox'][0]))
            
            finalData.append({
                "page": pgn,
                "fundname": fundName,
                "block": sorted_blocks,
            })
                
        return finalData

    def extract_span_data(self,data:list, name:list): #all
        final_data = dict()
        for pgn,page in enumerate(data):
            pgn_content = []
            seen_entries = set()
            for blocks in page['block']:
                for line in blocks['lines']:
                    for span in line.get('spans',[]):
                        
                        text, size, color, origin, bbox, font = span['text'].strip(), round(span['size']), span['color'], span['origin'], span['bbox'],span['font']
                        entry = (size, text, color, origin, tuple(bbox), font)

                        # Check for uniqueness
                        if entry not in seen_entries:
                            seen_entries.add(entry)
                            pgn_content.append([size, text, color, origin, bbox, font])
                            
            final_data[page['fundname']] = pgn_content
        
        return final_data

    #CLEAN
    
    def combine_left_right_data(self, dataset:list):
        
        data = list()
        for left, right in zip(dataset[0], dataset[1]):
            pgn = left['pgn']
            fund = left['fundname']
            left_block = left['block']
            right_block = right['block']
            block = left_block + right_block
            
            data.append({
                'pgn':pgn,
                'fundname': fund,
                'block': block
            })
        
        return data
 
        
    def process_text_data(self,text_data: dict, data_conditions: list):
        remove_text = ['Note:','Note :','Mutual Fund investments are subject to market risks, read all scheme related documents carefully.','Scheme Features','SCHEME FEATURES',"2.",'Experience','and Experience','otherwise specified.','Data as on 31st December, 2024 unles','Ratio','DECEMBER 31, 2024','(Last 12 months):','FOR INVESTORS WHO ARE SEEKING^','Amount:','(Date of Allotment):','Rating Profile','p','P','Key Facts','seeking*:','This product is suitable for investors who are','product is suitable for them.','advisers if in doubt about whether the','*Investors should consult their financial','are seeking*:','This product is suitable for investors who','(Annualized)','(1 year)','Purchase', 'Amount', 'thereafter', '.', '. ', ',', ':', 'st', ';', "-", 'st ', ' ', 'th', 'th ', 'rd', 'rd ', 'nd', 'nd ', '', '`', '(Date of Allotment)']
        
        updated_text_data = {}

        for fund, data in text_data.items():
            blocks = data

            # Clean blocks
            cleaned_blocks = []
            for block in blocks:
                size, text, color, origin, bbox,font = block
                if text not in remove_text:
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
                y_coord = math.ceil(block[3][1])  # Extract and round the y-coordinate
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

    def create_nested_dict(self,cleaned_data:dict,header_size:float, content_size:float):
            final_text_data = dict()
            final_matrix = dict()

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
                current_header = None
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
                        
                final_text_data[fund] = nested_dict        
                # matrix_df = pd.DataFrame(matrix, index=coordinates, columns=sizes)
                # final_matrix[fund] = matrix_df
            
            return final_text_data, final_matrix


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
                print(f"Error while parsing fund {e}")
                
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
                    
                except Exception:
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
            final_data_generated = {}

            for page in pdf.pages:
                text = page.extract_text()
                clean_text = text.encode("ascii", "ignore").decode()
                content = clean_text.split('\n')
                main_key = content[0]
                values = content[1:]
                final_data_generated[main_key] = values

        return {key: final_data_generated[key] for key in sorted(final_data_generated)}

    def get_generated_content(self, data:dict, path:str):
        extracted_text = dict()
        unextracted_text = dict()
        for fund, items in data.items():
            
           try:
               
                self.__generate_pdf_from_data(items, path)
                print(f'\n-----{fund}------', f'\nPDF Generated at: {path}')
                extracted_text[fund] = self.__extract_data_from_pdf(path)
                
           except Exception as e:
               
               print(f"\nError while processing fund '{fund}': {e}")
               continue
                
                
        return extracted_text
    



