# Workflow Overview

## 1. Entry Point

System continuously watches input folder.

Flow:

* Pick PDF
* Identify type (FS / SID / KIM)
* Route to correct parser

---

## 2. Main Flow (FS)

```text
execute_fs()
→ check_and_highlight()
→ get_data()
→ get_generated_content()
→ refine_extracted_data()
→ merge_and_select_data()
→ save JSON
```

---

## 3. Step Breakdown

### check_and_highlight

* Detects valid pages
* Uses:

  * title regex
  * financial keywords
* Output:
  `{page: fund_name}`

---

### get_data

* Extracts raw PDF blocks
* Methods:

  * clip (bbox)
  * line (left/right split)

Then:

* span extraction
* cleaning
* grouping into headers

---

### get_generated_content

* Rebuilds text from blocks
* Converts to structured text per fund
* Adds important metadata

---

### refine_extracted_data

3-stage refinement:

```text
primary → secondary → tertiary
```

Each stage:

```text
header → pattern match → extract function → structured dict
```

---

### merge_and_select_data

Final shaping:

```text
clone → merge → select → map → format
```

---

## 4. Mental Model

```text
PDF
→ Blocks
→ Clean Text
→ Headers
→ Pattern Match
→ Extract
→ Refine
→ Merge
→ Format
→ JSON
```

---

## 5. Debug Flow

If something breaks:

1. Check title detection
2. Check extracted blocks
3. Check header mapping
4. Check pattern match
5. Check merge/select logic

---

## 6. Key Classes

* Reader → extraction
* GrandFundData → regex + logic
* FundRegex → cleaning + formatting
* Config → controls behavior
