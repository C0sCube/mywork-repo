# parsers/base_parser.py
from abc import ABC, abstractmethod
from core.logger import get_logger, trace_exception

class BaseParser(ABC):
    def __init__(self, amc_id, params, pdf_path):
        self.amc_id = amc_id
        self.params = params
        self.pdf_path = pdf_path
        self.logger = get_logger(f"Parser[{amc_id}]")

    @abstractmethod
    def check_and_highlight(self):
        """Finds titles or sections in PDF."""
        pass

    @abstractmethod
    def extract_data(self):
        """Extracts structured data from the PDF."""
        pass

    @abstractmethod
    def refine_data(self, data):
        """Refines extracted data into standardized JSON."""
        pass

    def run_pipeline(self):
        try:
            title_map, processed_pdf = self.check_and_highlight()
            data = self.extract_data(title_map, processed_pdf)
            refined = self.refine_data(data)
            return refined
        except Exception:
            trace_exception(self.logger, "Pipeline failed")
            return {}
