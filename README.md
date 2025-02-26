# **MyWork-Repo**  

## **1. Overview**  

This project processes financial PDFs by extracting relevant data using regex patterns, highlighting detected text, and storing structured data in an Excel file.  

### **Key Features:**  

- Extracts structured data from PDFs  
- Highlights relevant keywords  
- Saves processed data into an Excel report  
- CRUD operations on `params.json5` for fund house configurations  

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
