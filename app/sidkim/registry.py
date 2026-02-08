from app.sidkim.fund_data import BaseSIDKIM
from app.konstant import get_registry
import importlib

def load_sidkim_registry():
    from app.logger import get_global_logger
    logger = get_global_logger()
    
    reg = get_registry()
    registry_list = reg.get("amc_registry",{})
    
    module = importlib.import_module("app.sidkim.fund_data")
    registry = {}
    for code, amc_data in registry_list.items():
        class_name = amc_data["sid_class"]
        cls = getattr(module, class_name, None)
        if not cls:
            logger.warning(f"{class_name} not found. Defaulting to BaseAMC.")
            cls = BaseSIDKIM
        registry[str(code)] = cls
        
    return registry