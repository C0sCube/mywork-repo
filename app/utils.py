import os, re, json, string, shutil
import fitz #type:ignore
from datetime import datetime
from collections import defaultdict
import pandas as pd #type:ignore

from app.program_logger import get_logger


class Helper:
    
    def __init__(self):
        self.logger = get_logger()
    
    #PARSING UTILS
    @staticmethod
    def get_pdf_with_id(path: str) -> dict:
        pdf_paths = {}
        suffix_map = {}

        for root, _, files in os.walk(path):
            for file_name in files:
                if file_name.endswith("FS.pdf"):
                    full_path = os.path.join(root, file_name)
                    # folder_name = os.path.basename(root).title()

                    parts = file_name.split("_")
                    fund_id = parts[0]

                    is_passive = len(parts[-2]) == 1 #determine passive
                    suffix = parts[-2] if is_passive else "0"
                    fund_key = f"{fund_id}_{suffix}"
                    # fund_name = f"{folder_name} Passive" if is_passive else folder_name

                    # print(fund_name)
                    pdf_paths[fund_key] = (file_name, full_path)

                elif file_name.endswith("KIM.pdf") or file_name.endswith("SID.pdf"):
                    full_path = os.path.join(root, file_name)
                    # folder_name = os.path.basename(root).title()

                    parts = file_name.split("_")
                    fund_id = parts[0]
                    pdf_paths[fund_id] = (file_name, full_path)
        return pdf_paths
                    
    @staticmethod
    def get_pdf_paths(base_path: str) -> dict:
        pdf_paths = {}
        suffix_map = {}
        for root, _, files in os.walk(base_path):
            folder_name = os.path.basename(root).title()

            for file_name in files:
                if file_name.lower().endswith(".pdf"):
                    full_path = os.path.join(root, file_name)
                    key = folder_name

                    if key in pdf_paths:
                        suffix = string.ascii_uppercase[suffix_map[key]]
                        key = f"{folder_name}_{suffix}"
                        suffix_map[folder_name] += 1
                    else:
                        suffix_map[folder_name] = 1

                    pdf_paths[key] = full_path
        return pdf_paths

    @staticmethod
    def get_amc_paths(base_path: str) -> dict:
        """Returns a mapping of fund keys to (fund name, file path) for all FS.pdf files in a directory."""
        fund_paths = {}
        logger = get_logger()
        logger.info(f"AMC At: {base_path}")
        for root, _, files in os.walk(base_path):
            # print(files)
            for file_name in files:
                if file_name.endswith("FS.pdf"):
                    # print(file_name)
                    full_path = os.path.join(root, file_name)
                    folder_name = os.path.basename(root).title()

                    parts = file_name.split("_")
                    fund_id = parts[0]

                    is_passive = len(parts[-2]) == 1 #determine passive
                    suffix = parts[-2] if is_passive else "0"
                    fund_key = f"{fund_id}_{suffix}"
                    fund_name = f"{folder_name} Passive" if is_passive else folder_name

                    # print(fund_name)
                    fund_paths[fund_key] = (fund_name, full_path)

                elif file_name.endswith("KIM.pdf") or file_name.endswith("SID.pdf"):
                    full_path = os.path.join(root, file_name)
                    folder_name = os.path.basename(root).title()

                    parts = file_name.split("_")
                    fund_id = parts[0]
                    fund_paths[fund_id] = (folder_name, full_path)
                     
        return fund_paths

    @staticmethod
    def get_fund_paths(path:str):
        mutual_fund_paths = {}
        for root, dirs, files in os.walk(path):
            file_found = False
            for name in files:
                if name.endswith((".pdf")) and not file_found:
                    tmp = root.split("\\")
                    key = tmp[-1].title()
                    value = rf'{root}\{name}'
                    mutual_fund_paths[key] = value
                    file_found = True
        
        return mutual_fund_paths
    
    @staticmethod
    def create_subdirs(base_path, folder_names):
        paths = {}
        for name in folder_names:
            dir_path = os.path.join(base_path, name)
            os.makedirs(dir_path, exist_ok=True)
            paths[f"{name.upper()}_DIR"] = dir_path
        return paths

    @staticmethod
    def _get_financial_indices(path:str):
        df = pd.read_excel(path)
        financial_indexes = df['indexes'].tolist()
        return set(financial_indexes)
    
    @staticmethod
    def pdf_report(data, path: str, sheet_name:str):
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
        logger = get_logger()
        logger.warning(f"Report:Sheet Name -> {sheet_name} Saved.")
        return df_final
    
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

        # logger.info(f"Deleted PDFs. {suffixes}")
        return deleted_files
    
    @staticmethod
    def copy_pdfs_to_folder(dest_folder: str, data):
        os.makedirs(dest_folder, exist_ok=True)

        if isinstance(data, dict):
            file_paths = list(data.values())
        elif isinstance(data, list):
            file_paths = data
        else:
            raise ValueError("Data must be a list of paths or a dict with path values")

        for path in file_paths:
            if not os.path.isfile(path):
                continue
            try:
                file_name = os.path.basename(path)
                dest_path = os.path.join(dest_folder, file_name)
                shutil.copy2(path, dest_path)
            except Exception as e:
                logger = get_logger()
                logger.error(f"Failed to copy '{path}' → {dest_folder}: {e}")
    
    @staticmethod
    def delete_files_and_empty_folder(file_path: str) -> bool:
        try:
            # print(file_path)
            if os.path.exists(file_path):
                os.remove(file_path)
                
                parent_dir = os.path.dirname(file_path)
                print("Remaining:", os.listdir(parent_dir))

                if os.path.isdir(parent_dir) and not os.listdir(parent_dir):
                    os.rmdir(parent_dir)
                return True
            return False
        except Exception as e:
            logger = get_logger()
            logger.exception(f"delete_file_and_empty_folder -> {e}")
            return False
        
    @staticmethod
    def delete_amc_pdf(data):
        try:
            for k, path in data.items():
                Helper.delete_files_and_empty_folder(path)
        except Exception as e:
            logger = get_logger()
            logger.exception(f"delete_amc_pdf: {e}")
            return
        return
    
    #JSON UN/LOAD 
    @staticmethod
    def save_json(data: dict, path: str, indent: int = 2):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent)

    @staticmethod
    def load_json(path: str):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    
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
            


    
    
