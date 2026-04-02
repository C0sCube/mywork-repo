import os, csv, requests
from zoneinfo import ZoneInfo
from datetime import datetime, timezone
import pandas as pd

from app.konstant import get_raw_dir, get_output_dir
from app.logger import get_global_logger


AMFI_URL = "https://portal.amfiindia.com/spages/NAVAll.txt"


class AmfiNavAggregator:

    def __init__(self):
        self.data_dir = get_raw_dir()
        self.output_dir = get_output_dir()
        self.logger = get_global_logger()

        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

    # ---------------- FETCH ---------------- #
    def run_fetch(self) -> str:
        now = self._now()
        ts = now.strftime("%Y%m%d_%H%M")

        filename = f"amfi_nav_{ts}.csv"
        filepath = os.path.join(self.data_dir, filename)

        self.logger.info("Fetching AMFI NAV data")

        response = requests.get(AMFI_URL, timeout=30, verify=False)
        response.raise_for_status()

        lines = response.text.splitlines()

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            writer.writerow([
                "Scheme Code",
                "ISIN Growth / Div Payout",
                "ISIN Div Reinvestment",
                "Scheme Name",
                "Net Asset Value",
                "Date",
            ])

            for line in lines:
                if line.strip() and line[0].isdigit():
                    parts = line.split(";")
                    if len(parts) == 6:
                        writer.writerow(parts)

        self.logger.info(f"Saved NAV CSV: {filename}")
        return filepath

    # ---------------- AGGREGATE ---------------- #
    def run_aggregate(self, run_time: datetime, lookback_count: int) -> str:

        self.logger.info(f"Aggregation using last {lookback_count} files")

        files = self._get_all_nav_files()

        if len(files) < lookback_count:
            self.logger.warning(
                f"Not enough files. Found={len(files)}, Required={lookback_count}"
            )
            return

        selected_files = [p for _, p in files[-lookback_count:]]

        self.logger.info("Selected files:")
        for f in selected_files:
            self.logger.info(f" - {os.path.basename(f)}")

        # -------- pandas aggregation -------- #
        try:
            dfs = [pd.read_csv(f) for f in selected_files]
            df = pd.concat(dfs, ignore_index=True)

            before = len(df)
            df = df.drop_duplicates(keep="first")
            after = len(df)

            self.logger.info(f"Rows before: {before}, after: {after}")

        except Exception as e:
            self.logger.warning(f"Aggregation failed: {e}")
            return

        if df.empty:
            self.logger.warning("Empty dataframe after aggregation")
            return

        output_ts = run_time.strftime("%Y%m%d_%H%M")
        output_file = os.path.join(
            self.output_dir, f"amfi_aggregated_{output_ts}.csv"
        )

        df.to_csv(output_file, index=False)

        self.logger.info(f"Aggregation complete: {output_file}")

        return output_file, selected_files

    # ---------------- HELPERS ---------------- #
    def _get_all_nav_files(self):
        files = []

        for file in os.listdir(self.data_dir):
            if file.startswith("amfi_nav_") and file.endswith(".csv"):
                try:
                    ts = self._parse_filename_ts(file)
                    full_path = os.path.join(self.data_dir, file)
                    files.append((ts, full_path))
                except Exception:
                    self.logger.warning(f"Skipping invalid file: {file}")

        files.sort(key=lambda x: x[0])  # ascending
        return files

    def _parse_filename_ts(self, filename: str) -> datetime:
        ts_part = filename.replace("amfi_nav_", "").replace(".csv", "")
        return datetime.strptime(ts_part, "%Y%m%d_%H%M").replace(
            tzinfo=timezone.utc
        )

    def _now(self) -> datetime:
        return datetime.now(ZoneInfo("Asia/Kolkata"))