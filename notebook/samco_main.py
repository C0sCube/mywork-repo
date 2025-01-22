from pdf_parse import Reader
import pprint
import pandas as pd


#SET PATHS
dir_path = r"C:\Users\Kaustubh.keny\OneDrive - Cogencis Information Services Ltd\Documents\mywork-repo"
#dir_path = r"C:\Users\rando\OneDrive\Documents\mywork-repo"
pdfReader = Reader(dir_path)
samco_path = pdfReader.get_file_path(r'\files\SamcoFactSheet2024.pdf')
dry_path  = pdfReader.get_file_path(r'\output\DryRun.pdf')



#FUND DATASET
fund_data = [[25,20],r"^(samco|tata).*fund$",20] #flag, regex_fund_name, font_size, font_color
path = pdfReader.get_file_path(r"\files\financial_indices.xlsx")
indices = pdfReader.get_financial_indices(path)

paths, fund_names, imp_pages = pdfReader.check_and_highlight(samco_path,indices, fund_data)
pdfReader.save_pdf_data(imp_pages,fund_names)

#GET ACCURATE DATA
user_input = input("Enter the pages to get data from: ")
pages= list(map(int, user_input.split()))
bbox = [(35,120,250,765)]
fund = fund_names

document_data = pdfReader.get_clipped_data(samco_path, pages, bbox, fund)
text_data = pdfReader.extract_span_data(document_data,[])
data_cond = [[9.0,8.0],-1,20.0] #sizes, color, set_size
cleaned_data = pdfReader.process_text_data(text_data, data_cond)
final_text_data, final_matrix = pdfReader.create_nested_dict(cleaned_data, 20.0 , 10.0)


#NESTED DICT
final_extracted_text = dict()
for fund, items in final_text_data.items():
    print(fund)
    pdfReader.generate_pdf_from_data(items, dry_path)
    extract_data = pdfReader.extract_data_from_pdf(dry_path)
    final_extracted_text[fund] = extract_data
    
    
    
# for fund, items in final_extracted_text.items():
#     print(f"\n{fund}______________________\n")
#     for key, value in items.items():
#         print(f'\n--{key}--\n')
#         print(value)
        
import json

json_path  = pdfReader.get_file_path(r"\output\dump.json")
with open(json_path, "w", encoding="utf-8") as file:
    json.dump(final_extracted_text, file, ensure_ascii=False, indent=4)
    print("JSON CREATED\n")
print('done')