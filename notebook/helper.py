import os, re, json
import pprint
import fitz
import pickle

import nltk
from nltk import word_tokenize, pos_tag, ne_chunk
from nltk.tree import Tree

# Download required data
nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')
nltk.download('maxent_ne_chunker')
nltk.download('words')

class Helper:
    
    def __init__(self):
        pass
    
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
    
    """Open the pdf , draw lines on the mentioned pages
    Args:input_pdf_path(str) , output_pdf_path (str)
    Returns: nothing, a new pdf created"""
    
    @staticmethod
    def draw_lines_on_pdf(pdf_path: str, lines: list, rects:list, pages:list,output_path: str):
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
    
   
    """Open the pdf , get all text data and blocks and draw a boundary along each boundary boxes
    Args:input_pdf_path(str) , output_pdf_path (str)
    Returns: nothing, a new pdf created"""
    
    @staticmethod
    def draw_boundaries_on_lines(input_pdf_path:str, path:str):
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
        
    """Open the pdf , get all text data and blocks and draw a boundary along each boundary boxes
    Args:input_pdf_path(str) , output_pdf_path (str)
    Returns: nothing, a new pdf created"""
    
    @staticmethod
    def draw_boundaries_on_pdf(input_pdf_path:str, path:str):
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
    def dump_pickle_data(data:dict, file_path:str):
        try:
            with open(file_path, 'wb') as file:
                pickle.dump(data, file)
            print(f"Data successfully dumped to {file_path}")
        except Exception as e:
            print(f"Error while dumping data to {file_path}: {e}")

    @staticmethod
    def load_pickle_data(file_path:str):

        try:
            with open(file_path, 'rb') as file:
                data = pickle.load(file)
            print(f"Data successfully loaded from {file_path}")
            return data
        except Exception as e:
            print(f"Error while loading data from {file_path}: {e}")
            return None

    @staticmethod
    def is_it_a_name():

        # Sample text
        text = "Aman Chopra and Luke Illingworth are working on a project with Sarah Connor."

        # Tokenize, POS tagging, and Named Entity Recognition
        def extract_names(text):
            chunks = ne_chunk(pos_tag(word_tokenize(text)))
            names = []
            for chunk in chunks:
                if isinstance(chunk, Tree) and chunk.label() == 'PERSON':
                    names.append(' '.join(c[0] for c in chunk))
            return names

        names = extract_names(text)
        print("Detected Names:", names)

    