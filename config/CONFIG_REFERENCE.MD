# CONFIG_REFERENCE

## Extraction Function Reference

| Function Name                        | Parameters       | Called In                  | Description                                  |
| ------------------------------------ | ---------------- | -------------------------- | -------------------------------------------- |
| `_extract_str_data`                  | data only        | primary/secondary/tertiary | Joins list into single string                |
| `_extract_generic_data`              | data + regex_key | primary/secondary/tertiary | Generic regex extractor (value or key-value) |
| `_extract_findall_select_first_data` | data + regex_key | primary/secondary/tertiary | Returns first regex match                    |
| `_extract_scheme_data`               | data + regex_key | primary                    | Extracts sections between keywords           |
| `_extract_scheme_non_esc_data`       | data + regex_key | primary                    | Same as above, without escape cleanup        |
| `_extract_metric_data`               | data + regex_key | primary/secondary          | Extracts metric key-value pairs              |
| `_extract_offset_data`               | data + regex_key | primary/secondary          | Fixes misaligned values (tables)             |
| `_extract_iter_data`                 | data + regex_key | primary/secondary          | Matches key-value by position                |
| `_extract_load_data`                 | data + regex_key | primary                    | Extracts entry/exit load                     |
| `_extract_amt_data`                  | data + regex_key | primary                    | Extracts amount + thereafter                 |
| `_extract_manager_data`              | data + regex_key | primary                    | Extracts fund manager details                |
| `_extract_lump_data`                 | data + regex_key | primary                    | Extracts min/add investment (alt format)     |
| `_extract_bench_data`                | data + regex_key | primary                    | Extracts benchmark                           |
| `_extract_benchmark_data`            | data + regex_key | secondary                  | Cleans benchmark using header + content      |
| `_extract_date_data`                 | data + regex_key | primary/secondary          | Extracts scheme launch date                  |
| `_extract_non_esc_data`              | data + regex_key | primary                    | Extracts without escape cleanup              |

---

## 🔄 Update Function Reference

| Function Name            | Parameters | Called In                  | Description                 |
| ------------------------ | ---------- | -------------------------- | --------------------------- |
| `_update_manager_data`   | data only  | secondary/tertiary/special | Aligns name, exp, since     |
| `_update_benchmark_data` | data only  | secondary                  | Cleans benchmark string     |
| `_update_date_data`      | data only  | secondary                  | Normalizes date             |
| `_update_bench_sub_data` | data only  | secondary                  | Removes unwanted substrings |

---

## 📌 Regex Definition Notes

All `regex_key` values come from:

```text
REGEX = {
  "manager": {...},
  "metrics": {...},
  "date": "...",
  "benchmark": "...",
  "escape": "..."
}
```

---

### 🔁 How it connects

```text
Header → PATTERN_TO_FUNCTION → function_name + regex_key
→ function executes using REGEX[regex_key]
```

---

## ⚠️ Important Rules

* If function expects `regex_key`, it MUST exist in REGEX
* If not needed → pass `null` or omit
* Function name must exactly match method name
* Prefer `_extract_generic_data` before custom functions

---

## 🧠 Quick Debug Guide

| Problem            | Check                           |
| ------------------ | ------------------------------- |
| No value extracted | regex_key missing or wrong      |
| Wrong mapping      | wrong function used             |
| Partial data       | switch to iter/offset extractor |
| Broken structure   | issue in SELECTKEYS / MERGEKEYS |
