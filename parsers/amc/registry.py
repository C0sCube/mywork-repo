# parsers/amc/registry.py
from importlib import import_module

CLASS_MAP = {
    "18_0": "parsers.amc.fund_data.ThreeSixtyOne",
    "12_0": "parsers.amc.fund_data.HDFC",
    # etc...
}

def get_amc_class(amc_id):
    path = CLASS_MAP.get(amc_id)
    if not path:
        raise ValueError(f"No registered class for {amc_id}")
    module_name, class_name = path.rsplit(".", 1)
    module = import_module(module_name)
    return getattr(module, class_name)
