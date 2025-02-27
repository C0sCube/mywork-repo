# **MyWork-Repo**  

## **1. Overview**  

This project automates the extraction, processing, and storage of financial data from PDFs. It identifies key patterns, highlights important text, generates structured reports, and refines extracted content for further use.  

### **Key Features:**  

- **Extracts** structured data from PDFs using regex.  
- **Highlights** key financial terms for better visibility.  
- **Generates Reports** with important data counts in Excel.  
- **Cleans & Refines** extracted text for accuracy.  
- **Performs CRUD Operations** for efficient database storage.  


## **2. Project Workflow**  

1. **Start Here:** Open `main.ipynb` (entry point).  
2. **Initialize:** Call the relevant Fund House object from `fundData.py`.  
3. **Extract Data:** Load a PDF and extract all text.  
4. **Highlight Keywords:** Use `check_and_highlight` to mark key financial terms.  
5. **Generate Reports:** Save results into an Excel report and create a highlighted PDF.  
6. **Identify Sections:** Retrieve page **titles** and **page numbers** from the report.  
7. **Extract Content:**  
   - Use `get_data_via_clip` or `get_data_via_line` for structured extraction.  
   - Call `get_generated_content` to process PDF data.  
8. **Refine Data:** Apply `refine_extracted_data` and `refine_secondary_data` to clean important content.  
9. **Store & Manage:** Perform **CRUD** operations on extracted data.  
10. **Log Everything:** Ensure logs are properly maintained.  

## **3. Installation & Setup**  

```bash
git clone https://github.com/C0sCube/mywork-repo.git  
cd mywork-repo  
pip install -r requirements.txt  
```

## **4. Things to Remember**  

**File Structure** should match the expected format for smooth execution.  

**Key Files & Their Roles:**  
- `fundData.py` → Contains `GrandFundData` (main class) and fund-specific subclasses (e.g., `"Tata"` for "Tata Mutual Fund").  
- `main.ipynb` → Entry point; call fund house objects here.  
- `params.json5` → Stores fund house configurations (handled by `structData.py`).  
- `regex.json` → Contains `header_patterns` & `stop_words` (used in `fundRegex.py`).  
- `paths.json` → Defines all paths; both `paths.json` and `configs` must be present before running the program.  
- `pdfParse.py` → Handles text extraction, highlighting, and PDF processing.  
- `logging_config.py` & `utils.py` → Manage logging and utility functions.  

**Config Structure (`params.json5`) Example:**  
```json
{
    "FUND_NAME": {
        "PARAMS": {
            "fund": [[FLAG(S)], "REGEX_PATTERN", [SIZE_MIN, SIZE_MAX], [COLOR(S)]],
            "clip_bbox": [[X0, Y0, X1, Y1]],
            "line_x": FLOAT,
            "data": [[FONT_SIZE_MIN, FONT_SIZE_MAX], [COLOR(S)], SET_HEAD_SIZE, [FONT_NAME]],
            "content_size": [HEAD_SIZE, NORMAL_TEXT_SIZE],
            "amc_check_count": INT,
            "check_max_highlights": INT
        },
        "REGEX": { "key": "regex" },
        "PATTERN_TO_FUNCTION": { "sub_head_regex": ["function_name", "key"] },
        "SECONDARY_PATTERN_TO_FUNCTION": { "sub_head_regex": ["function_name", "key"] },
        "SELECTKEYS": [],
        "MERGEKEYS": {}
    }
}
