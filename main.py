
from app.fundData import *
from app.helper import Helper

import os, configparser

config = configparser.ConfigParser()
config.read('config.ini')

BASE_PATH = config['path']["BASE_PATH"]
FUND_PATH = config['path']['FUND_PATH']

dry_path = config['path']['drypath']
fin_path = config['path']['indicepath']
indice_path  = config['path']['indicepath']
report_path  = config['path']['reportpath']
json_path = BASE_PATH + config['path']['jsonpath']


mutual_fund = Helper.get_fund_paths(FUND_PATH)

object = Samco(BASE_PATH, dry_path, fin_path, report_path)
file_path = mutual_fund['Samco Mutual Fund']


fund_data = object.PARAMS['fund']
line_x = object.PARAMS['line_x']
data_cond = object.PARAMS['data']
bbox = object.PARAMS['clip_bbox']

path, imp, fund_titles = object.check_and_highlight(file_path, fund_data, 7)

pages =  [3, 5, 7, 9, 11, 13, 15, 17, 18]

data = object.get_clipped_data(file_path,pages,bbox, fund_titles)
data = object.extract_span_data(data,[])
clean_data = object.process_text_data(data, data_cond) 
nested_data, matrix = object.create_nested_dict(clean_data,20.0, 10.0)
extracted_text = object.get_generated_content(nested_data, object.DRYPATH)

Helper.dump_pickle_data(extracted_text,json_path)

