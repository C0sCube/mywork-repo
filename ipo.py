import requests
from tendo import singleton
import sys
import datetime
import time
import socket
import configparser
import os
import pandas as pd
from details import Information
 
# Singleton pattern to avoid multiple script instances
try:
    me = singleton.SingleInstance()
except singleton.SingleInstanceException:
    print("Another instance is already running. Exiting...")
    sys.exit(1)
 
# Configuration setup
directory = os.path.dirname(__file__)
config = configparser.ConfigParser()
config.read(os.path.join(directory, 'config.ini'))
 
download_path = config['path']['download_path']
hostname = socket.gethostname()
download_path = os.path.join(directory, download_path)
 
if not os.path.exists(download_path):
    os.makedirs(download_path)
 
 
class IpoTrading(Information):
 
    def __init__(self):
        self.ipolistlink = "https://www.nseindia.com/api/ipo-current-issue"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Referer': 'https://www.nseindia.com/market-data/all-upcoming-issues-ipo',
            'Accept-Encoding': 'gzip, deflate, br, zstd'
        }
 
    def get_json_response(self, url, headers):
        session = requests.Session()
        session.headers.update(headers)
        try:
            response = session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error: {e.response.status_code} for URL: {url}")
            if e.response.status_code == 401:
                print("Unauthorized access. Retrying after 60 minutes...")
                super().log("Unauthorized access. Retrying after 60 minutes...")
                time.sleep(3600)  # Wait for 30 minutes before retrying
                return self.get_json_response(url, headers)
        except requests.exceptions.RequestException as e:
            print(f"Request Exception: {e} for URL: {url}")
            super().log(f"Request Exception: {e} for URL: {url}")
        return {}
 
    def get_ipo_list(self):
        get_data = self.get_json_response(self.ipolistlink, self.headers)
        if not get_data:
            return []
 
        ipo_list = []
        for data in get_data:
            ipo_list.append({
                'symbol': data.get('symbol', ''),
                'company_name': data.get('companyName', ''),
                'issue_start_date': data.get('issueStartDate', ''),
                'issue_end_date': data.get('issueEndDate', ''),
                'series': data.get('series', ''),
                'status': data.get('status', '')
            })
 
        return ipo_list
 
    def save_to_csv(self, data, filename):
            df = pd.DataFrame(data)
            df.to_csv(filename, index=False)
            print(f"File Created Successfully: {filename}")
            super().log(f"File saved at : {filename}")
 
    def get_ipo_details(self, ipo):
        symbol = ipo['symbol']
        company_name = ipo['company_name']
        series = ipo['series']
        status = ipo['status']
 
        get_issue_details = f"https://www.nseindia.com/api/ipo-detail?symbol={symbol}&series={series}"
        get_issue_data = self.get_json_response(get_issue_details, self.headers)
 
        if get_issue_data:
            result = get_issue_data.get('issueInfo', {}).get('dataList', [])
            current_time = datetime.datetime.now().strftime("%d_%m_%Y")
            filename = os.path.join(download_path, f'{company_name}_{symbol}_{current_time}.csv')
            self.save_to_csv(result, filename)
 
        self.get_consolidated_data(symbol, series, status, company_name)
 
    def get_consolidated_data(self, symbol, series, status, company_name):
        consolidated_data_link = f"https://www.nseindia.com/api/ipo-active-category?symbol={symbol}"
        consolidate_data = self.get_json_response(consolidated_data_link, self.headers)
 
        if consolidate_data:
            consolidate_result = consolidate_data.get('dataList', [])
            current_time = datetime.datetime.now().strftime("%d_%m_%Y")
            filename = os.path.join(download_path, f'Consolidated_bid_details_{company_name}_{current_time}.csv')
            self.save_to_csv(consolidate_result, filename)
 
    def run_crawler(self):
        print("[INFO]- Application Started..")
        ipo_list = self.get_ipo_list()
 
        if not ipo_list:
            print("No IPO data available.")
            super().log("No IPO data available.")
            return
 
        try:
            while True:
                cur_time = datetime.datetime.now()
 
                # Convert current time to the format used in IPO dates
                cur_date_str = cur_time.strftime('%d-%b-%Y')
 
                active_ipos = [
                    ipo for ipo in ipo_list
                    if ipo['issue_start_date'] <= cur_date_str <= ipo['issue_end_date']
                ]
 
                if not active_ipos:
                    print("No active IPOs at the moment.")
                    time_to_next_day = (datetime.datetime.combine(
                        datetime.date.today() + datetime.timedelta(days=1),
                        datetime.time.min
                    ) - cur_time).total_seconds()
                    time.sleep(time_to_next_day)
                    continue
 
                for ipo in active_ipos:
                    start_time = datetime.datetime.strptime(ipo['issue_start_date'], '%d-%b-%Y')
                    end_time = datetime.datetime.strptime(ipo['issue_end_date'], '%d-%b-%Y')
 
                    print(f"Processing IPO for {ipo['company_name']} (Symbol: {ipo['symbol']})")
 
                    # Run the IPO details fetch once before entering the loop
                    self.get_ipo_details(ipo)
 
                    while cur_time < end_time:
                        cur_time = datetime.datetime.now()
 
                        # Run the consolidated data fetch every 10 minutes
                        self.get_consolidated_data(ipo['symbol'], ipo['series'], ipo['status'], ipo['company_name'])
 
                        print(f"Sleeping for 10 minutes before fetching consolidated data again.")
                        time.sleep(10 * 60)
 
                    print(f"IPO {ipo['company_name']} has ended. Moving to the next one.")
                    super().log(f"IPO {ipo['company_name']} has ended. Moving to the next one.")
 
                next_start_time = datetime.datetime.combine(
                    datetime.date.today() + datetime.timedelta(days=1),
                    datetime.time.min
                )
                time_to_next_day = (next_start_time - datetime.datetime.now()).total_seconds()
                print(f'\nSleeping until next start time: {next_start_time.strftime("%Y-%m-%d %H:%M:%S")}')
                time.sleep(time_to_next_day)
 
        except Exception as e:
            print(f"Error during IPO processing: {e}")
 
 
if __name__ == "__main__":
    crawler = IpoTrading()
    crawler.run_crawler()