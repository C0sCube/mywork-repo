from app.amc.fund_data import *
import re, importlib
from datetime import datetime
from app.konstant import get_registry



def load_registry():
    from app.logger import get_global_logger
    logger = get_global_logger()
    
    reg = get_registry()
    registry_list = reg.get("class_registry",{})
    
    module = importlib.import_module("app.amc.fund_data")
    registry = {}
    for code, class_name in registry_list.items():
        cls = getattr(module, class_name, None)
        if not cls:
            logger.warning(f"{class_name} not found. Defaulting to BaseAMC.")
            cls = BaseAMC
        registry[code] = cls
        
    return registry

# CLASS_REGISTRY = load_registry()

def check_amc_file(path: str, file_name: str) -> tuple[str | None, str | None]:
    logger = get_global_logger()
    pattern = r"(\d{1,3}_\d{2}-[A-Za-z]{3}-\d{2}(?:_\d{1})?)_FS\.pdf"

    final_code, dt_year = None, None

    if file_name.endswith("_FS.pdf"):
        match = re.match(pattern, file_name)
        if match:
            logger.debug(f"Detected Pdf File Named {file_name}")
            code, dateval, *rest = match.group(1).split("_")
            date_obj = datetime.strptime(dateval, "%d-%b-%y")
            dt_year = str(date_obj.year)
            final_code = f"{code}_{1 if rest else 0}"
        else:
            logger.warning(f"Invalid File or File Type {file_name}")
    else:
        logger.info("Not a PDF!! Deleting file.")
        logger.debug(path)
        os.remove(path)

    return final_code, dt_year

    
    # elif file_name.endswith(".xlsx") and file_name == "table_data.xlsx":
    #     logger.info("Detected Excel File Named 'table_data.xlsx'")
    #     return True
        
    # else file_name.endswith(".json"):
    #     logger.info("You have attatched json here !!!")
    #     pass        
    
    

# CLASS_REGISTRY = {
#     "18_0": ThreeSixtyOne,
#     "2_0": BarodaBNP,
#     "5_0": BankOfIndia,
#     "51_0": ITI,
#     "55_0": Trust,
#     "56_0": NAVI, #ocr
#     "56_1": NAVIPassive, #ocr
#     "10_0": QuantMF,
#     "11_0": FranklinTempleton,
#     "26_0": MahindraManu,
#     "20_0": GROWW,
#     "21_0": Invesco,
#     "22_0": JMMF,
#     "57_0": NJMF,
#     "58_0": Samco,
#     "30_0": PPFAS,
#     "32_0": Quantum,
#     "95_0": OldBridge,
#     "96_0": AngelOne,
#     "97_0": Unifi,
#     "39_0": Taurus,
#     "40_0": Union,
#     "36_0": Shriram,
#     "37_0": Sundaram,
#     "25_0": LIC, #ocr
#     "42_0": WhiteOak,
#     "1_1": AXISMFPassive,
#     "71_0": Zerodha, #ocr
#     "6_0": Canara,
#     "60_0": Helios,
#     "7_0": PGIM,
#     "98_0":JioBlackRock,
     
#     # add pages
#     "59_0": BajajFinServ,
#     "8_0": DSP,
#     "12_0": HDFC,
#     "12_1": HDFC,
    
#     # manual annot
#     "1_0": AXISMF,
    
#     # long amcs
#     "27_0": MIRAE,
#     "3_0": AdityaBirla,
#     "27_1": MIRAEPassive,
#     "28_0": MotilalOswal,
#     "13_0": HSBC,
#     "28_1": MotilalOswalPassive,
#     "14_0": ICICI,
#     "9_0": Edelweiss,
#     "14_1": ICICIPassive,
#     "16_0": Bandhan,
#     "33_0": Nippon, #ocr
#     "41_0": UTI,
#     "23_0": Kotak,
#     "41_1": UTIPassive,
#     "35_0": SBI,
#     "38_0": Tata,
#     "35_1": SBIPassive, #ocr
#     "99_0": CapitalMind,
#     "100_0": WealthCompany,
# }
