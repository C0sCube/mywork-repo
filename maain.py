import threading
from datetime import datetime, timedelta
import os
import traceback

from app.constants import get_log_dir
from app.logger import setup_logger,log_exceptions
from app.news import AdverseNewsDetetor
from app.utils import Helper
from app.mailer import Mailer


PROG_NAME = "Adverse News Aggregator (GOOGLE/BING)"



def delete_old_files(folder_path, days=5):
    cutoff = datetime.now() - timedelta(days=days)

    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)

        if not os.path.isfile(file_path):
            continue

        modified_time = datetime.fromtimestamp(os.path.getmtime(file_path))

        if modified_time < cutoff:
            os.remove(file_path)
            print(f"Deleted: {filename}")


@log_exceptions(level="error")
def fetch_runner():

    logger.info(f"[FETCH] STARTED @ {datetime.now():%H:%M:%S}")

    mailer = Mailer()

    try:

        handler = AdverseNewsDetetor()
        handler.rss_handler(mode="single",ts="3h")

        logger.info("[FETCH] COMPLETED")

    except Exception as e:

        logger.exception("[FETCH] FAILED")

        mailer.send(
            subject=f"[FAILED] {PROG_NAME} FETCH",
            template="ERROR",
            program=PROG_NAME,
            error_message=str(e),
            traceback=traceback.format_exc()
        )

        raise


@log_exceptions(level="error")
def aggregate_runner():

    logger.info(f"[AGGREGATE] STARTED @ {datetime.now():%H:%M:%S}")

    mailer = Mailer()

    try:

        handler = AdverseNewsDetetor()

        output_dir = handler.program_24h_handler()

        if not output_dir:
            raise RuntimeError("Aggregation returned None")

        logger.info("Zipping output directory...")

        timestamp = datetime.now().strftime("%Y%m%d")

        zip_path = os.path.abspath(
            os.path.join(output_dir,"..",f"ADVERSE_NEWS_{timestamp}.zip")
        )

        helper.zip_folder(output_dir,zip_path)

        mailer.send(
            subject=f"[COMPLETED] {PROG_NAME}",
            template="SUCCESS",
            program=PROG_NAME,
            attachments=zip_path,
            dev=False
        )

        logger.info("Pipeline completed successfully.")

        try:
            # os.rmdir(output_dir)
            os.remove(zip_path)
            logger.info("ZIP FILE DELETED POST MAILING.")
            
            raw_dir = handler.OUTPUT_RAW_DIR
            
            delete_old_files(raw_dir, days= 4)
            logger.info("DELETED FILES OLDER THAN 4 DAYS IN RAW FOLDER")
            
        except Exception as e:
            logger.exception(f"ERROR IN DELETION: {e}")

    except Exception as e:

        logger.exception("[AGGREGATE] FAILED")

        mailer.send(
            subject=f"[FAILED] {PROG_NAME}",
            template="ERROR",
            program=PROG_NAME,
            error_message=str(e),
            traceback=traceback.format_exc()
        )

        raise


if __name__ == "__main__":

    log_dir = get_log_dir()
    logger = setup_logger("adv_log",log_dir=log_dir,use_color=True,make_global=True)
    helper = Helper()

    logger.info("="*60)
    logger.info("STARTING PARALLEL SCHEDULER SYSTEM")

    days = ["mon","tue","wed","thu","fri","sat","sun"]
    fetch_times = ["0030","0330","0630","0930","1230","1530","1830","2130"]
    agg_times   = ["1100"]

    fetch_scheduler = threading.Thread(
        target=helper.scheduler_loop,
        args=(logger,fetch_runner,days,fetch_times),
        daemon=False
    )

    agg_scheduler = threading.Thread(
        target=helper.scheduler_loop,
        args=(logger,aggregate_runner,days,agg_times),
        daemon=False
    )

    fetch_scheduler.start()
    agg_scheduler.start()

    try:
        fetch_scheduler.join()
        agg_scheduler.join()

    except KeyboardInterrupt:
        logger.info("Shutdown signal received. Exiting gracefully...")