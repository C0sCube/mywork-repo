# **MyWork-Repo**  

## **1. Overview**  

This project processes financial PDFs by extracting relevant data using regex patterns, highlighting detected text, generate a report for data present, clean, refine and store data in strucuted manner.

### **Key Features:**  

- Extracts structured data from PDFs  
- Highlights relevant keywords  
- Saves count of imp data into an Excel report
- Clean the parsed data and use regex functions to get imp data
- Perform CRUD operations on imp data for further database storage

### File Structure

```.
    ├── app/
    ├── data/
    │   ├── config/
    │   ├── input/
    │   └── output/
    ├── venv/
    ├── logs/
    ├── notebook/
    ├── .gitignore
    ├── README.md
    ├── logging_config.py
    ├── main.py
    ├── paths.json
    └── requirements.txt
```

## **2. Project Workflow**  

1. **Start Here:** Open `main.ipynb` (entry point).
2. CALL the object of Fund House in file `fundData.py`.
3. LOAD a pdf and extract all text.  
4. HIGHLIGHT key financial terms and fund-related information via `check_and_highlight`.  
5. SAVE processed results into an Excel report and make new pdf of highlighted data.
6. Get page TITLE, PAGES from the report required to parse data.
7. Get data either via `get_data_via_clip` or `get_data_via_line`
8. Use `get_generated_content` to get pdf data.
9. Use `refine_extracted_data` and if required `refine_secondary_data` to refine all the IMP data.
10. STORE or perform CRUD on data, use utils if required.
11. Be Happy !! Make sure to LOG !!

## **3. Installation & Setup**  

```bash
git clone https://github.com/C0sCube/mywork-repo.git  
cd mywork-repo  
pip install -r requirements.txt  
```

## **4. Things to Remember**

- Ensure the file structure is similar to what is shown.
- `fundData.py` has a main class `GrandFundData` and subclasses named similarly to the AMCs (e.g., "Tata Mutual Fund" as "Tata").
- Call the object of those subclasses in `main.ipynb`.
- `params.json5` stores fund house configurations handled by `structData.py`.
- `regex.json` stores `header_patterns` and `stop_words` handled by `fundRegex.py`.
- `paths.json` stores all paths; `paths` and `configs` files MUST BE PRESENT before running the main program.
- `pdfParse.py` contains the code to check, highlight, and extract data from PDFs.
- `logging_config.py` and `utils.py` are used for logging and helper functions, respectively.
- `params.json5` has the following structure:

    ```json
            {
                "FUND_NAME1": {
                    "PARAMS": {
                        "fund": [
                            [FLAG(S)], //int
                            "REGEX_PATTERN", //str
                            [SIZE_MIN, SIZE_MAX], //int
                            [COLOR(S)] //unsigned_int
                        ],
                        "clip_bbox": [
                            [X0, Y0, X1, Y1] //float
                        ],
                        "line_x": FLOAT,
                        "data": [
                            [FONT_SIZE_MIN, FONT_SIZE_MAX], //int
                            [COLOR(S)], //unsigned_int
                            SET_HEAD_SIZE, //float
                            [FONT_NAME] //str
                        ],
                        "content_size": [HEAD_SIZE, NORMAL_TEXT_SIZE], //float
                        "amc_check_xount": INT,
                        "check_max_highlights": INT
                    },
                    "REGEX": {
                        "key" :"regex", 
                    },
                    "PATTERN_TO_FUNCTION": {
                        "sub_head_regex": [
                            "function_name",
                            "key"
                        ],
                    },
                    "SECONDARY_PATTERN_TO_FUNCTION": {
                        "sub_head_regex": [
                            "function_name",
                            "key"
                        ],
                    },
                    "SELECTKEYS": [],
                    "MERGEKEYS": {}
                },

                "FUND_NAME2" :{..}
            }
    ```
