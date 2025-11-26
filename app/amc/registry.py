from app.amc.fund_data import *
import re
from datetime import datetime

CLASS_REGISTRY = {
    "18_0": ThreeSixtyOne,
    "2_0": BarodaBNP,
    "5_0": BankOfIndia,
    "51_0": ITI,
    "55_0": Trust,
    "56_0": NAVI, #ocr
    "56_1": NAVIPassive, #ocr
    "10_0": QuantMF,
    "11_0": FranklinTempleton,
    "26_0": MahindraManu,
    "20_0": GROWW,
    "21_0": Invesco,
    "22_0": JMMF,
    "57_0": NJMF,
    "58_0": Samco,
    "30_0": PPFAS,
    "32_0": Quantum,
    "95_0": OldBridge,
    "96_0": AngelOne,
    "97_0": Unifi,
    "39_0": Taurus,
    "40_0": Union,
    "36_0": Shriram,
    "37_0": Sundaram,
    "25_0": LIC, #ocr
    "42_0": WhiteOak,
    "1_1": AXISMFPassive,
    "71_0": Zerodha, #ocr
    "6_0": Canara,
    "60_0": Helios,
    "7_0": PGIM,
    "98_0":JioBlackRock,
     
    # add pages
    "59_0": BajajFinServ,
    "8_0": DSP,
    "12_0": HDFC,
    "12_1": HDFC,
    
    # manual annot
    "1_0": AXISMF,
    
    # long amcs
    "27_0": MIRAE,
    "3_0": AdityaBirla,
    "27_1": MIRAEPassive,
    "28_0": MotilalOswal,
    "13_0": HSBC,
    "28_1": MotilalOswalPassive,
    "14_0": ICICI,
    "9_0": Edelweiss,
    "14_1": ICICIPassive,
    "16_0": Bandhan,
    "33_0": Nippon, #ocr
    "41_0": UTI,
    "23_0": Kotak,
    "41_1": UTIPassive,
    "35_0": SBI,
    "38_0": Tata,
    "35_1": SBIPassive, #ocr
    "99_0": CapitalMind,
    "100_0": WealthCompany,
}


def check_amc_file(file_name:str)->bool:
    
    from app.logger import get_global_logger
    logger = get_global_logger()
    
    get_name = "(\\d{1,3}_\\d{2}-[A-Za-z]{3}-\\d{2}(?:_\\d{1})?)_FS.pdf"
    
    if file_name.endswith("_FS.pdf"):
        if matches:= re.findall(get_name, file_name):
            logger.debug(f"Detected Pdf File Named {file_name}")
            code,dateval,*rest = matches[0].split("_")
            date_obj = datetime.strptime(dateval, "%d-%b-%y")
            final_code = f"{code}_0"
            if rest:
                final_code =  f"{code}_1"
                
            return final_code, str(date_obj.year)
        logger.warning(f"Invalid File or File Type {file_name}")
        return None, None

    if file_name.endswith(".xlsx") and file_name == "table_data.xlsx":
        logger.info("Detected Excel File Named 'table_data.xlsx'")
        return True

    if file_name.endswith(".json"):
        pass        