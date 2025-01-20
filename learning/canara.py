import PyPDF2
import re
 
#path = r"C:\Users\Kaustubh.keny\OneDrive - Cogencis Information Services Ltd\Documents\mywork-repo"
path = r"C:\Users\rando\OneDrive\Documents\mywork-repo"
filename = r"\files\factsheet-march-2022.pdf"
 
read_file = PyPDF2.PdfReader(path + filename)
 
num_pages = len(read_file.pages)
data_all = []
 
i = 1
for i in range(num_pages):
    files = read_file.pages[i]
    data = files.extract_text()
    i += 1
    print(f"page number : {i}")
    data_all.append(data)
 
    # mention_start = ["FUND MANAGER :","TOTAL EXPERIENCE :"]
    # mention_end = ["TOTAL EXPERIENCE :","MANAGING THIS FUND :"]
    # header_pattern =  r"CANARA[^\n]*"
 
    # patterns = [r'({start}.+?){end}(.*?)(?={start}|$)'.format(start=re.escape(start), end=re.escape(end)) for start, end
    #             in zip(mention_start, mention_end)]
 
    # headers = re.findall(header_pattern, data)
 
    # if headers:
    #     scheme_name = headers[0]
    #     print("HEADER : ", scheme_name)
    #     print("=================")
 
    # for pattern in patterns:
    #     matches = re.finditer(pattern, data, re.DOTALL)
    #     for match in matches:
    #         extracted_text = match.group(1).strip()
    #         print(f"{extracted_text}")
    #         print("-----------------")