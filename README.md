MyWork-Repo
Overview
This project processes financial PDFs by extracting, refining, and structuring data for analysis and storage.

Key Features:
✅ Extracts structured data from PDFs
✅ Highlights key financial terms
✅ Generates an Excel report with important data
✅ Cleans and refines extracted text using regex
✅ Supports CRUD operations for database storage

Project Workflow
1️⃣ Start Here: Open main.ipynb (entry point).
2️⃣ Load Fund House: Call the respective fund house class from fundData.py.
3️⃣ Extract PDF Data: Load a PDF and extract text.
4️⃣ Highlight Key Terms: Use check_and_highlight to mark important financial data.
5️⃣ Generate Reports: Save results in an Excel report and create a new highlighted PDF.
6️⃣ Identify Relevant Pages & Titles: Extract fund details from reports.
7️⃣ Extract Required Data:

Use get_data_via_clip or get_data_via_line.
Retrieve text using get_generated_content.
8️⃣ Refine Data:
Use refine_extracted_data (and refine_secondary_data if needed).
9️⃣ Store & Process: Save data or perform CRUD operations.
🔟 Log Everything & Stay Happy! 🎉
Installation & Setup
bash
Copy
Edit
git clone https://github.com/C0sCube/mywork-repo.git  
cd mywork-repo  
pip install -r requirements.txt  
Important Notes
🔹 File Structure: Ensure all required files exist before running the program.
🔹 Fund Data (fundData.py):

Contains GrandFundData (main class) and subclasses for each AMC (e.g., "Tata Mutual Fund" → Tata).
Call subclass objects in main.ipynb.
🔹 Configuration Files:
params.json5 → Fund house settings, processed via structData.py.
regex.json → Regex patterns (header_patterns, stop_words), managed by fundRegex.py.
paths.json → Stores all necessary paths.
