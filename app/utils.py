import os, re, json, pprint, pickle
import fitz #type:ignore
from datetime import datetime
from collections import defaultdict
import pandas as pd #type:ignore
from functools import reduce

class Helper:
    
    def __init__(self):
        pass
    
    #PARSING UTILS
    @staticmethod
    def get_fund_paths(path:str):
        mutual_fund_paths = {}

        for root, dirs, files in os.walk(path):
            
            file_found = False
            for name in files:
                if name.endswith((".pdf")) and not file_found:
                    tmp = root.split("\\")
                    key = tmp[-1]
                    value = rf'{root}\{name}'
                    mutual_fund_paths[key] = value
                    file_found = True
        
        return mutual_fund_paths

    @staticmethod
    def _get_financial_indices(path:str):
        
        df = pd.read_excel(path)
        financial_indexes = df['indexes'].tolist()
        return set(financial_indexes)
    
    @staticmethod
    def _save_pdf_data(data,excel_path:str, threshold: int):
    
        df = pd.DataFrame(data)
        
        if 'detect_idx' in df.columns: #try catch required
            df_exp = df["detect_idx"].apply(lambda x: pd.Series(x) if isinstance(x, list) else pd.Series())
            df_exp.columns = [f"idx_{i+1}" for i in range(df_exp.shape[1])]
            df_exp = df_exp.dropna(axis=1, how='all') #drop empty values
            df_final = pd.concat([df.drop(columns=["detect_idx"]), df_exp], axis=1)
            
        df_final.to_excel(excel_path, engine="openpyxl", index=True)

        # Filter pages based on the threshold
        pages = df.loc[ (df["highlights"] >= threshold) & (df["title"].str.contains(r"\w+", na=False, regex=True))].index.to_list()
               
        print(f"\nDoc Saved At: {excel_path}")
        print(f"\nPages to Extract: {pages}")

        # Open the file on the screen
        # subprocess.Popen([excel_path], shell=True)
        return df_final
    
    #JSON UN/LOAD 
    @staticmethod
    def quick_json_dump(extracted_text, path:str, indent=4):
        
        current = str(datetime.now().strftime('%H_%M'))
        fund_name = list(extracted_text.keys())[0].split(" ")[0]
        output_path = path.replace(".json",f'_{fund_name}_{current}.json')
        with open(output_path, "w") as file:
            json.dump(extracted_text, file, indent=indent)
        
        print(f'\n JSON saved at {output_path}')
    
    @staticmethod
    def quick_json_load(path:str):
        try:
            with open(path, "r", encoding="utf-8") as file:
                data = json.load(file)
            print(f"\n JSON loaded from {path}")
            return data
        except Exception as e:
            print(f"Error loading JSON: {e}")
            return None
    
    
    
    #NESTED DICT CRUD OPS
    @staticmethod
    def merge_nested_dicts(*dicts):
        return {key: reduce(lambda acc, d: {**acc, **d.get(key, {})}, dicts, {}) for key in dicts[0].keys()}

    @staticmethod
    def drop_empty_dict_values(final_dict:dict):
        finally_dict = {}
        for fund, content in final_dict.items():
            non_empty_dict = {}
            for key, value in content.items():
                if len(value)>=1:
                    non_empty_dict[key] = value
            finally_dict[fund] = non_empty_dict
        return finally_dict
    
    @staticmethod
    def drop_selected_dict_values(final_dict:dict, patterns:list):
        finally_dict = {}
        for fund, content in final_dict.items():
            clean_dict = {}
            for k, v in content.items():
                if not any(re.search(pattern, k) for pattern in patterns):
                    clean_dict[k] = v
            finally_dict[fund] = clean_dict
        return finally_dict
    
    @staticmethod
    def select_dict_with_keys(final_dict: dict, patterns: list):
        selected_dict = {}
        for fund, content in final_dict.items():
            filtered_dict = {k: v for k, v in content.items() if any(re.search(pattern, k) for pattern in patterns)}
            selected_dict[fund] = filtered_dict

        return selected_dict
    
    @staticmethod
    def drop_keys_by_regex(data, patterns):
        if not isinstance(data, dict):
            return data
        
        regex_list = [re.compile(pattern) for pattern in patterns]
        final_dict = {}
        for key, value in data.items():
            if any(regex.match(key) for regex in regex_list):
                continue
            
            if isinstance(value, dict): #dict
                final_dict[key] = Helper.drop_keys_by_regex(value, patterns)
            elif isinstance(value, list): #list
                final_dict[key] = [Helper.drop_keys_by_regex(item, patterns) if isinstance(item, dict) else item for item in value]
            else:
                final_dict[key] = value
        
        return final_dict
    
    @staticmethod
    def merge_key_values(data, key1, key2):
        if isinstance(data, dict):
            if key1 in data and key2 in data:
                val1, val2 = data[key1], data[key2]

                if isinstance(val1, list) and isinstance(val2, list):
                    data[key1] = val1 + val2  # Merge lists
                elif isinstance(val1, dict) and isinstance(val2, dict):
                    merged_dict = defaultdict(dict, val1)
                    for k, v in val2.items():
                        if k in merged_dict and isinstance(merged_dict[k], dict) and isinstance(v, dict):
                            merged_dict[k].update(v)  # Merge nested dicts
                        else:
                            merged_dict[k] = v
                    data[key1] = dict(merged_dict)
                elif isinstance(val1, str) and isinstance(val2, str):
                    data[key1] = val1 + " " + val2  # Concatenate strings
                else:
                    data[key1] = [val1, val2]  # Handle mixed types as a list

                del data[key2]  # Remove key2 after merging

            for k, v in data.items():  # Recursively merge nested dictionaries
                Helper.merge_key_values(v, key1, key2)

        elif isinstance(data, list):  # Handle lists of dictionaries
            for item in data:
                Helper.merge_key_values(item, key1, key2)

        return data
   
   
   
    #PDF CRUD
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
        Args:input_pdf_path(str) , output_pdf_path (str)
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
                    shape.finish(color=(1,0,0), fill=(1, 0.75, 0.8), width=0.8, fill_opacity = .3)  # Pink fill, no border color
                    shape.commit()
            


        doc.save(output_path)
        print(f"Modified PDF saved to: {output_path}")
        #open the file on screen
        import subprocess
        subprocess.Popen([output_path],shell=True)

    @staticmethod
    def draw_boundaries_on_lines(input_pdf_path:str, path:str):
        """Open the pdf , get all text data and blocks and draw a boundary along each boundary boxes
        Args:input_pdf_path(str) , output_pdf_path (str)
        Returns: nothing, a new pdf created"""
        # Open the PDF file
        doc = fitz.open(input_pdf_path)
        for page in doc:
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                if "lines" in block:
                    for line in block["lines"]:
                        
                        bbox = line["bbox"]  # The bbox is now directly accessible from the line
                        page.draw_rect(bbox, color=(.4, 0.647, 0.0), width=1.5, overlay=False)
        
        
        output_path = path.replace('.pdf', '_line_highlighted.pdf')
        doc.save(output_path)
        doc.close()
        
    @staticmethod
    def draw_boundaries_on_pdf(input_pdf_path:str, path:str):
        """Open the pdf , get all text data and blocks and draw a boundary along each boundary boxes
        Args:input_pdf_path(str) , output_pdf_path (str)
        Returns: nothing, a new pdf created"""
        # Open the PDF file
        doc = fitz.open(input_pdf_path)
        for page in doc:
            blocks = page.get_text("blocks")  # Get the blocks of text on the page
            for block in blocks:
                bbox = block[:4]  # The bbox is the first four elements of the block
                # Draw a rectangle with an orange border around the bbox
                page.draw_rect(bbox, color=(1.0, 0.647, 0.0), width=1.5, overlay=False)
        
        # Save the modified document to a new file
        
        output_path = path.replace('.pdf', '_block_highlighted.pdf')
        doc.save(output_path)
        doc.close()
        
    @staticmethod
    def draw_bboxes_on_pdf(input_pdf_path:str, bbox:tuple):
        
        doc = fitz.open(input_pdf_path)
        for page in doc:
            page.draw_rect(bbox, color = (1.0,0,1.0), width = 1.5, overlay = False)

        output_path = input_pdf_path.replace('.pdf', '_bbox_highlighted.pdf')
        doc.save(output_path)
        doc.close()
    
    @staticmethod
    def get_structure(obj, level=0):
        """Recursively prints the structure of a nested list/dictionary."""
        indent = "  " * level  # Indentation for readability
        
        if isinstance(obj, list):
            print(f"{indent}List of {len(obj)} items")
            if obj:  # Check if the list is not empty
                Helper.get_structure(obj[0], level + 1)  # Check structure of first element
                
        elif isinstance(obj, dict):
            print(f"{indent}Dictionary with keys: {list(obj.keys())}")
            for key, value in obj.items():
                Helper.get_structure(value, level + 1)
                
        else:
            print(f"{indent}{type(obj).__name__}")

    
