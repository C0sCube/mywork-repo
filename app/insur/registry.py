from app.amc.fund_data import *
import re, importlib, os
from datetime import datetime
from app.konstant import get_registry
from app.logger import get_global_logger


def load_ifregistry():
    
    logger = get_global_logger()
    reg = get_registry()
    registry_list = reg.get("amc_registry",{})
    
    module = importlib.import_module("app.insur.fund_data")
    registry = {}
    for code, amc_data in registry_list.items():
        
        class_data = amc_data["fs_class"]
        for k,class_name in class_data.items():
            cls = getattr(module, class_name, None)
            if not cls:
                # logger.warning(f"{class_name} not found. Defaulting to BaseAMC.")
                cls = BaseAMC
            registry[f"{code}_{k}"] = cls
        
    return registry

# def check_insur_file(path: str, file_name: str) -> tuple[str | None, str | None, str | None]:
#     logger = get_global_logger()

#     fs_pattern = re.compile(r"^(?P<code>\d{1,3})_(?P<date>\d{2}-[A-Za-z]{3}-\d{2})(?:_(?P<rev>\d))?_IF\.pdf$")
#     # sidkim_pattern = re.compile(r"^(?P<code>\d{1,3})_.*?_(?P<type>SID|KIM)\.pdf$")

#     # ---------- FACTSHEET ----------
#     m = fs_pattern.match(file_name)
#     if m:
#         try:
#             code = m.group("code")
#             dateval = m.group("date")
#             rev = m.group("rev")

#             date_obj = datetime.strptime(dateval, "%d-%b-%y")

#             final_code = f"{code}_{1 if rev else 0}"
#             year = str(date_obj.year)

#             logger.debug(f"Detected INSUR PDF: {file_name}")
#             return final_code, year, "IF"

#         except Exception as e:
#             logger.warning(f"INSUR parse failed for {file_name}: {e}")
#             return None, None, None

#     # ---------- SID / KIM ----------
#     # m = sidkim_pattern.match(file_name)
#     # if m:
#     #     code = m.group("code")
#     #     sid_or_kim = m.group("type")  # "SID" | "KIM"

#     #     logger.debug(f"Detected {sid_or_kim} PDF: {file_name}")
#     #     return code, sid_or_kim, "SIDKIM"

#     # ---------- INVALID ----------
#     logger.warning(f"Invalid or unsupported PDF: {file_name}")
#     try:
#         os.remove(path)
#     except Exception:
#         pass

#     return None, None, None

