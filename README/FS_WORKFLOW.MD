# Factsheet Parsing

## 1. Core Idea

Factsheet parsing is:

* semi-structured
* regex driven
* config controlled

---

## 2. Extraction Layer

Handled in `Reader`

### Methods

#### extract_clipped_data

* Uses bounding boxes
* Best for structured layouts

#### extract_data_relative_line

* Splits page by vertical line
* Useful for 2-column layouts

---

#### extract_span_data

* Converts PDF spans → structured rows
* Removes duplicates

---

#### process_text_data

* Removes stop words
* Normalizes font sizes
* Groups text logically

---

#### create_nested_dict

Example:

```json
{
  "investment_objective": [...],
  "riskometer": [...]
}
```

---

## 3. Pattern Matching

```text
PATTERN_TO_FUNCTION = {
  "regex": ("function_name", "regex_key")
}
```

---

### Dynamic Execution

```text
_match_with_patterns()
→ finds matching regex
→ calls function dynamically
```

---

## 4. Extraction Functions

### Basic

* _extract_str_data → join text

---

### Regex Based

* _extract_generic_data
* _extract_findall_select_first_data

---

### Section Based

* _extract_scheme_data
* _extract_scheme_non_esc_data

---

### Metrics

* _extract_metric_data
* _extract_offset_data
* _extract_iter_data

---

### Special Fields

* _extract_load_data
* _extract_amt_data
* _extract_manager_data
* _extract_benchmark_data
* _extract_date_data

---

## 5. Update Functions

* _update_manager_data
* _update_benchmark_data
* _update_date_data

---

## 6. Merge & Select

```text
clone → merge → select → promote → map
```

---

## 7. Formatting (FundRegex)

* normalize keys
* clean fund names
* format metrics
* format manager
* convert date
* populate defaults

---

## 8. Output Format

```json
{
  "metadata": {},
  "records": [
    { "value": {} }
  ]
}
```

---

## 9. Common Issues

### Missing Data

* header not mapped
* regex not matching

### Wrong Data

* wrong extract function
* bad regex

### Broken Structure

* MERGEKEYS issue
* SELECTKEYS issue

---

## 10. Tips

* Log header → function mapping
* Test regex separately
* Start with generic extractor
