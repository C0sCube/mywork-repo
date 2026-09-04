import json, csv, ast
from pathlib import Path
from datetime import datetime
from pandas import pd
from numpy import np


from app.konstant import get_registry

class ConverterFunctions:
    
    def __init__(self):
      
        self.registry = get_registry()
    
    @staticmethod
    def _read_sections(csv_path):
        sections, cur = [], []
        with open(csv_path, "r", encoding="utf-8") as f:
            for row in csv.reader(f):
                if not any(cell.strip() for cell in row):
                    if cur:
                        sections.append(cur)
                        cur = []
                else:
                    cur.append(row)
        if cur:
            sections.append(cur)
        return sections


    def csv_to_sid_json(self,csv_path):
        sections = ConverterFunctions._read_sections(csv_path)
        value = {}
        if sections:
            header, *rows = sections[0]
            ki, vi = header.index("key"), header.index("value")
            for r in rows:
                k, v = r[ki].strip(), r[vi].strip()
                if k == "field_location" and v:
                    try:
                        v = ast.literal_eval(v)
                    except Exception:
                        pass
                value[k] = v
        for idx, key in ((1, "fund_manager"), (2, "load")):
            if len(sections) > idx:
                header, *rows = sections[idx]
                value[key] = [
                    {
                        h: r[i].strip() if i < len(r) else ""
                        for i, h in enumerate(header)
                        if h
                    }
                    for r in rows
                ]
        return {
            "metadata": {
                "document_name": Path(csv_path).name,
                "file_type": "sid",
                "process_date": datetime.today().strftime("%Y%m%d"),
            },
            "value": dict(sorted(value.items())),
        }


    def kim_to_csv(self,json_path, output_folder):
        json_path, output_folder = Path(json_path), Path(output_folder)
        output_folder.mkdir(parents=True, exist_ok=True)
        doc = json.loads(json_path.read_text(encoding="utf-8"))
        record = doc.get("records", [{}])[0].get("value", {}) or {}
        csv_path = output_folder / f"{json_path.stem}.csv"

        def write_df(fh, df):
            df.to_csv(fh, index=False)
            fh.write("\n\n")

        with open(csv_path, "w", encoding="utf-8", newline="") as fh:
            keys = [
                "amc_name",
                "main_scheme_name",
                "mutual_fund_name",
                "description",
                "field_location",
            ]
            write_df(
                fh,
                pd.DataFrame([{"key": k, "value": str(record.get(k, ""))} for k in keys]),
            )
            rows = []
            for item in record.get("asset_allocation_pattern", []):
                row = {
                    "instrument_type": item.get("instrument_type", ""),
                    "risk_profile": item.get("risk_profile", ""),
                    "min": "",
                    "max": "",
                    "total": "",
                }
                for a in item.get("allocation", []):
                    row[a.get("type")] = a.get("value", "")
                rows.append(row)
            if rows:
                write_df(fh, pd.DataFrame(rows))
        return str(csv_path)


    def csv_to_kim_json(self,csv_path):
        sections = ConverterFunctions._read_sections(csv_path)
        value = {}
        if sections:
            header, *rows = sections[0]
            ki, vi = header.index("key"), header.index("value")
            for r in rows:
                k, v = r[ki].strip(), r[vi].strip()
                if k == "field_location" and v:
                    try:
                        v = ast.literal_eval(v)
                    except Exception:
                        v = []
                value[k] = v
        if len(sections) > 1:
            header, *rows = sections[1]
            value["asset_allocation_pattern"] = [
                {
                    "instrument_type": (
                        r[header.index("instrument_type")]
                        if "instrument_type" in header
                        else ""
                    ),
                    "risk_profile": (
                        r[header.index("risk_profile")] if "risk_profile" in header else ""
                    ),
                    "allocation": [
                        {
                            "type": k,
                            "value": (
                                r[header.index(k)]
                                if k in header and header.index(k) < len(r)
                                else ""
                            ),
                        }
                        for k in ("min", "max", "total")
                    ],
                }
                for r in rows
            ]
        return {
            "metadata": {
                "document_name": Path(csv_path).name,
                "file_type": "kim",
                "process_date": datetime.today().strftime("%Y%m%d"),
            },
            "records": [{"value": dict(sorted(value.items()))}],
        }


    def json_to_csv(self,json_path, output_folder):
        json_path, output_folder = Path(json_path), Path(output_folder)
        output_folder.mkdir(parents=True, exist_ok=True)
        keys = self.registry.get("field_keys",{})
        static_keys, load_keys, metric_keys, manager_keys, field_location = (
            keys["static_keys"],
            keys["load_keys"],
            keys["metric_keys"],
            keys["manager_keys"],
            keys["field_location"],
        )
        records = json.loads(json_path.read_text(encoding="utf-8")).get("records", [])
        max_mgr = max((len(r["value"].get("fund_manager", [])) for r in records), default=1)
        headers = (
            static_keys
            + load_keys
            + metric_keys
            + [f"{k}_{i}" for i in range(1, max_mgr + 1) for k in manager_keys]
            + [field_location]
        )
        rows = []
        for r in records:
            v = r["value"]
            row = [v.get(k, "") for k in static_keys]
            entry = exit_ = ""
            for l in v.get("load", []):
                if l["type"] == "entry":
                    entry = l["comment"]
                elif l["type"] == "exit":
                    exit_ = l["comment"]
            row += [entry, exit_]
            metric_map = {m["name"]: m["value"] for m in v.get("metrics", [])}
            row += [metric_map.get(k, "") for k in metric_keys]
            mgrs = v.get("fund_manager", [])
            for i in range(max_mgr):
                row += (
                    [mgrs[i].get(k, "") for k in manager_keys]
                    if i < len(mgrs)
                    else [""] * len(manager_keys)
                )
            fl = v.get("field_location", [])
            row.append(json.dumps(fl[0]) if fl else "")
            rows.append(row)
        csv_path = output_folder / f"{json_path.stem}.csv"
        pd.DataFrame(rows, columns=headers).to_csv(csv_path, index=False)
        return str(csv_path)


    def csv_to_fs_json(self,csv_path):
        df = pd.read_csv(
            csv_path, dtype=str, encoding="utf-8", encoding_errors="replace"
        ).fillna("")
        keys = self.registry.get("field_keys",{})
        records = []
        for _, row in df.iterrows():
            value = {k: row[k] for k in keys["static_keys"] if k in row and row[k]}
            loads = (
                [{"type": "entry", "comment": row["entry"]}] if row.get("entry") else []
            ) + ([{"type": "exit", "comment": row["exit"]}] if row.get("exit") else [])
            if loads:
                value["load"] = loads
            metrics = [
                {"name": k, "value": row[k]} for k in keys["metric_keys"] if row.get(k)
            ]
            if metrics:
                value["metrics"] = metrics
            managers = []
            i = 1
            while f"name_{i}" in df.columns:
                fm = {
                    k: row[f"{k}_{i}"] for k in keys["manager_keys"] if row.get(f"{k}_{i}")
                }
                if fm:
                    managers.append(fm)
                i += 1
            if managers:
                value["fund_manager"] = managers
            if row.get(keys["field_location"]):
                try:
                    value["field_location"] = [json.loads(row[keys["field_location"]])]
                except Exception:
                    pass
            records.append({"value": dict(sorted(value.items()))})
        return {
            "metadata": {
                "document_name": Path(csv_path).with_suffix(".pdf").name,
                "file_type": "fs",
                "process_date": datetime.now().strftime("%Y%m%d"),
            },
            "records": records,
        }


    def if_to_csv(self,json_path, output_folder):
        json_path, output_folder = Path(json_path), Path(output_folder)
        output_folder.mkdir(parents=True, exist_ok=True)
        keys = self.registry.get("field_keys",{}).get("if_keys",{})
        headers = keys["static_keys"] + keys["portfolio_keys"]
        rows = []
        records = json.loads(json_path.read_text(encoding="utf-8")).get("records", [])
        for r in records:
            v = r.get("value", {})
            static_values = [v.get(k, "") for k in keys["static_keys"]]
            portfolio_list = v.get("portfolio_data", [])
            if not isinstance(portfolio_list, list):
                continue
            rows.extend(
                [
                    static_values + [item.get(k, "") for k in keys["portfolio_keys"]]
                    for item in portfolio_list
                ]
            )
            rows += [[""] * len(headers), [""] * len(headers)]
        csv_path = output_folder / f"{json_path.stem}.csv"
        pd.DataFrame(rows, columns=headers).to_csv(csv_path, index=False)
        return str(csv_path)

    def sid_to_csv(self,json_path, output_folder):
        json_path, output_folder = Path(json_path), Path(output_folder)
        output_folder.mkdir(parents=True, exist_ok=True)
        record = json.loads(json_path.read_text(encoding="utf-8")).get("value", {}) or {}
        csv_path = output_folder / f"{json_path.stem}.csv"

        def write_df(fh, df):
            df.to_csv(fh, index=False)
            fh.write("\n\n")

        with open(csv_path, "w", encoding="utf-8", newline="") as fh:
            kv = []
            for k in sorted(record.keys()):
                if k not in ("fund_manager", "load", "field_location"):
                    v = record.get(k)
                    v = " ".join(map(str, v)) if isinstance(v, (dict, list)) else v
                    kv.append({"key": k, "value": v or ""})
                if k == "field_location":
                    kv.append({"key": k, "value": str(record.get(k))})
            write_df(fh, pd.DataFrame(kv))
            if record.get("fund_manager"):
                write_df(fh, pd.DataFrame(record["fund_manager"]))
            if record.get("load"):
                write_df(fh, pd.DataFrame(record["load"]))
        return str(csv_path)


