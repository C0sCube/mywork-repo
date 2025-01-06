import pandas as pd
import pickle as pkl

path = r"C:\Users\Kaustubh.keny\OneDrive - Cogencis Information Services Ltd\Documents\mywork-repo"

sheet_path = r"\imp_incides.xlsx"

pkl_path = path + r"\output\pkl\market_indices.pkl"

file_path = path +sheet_path

file = pd.read_excel(file_path)

fields = file['Fields In Factsheet']
#print(fields.to_list())

file_path = path + pkl_path
with open(file_path, 'wb') as f:
    pkl.dump(fields, f)

#print(file)