import os
import re
import pandas as pd
import fitz


class Reader:
    
    BASEPATH  = ''
    DRYPATH = ''
    
    def __init__(self, path:str):
        self.BASEPATH = path
    
    def get_file_path(self, path:str):
        return self.BASEPATH + path
    
    
    def get_financial_indices(self, path:str):
        
        if not os.path.exists(path):
            print('File does not exists')
            return
        
        df = pd.read_excel(path)
        financial_indexes = df['indexes'].tolist()
        return set(financial_indexes)
    
    def check_and_highlight(self, path:str, indices:list,fund_pattern: str, fund_size:int):
        
        document = fitz.open(path)
        document_page_count = document.page_count
        
        #FUND DATASET
        fund_data = [[25,20,16,4],r"^(samco|tata|canara)",10]
        
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
                        
                    #CHECK IF PAGE IS FUND
                        fund_conditons = [
                            count in range(0,15),
                            re.match(fund_data[1], text, re.IGNORECASE),
                            size in range(fund_data[2]-4,fund_data[2]+4),
                            flag in fund_data[0]
                        ]
                        
                        if all(fund_conditons):
                            fund_titles[dpgn] = text
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
                            
            
        
        
       
       
    
    
    

if __name__ =='__main__':
    
    pdfReader = Reader(r"C:\Users\rando\OneDrive\Documents\mywork-repo")
    
    path = pdfReader.get_file_path(r"\files\financial_indices.xlsx")
    
    lol = pdfReader.get_financial_indices(path)
    samco_path = pdfReader.get_file_path(r'\files\SamcoFactSheet2024.pdf')
    paths,fund,imp = pdfReader.check_and_highlight(samco_path,lol,r'lol',10)
    
    print(fund)

