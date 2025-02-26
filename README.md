# **MyWork-Repo**  

## **1. Overview**  

This project processes financial PDFs by extracting relevant data using regex patterns, highlighting detected text, generate a report for data present, clean, refine and store data in strucuted manner.

### **Key Features:**  

- Extracts structured data from PDFs  
- Highlights relevant keywords  
- Saves count of imp data into an Excel report
- Clean the parsed data and use regex functions to get imp data
- Perform CRUD operations on imp data for further database storage
- `regex.json`,`params.json5`,`paths.json` are important configs

### File Structure

```.
    ├── app/
    ├── data/
    │   ├── config/
    │   ├── input/
    │   └── output/
    ├── notebook/
    ├── .gitignore
    ├── README.md
    ├── logging_config.py
    ├── main.py
    ├── paths.json
    └── req.txt
```

## **2. Project Workflow**  

1. **Start Here:** Open `main.ipynb` (entry point).  
2. Load a PDF and extract text.  
3. Highlight key financial terms and fund-related information.  
4. Save processed results into an Excel report.  

## **3. Installation & Setup**  

```bash
git clone https://github.com/C0sCube/mywork-repo.git  
cd mywork-repo  
pip install -r requirements.txt  
```

## **4. Things to Remember**  

- `params.json5` stores fund house configurations.  
- Unique detection indices are stored but all matches are highlighted.  
- The `_save_pdf_data()` function logs extracted info into an Excel file.  

## **5. Code Progression**  

- **[Date]**: Removed pandas dependency from `check_and_highlight()`.  
- **[Date]**: Improved `update_fund_house()` to use `dict.update()`.  
- **[Date]**: Added error handling for missing keys in JSON.
