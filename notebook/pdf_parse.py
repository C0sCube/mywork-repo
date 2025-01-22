import os, re, math, pprint
import pandas as pd
import numpy as np
import fitz
from collections import defaultdict
import pdfplumber


class Reader:
    
    BASEPATH  = ''
    DRYPATH = ''
    
    def __init__(self, path:str):
        self.BASEPATH = path
    
    def get_file_path(self, path:str):
        return self.BASEPATH + path
    
    
    #HIGHLIGHT
    def get_financial_indices(self, path:str):
        
        if not os.path.exists(path):
            print('File does not exists')
            return
        
        df = pd.read_excel(path)
        financial_indexes = df['indexes'].tolist()
        return set(financial_indexes)
    
    def check_and_highlight(self, path:str, indices:list,fund_data:list):
        
        document = fitz.open(path)
        document_page_count = document.page_count
        
        
        #initialize imp datasets
        pages = [i for i in range(document_page_count)]
        important_pages = dict.fromkeys(pages,0)
        fund_titles = dict.fromkeys(pages,'')
        
        for dpgn, page in enumerate(document):
            
            pageBlocks = page.get_text('dict')
            pageTexts = pageBlocks['blocks']
            
            sortedPageTexts = sorted(pageTexts, key=lambda x:(x['bbox'][1],x['bbox'][0]))
            
            for count,block in enumerate(sortedPageTexts):
                
                if 'lines' not in block:
                    continue
                for line in block['lines']:
                    for span in line['spans']:
                        text = span['text'].strip().lower()
                        size = span['size']
                        flag = span['flags']
                        color = span['color']
                        
                        if flag in fund_data[0]:   
                        #CHECK IF PAGE IS FUND
                            fund_conditons = [
                                count in range(0,15),
                                re.match(fund_data[1], text, re.IGNORECASE),
                                size >=fund_data[2],
                                #color in fund_data[3]
                            ]
                            
                            if all(fund_conditons):
                                fund_titles[dpgn] = text
                                #print(fund_titles)
                                #highlight
                                rect = fitz.Rect(span['bbox'])
                                page.add_rect_annot(rect)
                            
                        #CHECK IF INDICES EXISTS IN PAGE AND COUNT
                            financial_indices = indices
                            for indice in financial_indices:
                                pattern = rf'\b{re.escape(indice)}\b' 
                                if re.search(pattern, text):
                                    
                                    important_pages[dpgn]+=1
                                    #highlight
                                    rect = fitz.Rect(span['bbox'])
                                    page.add_highlight_annot(rect)
                                    break #one highlight
        output_path = None
        if any(important_pages.values()):
            output_path = path.replace('.pdf','_highlighted.pdf')
            document.save(output_path)
        document.close()
        
        return output_path, fund_titles, important_pages
                            
     #EXTRACT
    
    def save_pdf_data(self,highlights:dict,fund_names:dict):
           
        pagedf = pd.DataFrame({"title":fund_names.values(),
                               "highlights": highlights.values()})
        excel_path = self.BASEPATH + r'\output\pdf_report.xlsx'
        pagedf.to_excel(excel_path)
        
        print(f'\nDoc saved at {excel_path}')
    
    def get_clipped_data(self,input:str, pageSelect:list, bbox:list[set], fund_names:dict):
    
        document = fitz.open(input)
        finalData = []
        
        for pgn in pageSelect:
            #get the page
            page = document[pgn]
            fundName = fund_names[pgn]
        
            blocks = page.get_text('dict', clip = bbox[0])['blocks'] #get all blocks
            
            filtered_blocks = [block for block in blocks if block['type']==0 and 'lines' in block]
            sorted_blocks = sorted(filtered_blocks, key= lambda x: (x['bbox'][1], x['bbox'][0]))
            
            finalData.append({
                "page": pgn,
                "fundname": fundName,
                "block": sorted_blocks,
            })
                
        return finalData

    def get_pdf_data(self,input:str, pageSelect:list, fund_names:dict):
    
        document = fitz.open(input)
        finalData = []
        
        for pgn in pageSelect:
            #get the page
            page = document[pgn]
            fundName = fund_names[pgn]
        
            blocks = page.get_text('dict')['blocks'] #get all blocks
            
            filtered_blocks = [block for block in blocks if block['type']==0 and 'lines' in block]
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
            for blocks in page['block']:
                for line in blocks['lines']:
                    spans = line.get('spans',[])
                    for span in spans:
                        
                        text = span['text'].strip()
                        size = span['size']
                        color = span['color']
                        origin = span['origin']
                        bbox = span['bbox']
                    
                        pgn_content.append([size,text,color,origin,bbox])
                        
            final_data[page['fundname']] = pgn_content
        
        return final_data

    
    #CLEAN
    def clean_block_data(self,blocks:dict, data_conditions:list):
        
        remove_text = ['Purchase','Amount','thereafter','.','. ',',',':','st',";","-",'st ',' ','th', 'th ', 'rd', 'rd ', 'nd', 'nd ','','`','(Date of Allotment)']
        
        sorted_blocks = sorted(blocks, key=lambda x: (x[3][1],x[3][0]))
        
        cleaned_blocks = []
        for block in sorted_blocks:
            size, text, color, origin, bbox = block
            if text not in remove_text:
                cleaned_blocks.append(block)
    
        processed_blocks = []
        # adjust size based on color and size
        for block in cleaned_blocks:
            size, text, color, origin, bbox = block
            text = text.strip()
            if size in data_conditions[0] and color == data_conditions[1]:
                size = data_conditions[2]  # Update size to 20.0
            processed_blocks.append([size, text, color, origin, bbox])
                    

        # group blocks by rounded y-coordinate
        grouped_blocks = defaultdict(list)
        for block in processed_blocks:
            y_coord = math.ceil(block[3][1])# Extract and round the y-coordinate
            size = block[0]
            grouped_blocks[(y_coord,size)].append(block)

        # Combine blocks with the same y-coordinate
        combined_blocks = []
        for key, group in grouped_blocks.items():
            
            if key[1] == data_conditions[2]:
                combined_text = " ".join(item[1] for item in group).strip()
                if combined_text:  # Ignore whitespace-only text
                    size, color, origin, bbox = group[0][0], group[0][2], group[0][3],group[0][4]
                    combined_blocks.append([size, combined_text, color, origin,bbox])
            
            else:
                for item in group:
                    combined_blocks.append(item)

        return combined_blocks

    def process_text_data(self,text_data:dict, data_conditions:list):

        updated_text_data = {}

        for fund, data in text_data.items():
            blocks = data
            cleaned_blocks = Reader.clean_block_data(self,blocks, data_conditions)
            updated_text_data[fund] = cleaned_blocks

        return updated_text_data


    #PROCESS
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
    
    def generate_pdf_from_data(self,data:list, output_path:str):
        
        pdf_doc = fitz.open()
        
        for header, items in data.items():
            
            page = pdf_doc.new_page()
            text_position = 72  # for title initalize something

            #section title
            title_font_size = 24
            try:
                page.insert_text(
                    (72, text_position), #initalizor
                    header,
                    fontsize=title_font_size,
                    fontname="helv",
                    color=(0, 0, 1),
                )        
            except Exception as e:
                print(f"Error while parsing fund {e}")
                
            for item in items:
                size,text,color,bbox = item
    
                #Errror in fitz font 
                try:
                    page.insert_text(
                        (bbox[0], bbox[1]),
                        text,
                        fontsize=size,
                        fontname="helv",
                        color=tuple(int(color & 0xFFFFFF) for _ in range(3)))#unsigned int value so (0,0,0)
                    
                except Exception:
                    page.insert_text(
                        (bbox[0], bbox[1]),
                        text,
                        fontsize=size,
                        fontname="helv",
                        color=(1, 0, 0),
                    )

        # Save the created PDF
        pdf_doc.save(output_path)
        pdf_doc.close()
        print(f" pdf generated to: {output_path}")

    def extract_data_from_pdf(self,path:str):
        
        def replace_main_key(string: str):
            replace_key = string
            if re.match(r'^nav', string, re.IGNORECASE):
                replace_key = "nav" 
            elif "market" in string.lower():
                replace_key = "market_capitalization"
            elif re.match(r"^assets_under", string, re.IGNORECASE):
                replace_key = "assets_under_management"   
            return replace_key
        
        with pdfplumber.open(path) as pdf:
            final_data = []
            final_data_generated = {}
            
            for page in pdf.pages:
                # extract text from the page
                text = page.extract_text()
                final_data.append(text)
            
            #store them in a dict for each page
            for data in final_data:
                content = data.split('\n')
                #first val is the header and the rest are content
                main_key = replace_main_key(content[0])
                values = content[1:]
            
                final_data_generated[main_key] = values

            #sort the headers in lex order
            sorted_final_generated = {key: final_data_generated[key] for key in sorted(final_data_generated)}

        return sorted_final_generated

# if __name__ =='__main__':
    
#     print("hello")


