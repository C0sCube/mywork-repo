import threading
from datetime import datetime
import traceback
import os

from app.konstant import get_log_dir
from app.logger import setup_logger, log_exceptions, set_global_logger
from app.utils import Helper
from app.mailer import Mailer
from app.amfi_nav import AmfiNavAggregator
import zipfile

def create_zip_bundle(output_file, selected_files):

    base_dir = os.path.dirname(output_file)
    zip_name = os.path.basename(output_file).replace(".csv", ".zip")
    zip_path = os.path.join(base_dir, zip_name)

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:

        # Add aggregated file
        zipf.write(output_file, os.path.basename(output_file))

        # Add source files
        for f in selected_files:
            zipf.write(f, os.path.basename(f))

    return zip_path

PROG_NAME = "AMFI NAV Aggregator"


@log_exceptions(level="error")
def fetch_runner():
    logger.info(f"[FETCH] STARTED @ {datetime.now():%H:%M:%S}")

    try:
        filepath = aggregator.run_fetch()
        logger.info(f"[FETCH] COMPLETED: {os.path.basename(filepath)}")

    except Exception:
        logger.exception("[FETCH] FAILED")
        raise


@log_exceptions(level="error")
def aggregate_runner():
    logger.info("[AGGREGATE] STARTED")

    now = datetime.now()
    agg_time = now.strftime("%H%M")

    lookback_count = agg_data.get(agg_time)

    if lookback_count is None:
        logger.warning(f"No aggregation config for {agg_time}")
        return

    logger.info(f"Aggregation using last {lookback_count} files")

    try:
        result = aggregator.run_aggregate(
            run_time=now,
            lookback_count=lookback_count,
        )

        if not result:
            return

        output_file, selected_files = result

        logger.info(f"[AGGREGATE] OUTPUT: {os.path.basename(output_file)}")

        
        zip_path = create_zip_bundle(output_file, selected_files)
        
        if mailer.SEND_MAIL:
            
            mailer.send(
                subject=PROG_NAME,
                template="SUCCESS",
                attachments=zip_path
            )

        logger.info(f"[AGGREGATE] ZIP CREATED: {os.path.basename(zip_path)}")

    except Exception:
        logger.exception("[AGGREGATE] FAILED")
        raise


if __name__ == "__main__":

    # Setup logger
    log_dir = get_log_dir()
    logger = setup_logger("amfi_log", log_dir=log_dir)
    set_global_logger(logger)
    logger.info("=" * 72)
    logger.info("STARTING AMFI NAV PARALLEL SCHEDULER SYSTEM")
    mail_config = {
        "send_mail": True,
        "sender": "newsrssfetch.fornse@cogencis.com",
        "dev_recipients": [
            "Kaustubh.Keny@cogencis.com"
        ],
        "recipients": [
            "Kaustubh.Keny@cogencis.com"
        ],
        "cc": [],
        "bcc": [],
        "server": "172.17.0.126",
        "port": 25
    }
    

    # Run all days for testing
    days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

    # ---------------- FETCH SCHEDULE ---------------- #
    # Keep short intervals for testing
    fetch_times = [
        "2241", "2243", "2245", "2247","2249","2251"
    ]
    # fetch_times = [f"{(16 + i) % 24:02d}00" for i in range(24)]

    # ---------------- AGGREGATION CONFIG ---------------- #
    # key = time, value = last N files
    agg_data = {
        "2252": 2,   # last 4 files
    }
    agg_times = list(agg_data.keys())
    
    
    
    helper = Helper()
    aggregator = AmfiNavAggregator()  
    mailer = Mailer(mail_config)

    # ---------------- THREADS ---------------- #
    fetch_scheduler = threading.Thread(
        target=helper.scheduler_loop,
        args=(logger, fetch_runner, days, fetch_times),
        daemon=False,
        name="AMFI-FETCH-SCHEDULER",
    )

    agg_scheduler = threading.Thread(
        target=helper.scheduler_loop,
        args=(logger, aggregate_runner, days, agg_times),
        daemon=False,
        name="AMFI-AGG-SCHEDULER",
    )

    fetch_scheduler.start()
    agg_scheduler.start()

    try:
        fetch_scheduler.join()
        agg_scheduler.join()

    except KeyboardInterrupt:
        logger.info("Shutdown signal received. Exiting gracefully...")