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

def load_sidkim_registry():
    from app.logger import get_global_logger
    logger = get_global_logger()
    
    reg = get_registry()
    registry_list = reg.get("sid_class_registry",{})
    
    module = importlib.import_module("app.sid.fund_data")
    registry = {}
    for code, class_name in registry_list.items():
        cls = getattr(module, class_name, None)
        if not cls:
            logger.warning(f"{class_name} not found. Defaulting to BaseAMC.")
            cls = BaseAMC
        registry[code] = cls
        
    return registry



def check_amc_file(path: str, file_name: str) -> tuple[str | None, str | None, str | None]:
    logger = get_global_logger()

    fs_pattern = re.compile(
        r"^(?P<code>\d{1,3})_(?P<date>\d{2}-[A-Za-z]{3}-\d{2})(?:_(?P<rev>\d))?_FS\.pdf$"
    )

    sidkim_pattern = re.compile(
        r"^(?P<code>\d{1,3})_.*?_(?P<type>SID|KIM)\.pdf$"
    )

    # ---------- FACTSHEET ----------
    m = fs_pattern.match(file_name)
    if m:
        try:
            code = m.group("code")
            dateval = m.group("date")
            rev = m.group("rev")

            date_obj = datetime.strptime(dateval, "%d-%b-%y")

            final_code = f"{code}_{1 if rev else 0}"
            year = str(date_obj.year)

            logger.debug(f"Detected FS PDF: {file_name}")
            return final_code, year, "FS"

        except Exception as e:
            logger.warning(f"FS parse failed for {file_name}: {e}")
            return None, None, None

    # ---------- SID / KIM ----------
    m = sidkim_pattern.match(file_name)
    if m:
        code = m.group("code")
        sid_or_kim = m.group("type")  # "SID" | "KIM"

        logger.debug(f"Detected {sid_or_kim} PDF: {file_name}")
        return code, sid_or_kim, "SIDKIM"

    # ---------- INVALID ----------
    logger.warning(f"Invalid or unsupported PDF: {file_name}")
    try:
        os.remove(path)
    except Exception:
        pass

    return None, None, None

# CLASS_REGISTRY = load_registry()

# def check_amc_file(path: str, file_name: str) -> tuple[str | None, str | None]:
#     logger = get_global_logger()
#     fs_pattern = r"(\d{1,3}_\d{2}-[A-Za-z]{3}-\d{2}(?:_\d{1})?)_FS\.pdf"
#     sid_pattern = r"^(\d{1,3})_.*_\d{6}+_(SID|KIM)\.pdf"

#     final_code, dt_year,types = None, None, None

#     if file_name.endswith("_FS.pdf"):
#         match = re.match(fs_pattern, file_name)
#         if match:
#             logger.debug(f"Detected Pdf File Named {file_name}")
#             code, dateval, *rest = match.group(1).split("_")
#             date_obj = datetime.strptime(dateval, "%d-%b-%y")
            
#             types = "FS"
#             dt_year = str(date_obj.year)
#             final_code = f"{code}_{1 if rest else 0}"
#         else:
#             logger.warning(f"Invalid File or File Type {file_name}")
    
#     elif file_name.endswith("_SID.pdf") or file_name.endswith("_KIM.pdf"):        
#         if match:
#             logger.debug(f"Detected Pdf File Named {file_name}")
#             match = re.findall(sid_pattern, file_name)
#             code, sid_o_kim = match[0]
            
#             types = "SIDKIM"
#             dt_year = sid_o_kim
#             final_code = code
        
#         else:
#             logger.warning(f"Invalid File or File Type {file_name}")
#     else:
#         logger.info("Not a PDF!! Deleting file.")
#         logger.debug(path)
#         os.remove(path)

#     return final_code, dt_year, types

    
    # elif file_name.endswith(".xlsx") and file_name == "table_data.xlsx":
    #     logger.info("Detected Excel File Named 'table_data.xlsx'")
    #     return True
        
    # else file_name.endswith(".json"):
    #     logger.info("You have attatched json here !!!")
    #     pass        
    
    