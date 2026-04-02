
import os, csv, requests
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta, timezone
from typing import List, Dict

from app.konstant import get_raw_dir
from app.logger import get_global_logger, log_exceptions

AMFI_URL = "https://portal.amfiindia.com/spages/NAVAll.txt"


class AmfiNavAggregator:
    def __init__(self, ):
        self.data_dir = get_raw_dir()
        self.logger = get_global_logger()

        os.makedirs(self.data_dir, exist_ok=True)

    # Job 1: Fetcher
    def run_fetch(self) -> str:
        """
        Fetch AMFI NAV data and save as timestamped CSV
        """
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


    # Job 2: Aggregator + Mailer
    def run_aggregate(self, run_time: datetime, lookback_hours: int)->str:
        """
        Aggregate NAV CSV files from:
        [run_time - lookback_hours, run_time)
        """
        window_start = run_time - timedelta(hours=lookback_hours)

        self.logger.info(
            f"Aggregating files from {window_start} → {run_time}"
        )

        selected_files = []

        for file in os.listdir(self.data_dir):
            if not file.startswith("amfi_nav_") or not file.endswith(".csv"):
                continue

            file_ts = self._parse_filename_ts(file)
            full_path = os.path.join(self.data_dir, file)

            if window_start <= file_ts < run_time:
                selected_files.append(full_path)

        if not selected_files:
            self.logger.warning("No NAV files found in window")
            return

        self.logger.info(f"Selected files: {selected_files}")

        seen = set()
        aggregated_rows: List[Dict] = []

        for file in selected_files:
            for row in self._read_rows(file):
                key = (row["Scheme Code"], row["Date"])
                if key not in seen:
                    seen.add(key)
                    aggregated_rows.append(row)

        output_ts = run_time.strftime("%Y%m%d_%H%M")
        output_file = os.path.join(
            self.data_dir, f"amfi_aggregated_{output_ts}.csv"
        )

        self._write_rows(output_file, aggregated_rows)


        return output_file

    # Internal Helpers

    def _parse_filename_ts(self, filename: str) -> datetime:
        """
        Extract timestamp from filename: amfi_nav_YYYYMMDD_HHMM.csv
        """
        ts_part = filename.replace("amfi_nav_", "").replace(".csv", "")
        return datetime.strptime(ts_part, "%Y%m%d_%H%M").replace(
            tzinfo=timezone.utc
        )

    def _read_rows(self, filepath: str):
        with open(filepath, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                yield row

    def _write_rows(self, filepath: str, rows: List[Dict]):
        if not rows:
            return

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

    def _now(self) -> datetime:
        """
        Centralized clock (easy to mock/test)
        """
        return datetime.now(ZoneInfo("Asia/Kolkata"))

    