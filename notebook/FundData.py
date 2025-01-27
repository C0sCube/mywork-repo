import re
import os
from pdfParse import Reader
import fitz


class Samco(Reader):
    
    PARAMS = {
        'fund': [[25,20],r"^(samco|tata).*fund$",[18,28],[-1]], #FUND NAME DETAILS order-> [flag], regex_fund_name, range(font_size), [font_color]
        'clip_bbox': [(35,120,250,765)],
        'line_x': 200.0,
        'data': [[9,10],-1,20.0,['Inter-SemiBold']] #sizes, color, set_size font_name
    }
    
    def __init__(self, path: str,dry:str,fin:str):
        super().__init__(path,dry,fin)
    
    def return_required_header(self,string: str):
            replace_key = string
            if re.match(r'^nav.*', string, re.IGNORECASE):
                replace_key = "nav"
            elif re.match(r"^market", string, re.IGNORECASE):
                replace_key = "market_capital"  
            elif re.match(r"^assets", string, re.IGNORECASE):
                replace_key = "assets_under_management"
            elif re.match(r"^fund", string, re.IGNORECASE):
                replace_key = "fund_manager" 
            elif re.match(r"^scheme", string, re.IGNORECASE):
                replace_key = "scheme_details" 
            elif re.match(r"^investment", string, re.IGNORECASE):
                replace_key = "investment_objective"
            elif re.match(r"^quanti", string, re.IGNORECASE):
                replace_key = "quantitative_data"
            elif re.match(r"^portfolio", string, re.IGNORECASE):
                replace_key = "portfilio" 
            elif re.match(r"^industry", string, re.IGNORECASE):
                replace_key = "industry_allocation_of_equity"       
            return replace_key
    
    #REGEX FUNCTIONS
    def __return_invest_data(self,key:str,data:list):
        investment_objective = data
        values = " ".join(txt for txt in investment_objective)

        data = {
            key:values
        }

        return data

    def __return_scheme_data(self,key:str,data:list):
        scheme_data = data
        main_key = key
        structured_data = {main_key: {}}

        # Patterns
        date_pattern = r"^(.*?date)\s(\d{2}-[A-Za-z]{3}-\d{4})$"
        benchmark_pattern = r"^(Benchmark)\s+(.*)$"
        application_pattern = r"(?:·)?\d+(?:,\d{3})*(?:\.\d+)?/-"

        for data in scheme_data:
            if re.search(date_pattern, data, re.IGNORECASE):
                match = re.match(date_pattern, data, re.IGNORECASE)
                if match:
                    key = match.group(1)
                    value = match.group(2)
                    structured_data[main_key][key] = value
            elif re.search(benchmark_pattern, data, re.IGNORECASE):
                match = re.match(benchmark_pattern, data, re.IGNORECASE)
                if match:
                    key = match.group(1)
                    value = match.group(2)
                    structured_data[main_key][key] = value
            elif re.search(r"\b(min|application)\b", data, re.IGNORECASE):
                matches = re.findall(application_pattern, data, re.IGNORECASE)
                if matches:
                    cleaned_matches = [match.replace('·', '') for match in matches]
                    structured_data[main_key]["min_appl_amt"] = cleaned_matches
            elif re.search(r"\b(additional.* and in multiples of)\b", data, re.IGNORECASE):
                matches = re.findall(application_pattern, data, re.IGNORECASE)
                if matches:
                    cleaned_matches = [match.replace('·', '') for match in matches]
                    structured_data[main_key]["additional_amt"] = cleaned_matches

        return structured_data

    def __return_fund_data(self,key:str,data:list):
        fund_manager = data
        main_key = key
        strucuted_data = {main_key:[]}
        current_entry = None
        name_pattern = r'^(Ms\.|Mr\.)'
        manage_pattern = r'^\(|\)$'
        date_pattern = r'\b\w+ \d{1,2}, \d{4}\b'
        experience_pattern = r'^Total Experience: (.+)$'

        for data in fund_manager:
            if re.match(name_pattern,data):
                if current_entry:
                    strucuted_data[main_key].append(current_entry)
                current_entry = {
                    'name': data.split(",")[0].strip().lower(),
                    'designation': "".join(data.split(",")[1:]).strip().lower()
                }
                #print(data.split(",")[0],"".join(data.split(",")[1:]))
            elif re.match(manage_pattern,data):
                if "inception" in data.lower():
                    current_entry['managing_since'] = 'inception'
                else:
                    date = re.search(date_pattern, data)
                    current_entry['managing_since'] = date.group() if date != None else None
            elif re.match(experience_pattern,data):
                current_entry['total_experience'] = data.split(":")[1].strip().lower()
                #print(data.split(":")[1])

            
        if current_entry:  # Append the last entry
            strucuted_data[main_key].append(current_entry)
                
        return strucuted_data

    def __return_nav_data(self,key:str,data:list):
        main_key = key
        structured_data = {main_key: {}}
        
        growth_pattern = r"((?:Regular|Direct)\s+(?:Growth|IDCW))\s*:?\s*·\s*([\d.]+)"
        
        for line in data:
            matches = re.findall(growth_pattern, line)
            for key, value in matches:
                structured_data[main_key][key.strip().lower()] = float(value)
            
        return structured_data

    def __return_quant_data(self,key:str,data:list):
        qunatitative_data = data
        main_key = key

        strucuted_data = {main_key:{}}
        current_entry = None
        comment = ""

        ratio_pattern = r"\b(ratio|turnover)\b"
        annual_pattern = r'\b(annualised|YTM)\b'
        macaulay_pattern = r"\b(macaulay.*duration)\b"
        residual_pattern = r"\b(residual.*maturity)\b"
        modified_pattern = r"\b(modified.*duration)\b"

        for data in qunatitative_data:
            if re.search(ratio_pattern,data, re.IGNORECASE):
                key = data.split(":")[0].lower().strip()
                value = data.split(":")[1].lower().strip()
            elif re.search(annual_pattern,data, re.IGNORECASE):
                key = data.split(":")[0].lower().strip()
                value = data.split(":")[1].lower().strip()
            elif re.search(macaulay_pattern,data, re.IGNORECASE):
                key = data.split(":")[0].lower().strip()
                value = data.split(":")[1].lower().strip()
            elif re.search(residual_pattern,data, re.IGNORECASE):
                key = data.split(":")[0].lower().strip()
                value = data.split(":")[1].lower().strip()
            elif re.search(modified_pattern,data, re.IGNORECASE):
                key = data.split(":")[0].lower().strip()
                value = data.split(":")[1].lower().strip()
            else:
                comment+= data
            strucuted_data[main_key][key] = value
        
        strucuted_data[main_key]['comment'] = comment

        return strucuted_data

    def __return_aum_data(self,key:str,data:list):
        
        aum = data
        main_key = key
        strucuted_data = {main_key:{}}

        pattern = r"\b\d{1,3}(?:,\d{3})*(?:\.\d+)? Crs\b"

        for data in aum:
            if re.search(r'average', data, re.IGNORECASE):
                match = re.search(pattern, data)
                key = 'avg_aum (crs)'
            elif re.search(pattern, data):
                match = re.search(pattern, data)
                key = "aum (crs)"
            else:
                continue
            
            if match:
                strucuted_data[main_key][key] = float(match.group().split(" ")[0])

        return strucuted_data

    def __return_dummy_data(self,key:str,data:list):
        return {key:{}}


    #REGEX MAPPING FUNCTION
    def match_regex_to_content(self,string:str, data:list, *args):
        
        check_header = string
        
        if re.match(r"^Investment", check_header, re.IGNORECASE):
            return self.__return_invest_data(string,data)
        elif re.match(r"^Scheme", check_header, re.IGNORECASE):
            return self.__return_scheme_data(string, data)
        
        elif re.match(r"^NAV", check_header, re.IGNORECASE):
            return self.__return_nav_data(string, data)
        
        elif re.match(r"^Quant", check_header, re.IGNORECASE):
            return self.__return_quant_data(string, data)
        
        elif re.match(r"^Fund", check_header, re.IGNORECASE):
            return self.__return_fund_data(string, data)
        
        elif re.match(r"^Assets", check_header, re.IGNORECASE):
            return self.__return_aum_data(string, data)
        
        else:
            return self.__return_dummy_data(string,data)             
class Tata(Reader):
    
    PARAMS = {
        'fund': [[25,20,0,16],r"^(samco|tata).*(fund|etf|fof|eof|funds|plan|\))$",[10,20],[-1]], #[flag], regex_fund_name, range(font_size), [font_color]
        'clip_bbox': [(0,50,160,750)],
        'line_x': 160.0,
        'data': [[5,8],[-15570765],20.0,['Swiss721BT-BoldCondensed']] #sizes, color, set_size font_name
    }
    
    
    def __init__(self, path: str,dry:str,fin:str):
        super().__init__(path,dry,fin)
    
    def return_required_header(self,string: str):
            replace_key = string
            if re.match(r'^nav.*', string, re.IGNORECASE):
                replace_key = "nav"
            elif re.match(r"^market", string, re.IGNORECASE):
                replace_key = "market_capital"  
            elif re.match(r"^assets", string, re.IGNORECASE):
                replace_key = "assets_under_management"
            elif re.match(r"^fund", string, re.IGNORECASE):
                replace_key = "fund_manager" 
            elif re.match(r"^scheme", string, re.IGNORECASE):
                replace_key = "scheme_details" 
            elif re.match(r"^investment", string, re.IGNORECASE):
                replace_key = "investment_objective"
            elif re.match(r"^quanti", string, re.IGNORECASE):
                replace_key = "quantitative_data"
            elif re.match(r"^portfolio", string, re.IGNORECASE):
                replace_key = "portfilio" 
            elif re.match(r"^industry", string, re.IGNORECASE):
                replace_key = "industry_allocation_of_equity"       
            return replace_key
    
    
    #REGEX FUNCTIONS
    def __extract_inv_data(self,key:str, data:list):
        return
    
    def __extract_fund_data(self,key:str, data:list):
        return
    
    def __extract_nav_data(self,key:str, data:list):
        return
    
    def __extract_turn_data(self,key:str, data:list):
        return
    
    def __extract_bench_data(self,key:str, data:list):
        return
    
    def __extract_load_data(self,key:str, data:list):
        return
    
    def __extract_aum_data(self,key:str, data:list):
        return
    
    def __extract_trkerr_data(self,key:str, data:list):
        return
    
    def __extract_volat_data(self,key:str, data:list):
        return
    
    def __extract_dum_data(self,key,data:list):
        return


    def match_regex_to_content(self, string:str, data:list, *args):
        return 
    
class FranklinTempleton(Reader):
    
    PARAMS = {
        'fund': [[25,20],r"^(Franklin|Templeton).*$",[16,24],[-65794]], #[flag], regex_fund_name, range(font_size), [font_color]
        'clip_bbox': [(0,5,180,812)],
        'line_x': 180.0,
        'data': [[6,9],[-16751720],20.0,['ZurichBT-BoldCondensed']] #sizes, color, set_size font_name
    }
    
    def __init__(self, path: str,dry:str,fin:str):
        super().__init__(path,dry,fin)      

class GROWW(Reader):
    
    PARAMS = {
        'fund': [[25,20,21],r'.*(FUND|FOF|EOF|ETF)$',15.0,[-14475488]], #FUND NAME DETAILS order-> flag, regex_fund_name, font_size, font_color
        'clip_bbox': [(0,5,225,812)],
        'line_x': 225.0,
        'data': [[7,6,8],[-1],20.0,[""]] #sizes, color, set_size
    }
    
    def __init__(self, path: str,dry:str,fin:str):
        super().__init__(path,dry,fin)

class Bandhan(Reader):
    PARAMS = {
        'fund': [[20],r"^Bandhan.*(Fund|Funds|Plan|ETF)$", [13,24],[-1361884]], #FUND NAME DETAILS order-> flag, regex_fund_name, font_size, font_color
        'clip_bbox': [(0,5,225,812)],
        'line_x': 200.0,
        'data': [[6, 8], [-14475488], 20.0, ['Ubuntu-Bold']] #sizes, color, set_size font_name
    }
    
    
    def __init__(self, path: str,dry:str,fin:str):
        super().__init__(path,dry,fin)            
        
class Helios(Reader):
    
    PARAMS = {
        'fund': [[20], r'^Helios.*Fund$',[16,24],[-1]],
        'clip_box': [(0,5,250,812)],
        'line_x': 250.0,
        'data': [[7,10], [-1,-2545112], 30.0, ['Poppins-SemiBold']]
    }
    
    
    def __init__(self, path: str,dry:str,fin:str):
        super().__init__(path,dry,fin)   

class Edelweiss(Reader):
    
    PARAMS = {
        'fund': [[20], r'^(Edelweiss|Bharat)',[12,20],[-16298334]],
        'clip_box': [(0,5,410,812)],
        'line_x': 410.0,
        'data': [[5,9], [-16298334,-6204255], 20.0, ['Roboto-Bold']]
    }
    
    
    def __init__(self, path: str,dry:str,fin:str):
        super().__init__(path,dry,fin)
        
    
    def get_proper_fund_names(self,path:str,pages:list):
        
        doc = fitz.open(path)
        
        final_fund_names = dict()
        final_objectives = dict()
        
        for pgn in range(doc.page_count):
            fund_names = ''
            objective_names = ''
            
            if pgn in pages:
                page = doc[pgn]            
                blocks = page.get_text("dict")['blocks']
                for count,block in enumerate(blocks):
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            text = span['text'].strip()
                            if count in range(1,2):  #contains fund name        
                                fund_names += f'{text} '
                            
                            if count in range(4,5): #contains objectives
                                objective_names+= f'{text} '
                           
            final_fund_names[pgn] = fund_names
            final_objectives[pgn] = objective_names

        return final_fund_names, final_objectives
                                
class HSBC(Reader):
    
    PARAMS = {
        'fund': [[20,16], r'^(HSBC|Bharat).*Fund$',[12,20],[-1237724]],
        'clip_box': [(0,5,180,812)],
        'line_x': 180.0,
        'data': [[6,8], [-16777216], 30.0, ['Arial-BoldMT']]
    }
    
    
    def __init__(self, path: str,dry:str,fin:str):
        super().__init__(path,dry,fin)              
        
class Invesco(Reader):
    
    PARAMS = {
        'fund': [[20,16], r'^(Invesco|Bharat).*Fund$',[12,20],[-16777216]],
        'clip_box': [(0,135,185,812)],
        'line_x': 180.0,
        'data': [[7,9], [-16777216], 30.0, ['Graphik-Semibold']]
    }
    
    
    def __init__(self, path: str,dry:str,fin:str):
        super().__init__(path,dry,fin)   
               
class ITI(Reader):
    
    PARAMS = {
        'fund': [[20,16], r'^(ITI|Bharat).*Fund$',[14,24],[-1]],
        'clip_box': [(0,105,180,812)],
        'line_x': 180.0,
        'data': [[5,8], [-1688818,-1165277], 30.0, ['Calibri-Bold']]
    }
    
    
    def __init__(self, path: str,dry:str,fin:str):
        super().__init__(path,dry,fin)   

class JMMF(Reader):
    
    PARAMS = {
        'fund': [[20,16], r'^(JM|Bharat).*Fund$',[14,24],[-10987173]],
        'clip_box': [(390,105,596,812)],
        'line_x': 390.0,
        'data': [[6,9], [-1], 30.0, ['MyriadPro-BoldCond']]
    }
    
    
    def __init__(self, path: str,dry:str,fin:str):
        super().__init__(path,dry,fin)  

class DSP(Reader):
    
    PARAMS = {
        'fund': [[20,16], r'^(DSP|Bharat).*(Fund|ETF|FTF|FOF)$|^(DSP|Bharat)',[14,24],[-1]],
        'clip_box': [(0,5,120,812),[480,5,596,812]],
        'line_x': 120.0,
        'data': [[7,10], [-16777216], 30.0, ['TrebuchetMS-Bold']]
    }
    
    
    def __init__(self, path: str,dry:str,fin:str):
        super().__init__(path,dry,fin)
        
class BankOfIndia(Reader):
    
    PARAMS = {
        'fund': [[20,16], r'^(DSP|Bharat).*(Fund|ETF|FTF|FOF)$|^(DSP|Bharat)',[14,24],[-1]],
        'clip_box': [(0,5,120,812),[480,5,596,812]],
        'line_x': 120.0,
        'data': [[7,10], [-16777216], 30.0, ['TrebuchetMS-Bold']]}
    
    def __init__(self, path: str,dry:str,fin:str):
        super().__init__(path,dry,fin)
        
class Kotak(Reader):
    
    PARAMS = {
        'fund': [[20,16], r'^(Kotak|Bharat).*(Fund|ETF|FTF|FOF)$|^Kotak',[12,20],[-15319437]],
        'clip_box': [(0,5,150,812),],
        'line_x': 150.0,
        'data': [[5,8], [-15445130,-14590595], 30.0, ['Frutiger-Bold']]}
    
    def __init__(self, path: str,dry:str,fin:str):
        super().__init__(path,dry,fin)

class LIC(Reader):
    
    PARAMS = {
        'fund': [[20,16], r'^(LIC|Bharat).*(Fund|ETF|FTF|FOF)$',[12,20],[-15319437]],
        'clip_box': [(0,5,150,812),],
        'line_x': 150.0,
        'data': [[5,8], [-15445130,-14590595], 30.0, ['Frutiger-Bold']]}
    
    def __init__(self, path: str,dry:str,fin:str):
        super().__init__(path,dry,fin)            

class MahindraManu(Reader):
    PARAMS = {
        'fund': [[20,16], r'',[12,20],[-15319437]],
        'clip_box': [(0,65,200,812)],
        'line_x': 200.0,
        'data': [[7,10], [-7392877,-16749906,-7953091,-7767504,-12402502,-945627,], 30.0, ['QuantumRise-Bold','QuantumRise','QuantumRise-Semibold']]}
    
    def __init__(self, path: str,dry:str,fin:str):
        super().__init__(path,dry,fin)
        
    def get_proper_fund_names(self,path:str,pages:list):
        
        doc = fitz.open(path)
        final_fund_names = dict()
        
        for pgn in range(doc.page_count):
            fund_names = ''
            if pgn in pages:
                page = doc[pgn]            
                blocks = page.get_text("dict")['blocks']
                
                sorted_blocks = sorted(blocks,key=lambda k:(k['bbox'][1],k['bbox'][0]))
                for count,block in enumerate(sorted_blocks):
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            text = span['text'].strip()
                            if count in range(0,2): #contains fund name        
                                fund_names += f'{text} '
            if matches:= re.search(r'\bMahindra.*?(Fund|ETF|EOF|FOF|FTF|Path)\b', fund_names, re.IGNORECASE):           
                final_fund_names[pgn] = matches.group()
            else:
                final_fund_names[pgn] = ''

        return final_fund_names

class MotilalOswal(Reader):
    PARAMS = {
        'fund': [[20,16], r'^(Motilal|Oswal).*(Fund|ETF|EOF|FOF|FTF|Path)$',[20,28],[-13616547]],
        'clip_box': [(0,65,170,812)],
        'line_x': 170.0,
        'data': [[7,12], [-13948375], 30.0, ['Calibri-Bold']]}
    
    def __init__(self, path: str,dry:str,fin:str):
        super().__init__(path,dry,fin)       

class NJMF(Reader):
    PARAMS = {
        'fund': [[20,16,0], r'^(NJ).*(Fund|ETF|EOF|FOF|FTF|Path)$',[16,24],[-13604430]],
        'clip_box': [(0,5,250,812)],
        'line_x': 250.0,
        'data': [[6,11], [-14475488], 30.0, ['Swiss721BT-Medium']]}
    
    def __init__(self, path: str,dry:str,fin:str):
        super().__init__(path,dry,fin)
        
class QuantMF(Reader):
    PARAMS = {
        'fund': [[16,0], r'^(quant).*(Fund|ETF|EOF|FOF|FTF|Path)$',[16,24],[-13604430]],
        'clip_box': [(0,5,180,812)],
        'line_x': 180.0,
        'data': [[6,11], [-16777216], 30.0, ['Calibri,Bold',]]}
    
    def __init__(self, path: str,dry:str,fin:str):
        super().__init__(path,dry,fin) 

class Sundaram(Reader):
    PARAMS = {
        'fund': [[4,0], r'^(Sundaram).*(Fund|ETF|EOF|FOF|FTF|Path|Fund*|Fund -)$|^Sundaram',[14,18],[-16625248]],
        'clip_box': [(0,5,220,812)],
        'line_x': 220.0,
        'data': [[6,13], [-1], 30.0, ['UniversNextforMORNW02-Cn',]]}
    
    def __init__(self, path: str,dry:str,fin:str):
        super().__init__(path,dry,fin) 

class Taurus(Reader):
    PARAMS = {
        'fund': [[4,20], r'^(Taurus).*(Fund|ETF|EOF|FOF|FTF|Path|Fund*)$',[16,24],[-9754846]],
        'clip_box': [(0,65,210,812)],
        'line_x': 210.0,
        'data': [[6,12], [-9754846], 30.0, ['Calibri-Bold']]}
    
    def __init__(self, path: str,dry:str,fin:str):
        super().__init__(path,dry,fin) 

class Trust(Reader):
    
    PARAMS = {
        'fund': [[4,20], r'^(Trust).*(Fund|ETF|EOF|FOF|FTF|Path|Fund*)$',[16,22],[-1]],
        'clip_box': [(0,65,180,812)],
        'line_x': 180.0,
        'data': [[7,12], [-1, -14475488], 30.0, ['Roboto-Bold']]}
    
    def __init__(self, path: str,dry:str,fin:str):
        super().__init__(path,dry,fin)  

class UTI(Reader):
    PARAMS = {
        'fund': [[20], r'^(UTI).*(Fund|ETF|EOF|FOF|FTF|Path|Fund\*|Plan\*|Duration)$',[14,24],[-65794]],
        'clip_box': [(0,65,200,812)],
        'line_x': 200.0,
        'data': [[7,10], [-65794,-1], 30.0, ['Calibri-Bold']]}
    
    def __init__(self, path: str,dry:str,fin:str):
        super().__init__(path,dry,fin)  


class WhiteOak(Reader):
    PARAMS = {
        'fund': [[20], r'^(whiteOak).*(Fund|ETF|EOF|FOF|FTF|Path|Fund\*|Plan\*|Duration)$',[16,24],[-13159371]],
        'clip_box': [(0, 85, 240, 812)],
        'line_x': 240.0,
        'data': [[7,11], [-65794,-1], 30.0, ['MyriadPro-Bold']]}
    
    def __init__(self, path: str,dry:str,fin:str):
        super().__init__(path,dry,fin)  


class BarodaBNP(Reader):
    PARAMS = {
        'fund': [[20], r'^(whiteOak).*(Fund|ETF|EOF|FOF|FTF|Path|Fund\*|Plan\*|Duration)$',[16,24],[-13159371]],
        'clip_box': [(0, 85, 240, 812)],
        'line_x': 240.0,
        'data': [[7,11], [-65794,-1], 30.0, ['MyriadPro-Bold']]}
    
    def __init__(self, path: str,dry:str,fin:str):
        super().__init__(path,dry,fin)   
    
#something