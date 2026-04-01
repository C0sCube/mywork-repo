import os, re, time, inspect, ocrmypdf
import fitz # type: ignore
from collections import defaultdict
import pandas as pd
from pathlib import Path


from app.insur.parse_regex import *
from app.insur.fund_data import *
from app.utils import Helper
from app.logger import get_global_logger, log_exceptions
from app.konstant import (
    get_output_path, get_report_dir,
    get_json_dir
)

class ReaderInsurance:
    
    
    def __init__(self,path:str,params:dict):
        
        self.log = get_global_logger()
        self.PARAMS = params
        self.UTILS = Helper()
        
        #paths & name
        self.FILE_NAME = Path(path).name
        self.OUTPUT_PATH = get_output_path()
        self.PDF_PATH = path
        self.DRYPATH = os.path.join("app","temp","dry.pdf")
        self.REPORT_PATH = get_report_dir()
        self.JSON_PATH = get_json_dir()
        pass
    
    #HIGHLIGHT
    @log_exceptions()
    def _get_normal_title(self, path: str, title_regex: str, bbox):
        func = inspect.currentframe().f_code.co_name
        self.log.info(f"▶ Start {func} | file={path}")
        # print(f"▶ Start {func} | file={path}")

        title_detected,escape_regex = {},self.PARAM_REGEX.ESCAPE

        with fitz.open(path) as doc:
            for pgn, page in enumerate(doc):
                try:
                    if path.endswith("_ocr.pdf"):
                        title_text = " ".join(page.get_text("text").split("\n"))
                    else:
                        title_text = " ".join(page.get_text("text", clip=bbox).split("\n"))
                    title_text = re.sub(escape_regex, "", title_text).strip()
                    title_match = re.findall(title_regex, title_text, re.DOTALL)
                    title = (
                        " ".join([_ for _ in title_match[0].strip().split(" ") if _])
                        if title_match else ""
                    )

                    if title:self.log.info(f"Page {pgn} → Title Found: {title}")
                    else:self.log.debug(f"Page {pgn} → No title detected in '{title_text[:50]}...'")
                    title_detected[pgn] = title

                except Exception as e:
                    self.log.warning(f"Partial read failed on page {pgn}: {e}")
                    continue
        self.log.debug(f"📄 {func} complete | {len(title_detected)} pages scanned")
        
        # if path.endswith("FS_ocr.pdf"): 
        #     os.remove(path)
        return title_detected

    @log_exceptions()
    def _get_ocr_title(self, path: str, title_regex: str, bbox):
        func = inspect.currentframe().f_code.co_name
        self.log.info(f"▶ {func} | OCR processing for {self.FILE_NAME}")

        clipped_pdf = path.replace(".pdf", "_clipped.pdf")
        ocr_pdf = path.replace(".pdf", "_ocr.pdf")

        with fitz.open(path) as doc, fitz.open() as new_doc:
            for page_num in range(len(doc)):
                new_page = new_doc.new_page(width=bbox[2] - bbox[0], height=bbox[3] - bbox[1])
                new_page.show_pdf_page(new_page.rect, doc, page_num, clip=bbox)
            new_doc.save(clipped_pdf)

        try:
            # run OCR externally
            time.sleep(1)
            ocrmypdf.ocr(clipped_pdf, ocr_pdf, deskew=True, force_ocr=True)
        except PermissionError as e:
            self.log.warning(f"[Permission Denied] while writing: {ocr_pdf} | {e}")
            return {}
        except Exception:
            raise  # let decorator log unexpected issues
        
        # os.remove(clipped_pdf)
        self.log.debug(f"OCR complete — passing to _get_normal_title()")
        print(ocr_pdf)
        return self._get_normal_title(ocr_pdf, title_regex, bbox)

    @log_exceptions()  
    def _ocr_pdf(self,path:str):
        func = inspect.currentframe().f_code.co_name
        self.log.info(f"▶ {func} | Performing full-page OCR on {self.FILE_NAME}")
        ocr_path = path.replace(".pdf", "_all_ocr.pdf")
        time.sleep(2)
        ocrmypdf.ocr(path, ocr_path, deskew=True, force_ocr=True)
        return ocr_path
    # def _ocr_pdf(self, path: str):
    #     func = inspect.currentframe().f_code.co_name
    #     self.log.info(f"▶ {func} | Performing full-page OCR on {self.FILE_NAME}")

    #     ocr_path = path.replace(".pdf", "_all_ocr.pdf")
    #     self.safe_ocr(path, ocr_path, timeout=90)
    #     self.log.debug(f"OCR completed successfully: {ocr_path}")
    #     return ocr_path

    @log_exceptions()
    def check_and_highlight(self, path, save_htld_pdf=False, save_report=False):
        func = inspect.currentframe().f_code.co_name
        self.log.info(f"▶ Start {func} | file={self.FILE_NAME}")

        data,output_path = [],path.replace(".pdf", "_hltd.pdf")
        title_regex, bbox, ocr = self.PARAMS["title"]['pattern'], self.PARAMS["title"]['bbox'], self.PARAMS["title"]["ocr"]
        financial_terms = self.PARAM_REGEX.FINANCIAL_TERMS

        detected_titles = (
            self._get_ocr_title(path, title_regex, bbox)
            if ocr
            else self._get_normal_title(path, title_regex, bbox)
        )
        path_pdf = self._ocr_pdf(path) if self.PARAMS['pdf_ocr'] else path
        
        with fitz.open(path_pdf) as doc:
            for pgn, page in enumerate(doc):
                highlight_count, found_indices = 0, []
                for block in page.get_text("dict")["blocks"]:
                    if "lines" not in block:
                        continue
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text = self.UTILS._remove_non_word_space_chars(span["text"])
                            for indice in financial_terms:
                                if re.search(rf"\b{re.escape(indice)}\b", text, re.IGNORECASE):
                                    if indice not in found_indices:
                                        found_indices.append(indice)
                                        highlight_count += 1
                                    page.add_highlight_annot(fitz.Rect(span["bbox"]))
                                    break
                
                # self.log.info("|".join(found_indices))
                
                data.append({
                    "page": pgn,
                    "title": detected_titles.get(pgn, ""),
                    "highlight_count": highlight_count,
                    "indices": found_indices
                })

            if save_htld_pdf:
                doc.save(output_path)

        df_report = pd.DataFrame(data)
        self.log.debug(
            "\n📄 Highlight Report — %s\n%s\n%s",
            self.FILE_NAME,
            df_report.to_string(index=False, justify="center"),
            "-" * 80,
        )

        if save_report:
            ReaderInsurance.__pdf_report(data, self.REPORTPATH, self.FILE_NAME)

        self.log.info(f"{func} done | total_pages={len(data)}, highlights={sum(d['highlight_count'] for d in data)}")
        return {
            d["page"]: d["title"]
            for d in data
            if d["title"] and d["highlight_count"] >= self.PARAMS["max_financial_index_highlight"]
        }, path_pdf

    @staticmethod
    def __pdf_report(data, path: str, sheet_name:str):

        excel_path = os.path.join(path, f"{sheet_name.replace(".pdf","")}_REPORT.xlsx")
        df = pd.DataFrame(data)

        if 'indices' in df.columns:
            try:
                df_exp = df["indices"].apply(lambda x: pd.Series(x) if isinstance(x, list) else pd.Series())
                df_exp.columns = [f"idx_{i+1}" for i in range(df_exp.shape[1])]
                df_exp = df_exp.dropna(axis=1, how='all')
                df_final = pd.concat([df.drop(columns=["indices"]), df_exp], axis=1)
            except Exception as e:
                print(f"[ERROR] Expanding indices failed: {e}")
                df_final = df
        else:
            df_final = df

        # if os.path.exists(excel_path):
        #     with pd.ExcelWriter(excel_path, engine="openpyxl", mode='a', if_sheet_exists='replace') as writer:
        #         df_final.to_excel(writer, sheet_name=sheet_name, index=False)
        # else:
        #     with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        #         df_final.to_excel(writer, sheet_name=sheet_name, index=False)
        with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
            df_final.to_excel(writer, sheet_name=sheet_name, index=False)

        return df_final