import threading
from datetime import datetime, timezone
import traceback
import os

from app.konstant import get_log_dir
from app.logger import setup_logger, log_exceptions, set_global_logger
from app.mailer import Mailer
from app.utils import Helper

from app.amfi_nav import AmfiNavAggregator


PROG_NAME = "AMFI NAV Aggregator"


@log_exceptions(level="error")
def fetch_runner():
    logger.info(f"[FETCH] STARTED @ {datetime.now():%H:%M:%S}")
   
    try:
        filepath = aggregator.run_fetch()

        logger.info(f"[FETCH] COMPLETED: {os.path.basename(filepath)}")

    except Exception as e:
        logger.exception("[FETCH] FAILED")
        raise


@log_exceptions(level="error")
def aggregate_runner():
    logger.info("[AGGREGATE] STARTED")

    now = datetime.now()
    agg_time = now.strftime("%H%M")

    lookback_hours = agg_data.get(agg_time)

    if lookback_hours is None:
        logger.warning(f"No aggregation config for {agg_time}")
        return

    logger.info(
        f"Aggregation window: last {lookback_hours} hours"
    )

    aggregator.run_aggregate(
        run_time=now,
        lookback_hours=lookback_hours,
    )

    logger.info("[AGGREGATE] COMPLETED")



if __name__ == "__main__":

    log_dir = get_log_dir()
    logger = setup_logger(
        "amfi_log",
        log_dir=log_dir,
    )

    set
    helper = Helper()
    aggregator = AmfiNavAggregator()

    logger.info("=" * 72)
    logger.info("STARTING AMFI NAV PARALLEL SCHEDULER SYSTEM")
    days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

    # Fetch NAVs every few hours
    fetch_times =[
        # "0000","0100","0200","0300","0400","0500",
        # "0600","0700","0800","0900","1000","1100",
        # "1200","1300","1400","1500","1600","1700",
        # "1800","1900","2000","2100","2200","2300"
        "1533", "1535", "1538",
    ]

    # Aggregate once (non-overlapping)
    agg_data = {
        "1537":2,
    }
    
    agg_times = [ i for i in agg_data]

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