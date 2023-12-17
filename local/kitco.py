#!/bin/python3

import urllib.request
import sys
import json
import csv
import re
import metal_lib
from fractions import Fraction
from datetime import datetime
from bs4 import BeautifulSoup

# args


def main():
    # vars
    FETCH_LATEST = False
    ROOT_PATH="/volume1/metal_data/"
    CONTENT_FILE_PATH = "kitco-temp.html"
    JSON_FILE_PATH = "kitco-{0}.json"
    CSV_FILE_PATH = "kitco-{0}.csv"
    DOMAIN = "https://kitcoasiametals.com/"
    ROOT_URL = "https://kitcoasiametals.com/tw/ProductCategory/silver"
    HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)',
           'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7,ja-JP;q=0.6,ja;q=0.5',
            }
    silver_price = None
    fetch_next_page = False
    item_list = []
    csv_fileds = metal_lib.get_csv_fields()
    csv_list = []

    silver_price = metal_lib.update_silver_price()

    # main
    if FETCH_LATEST:
        print("fetching latest content...")
        content = metal_lib.fetch(ROOT_URL)
        with open(CONTENT_FILE_PATH, 'wb') as f:
            f.write(content)
    else:
        print("reading from file...")
        with open(CONTENT_FILE_PATH, 'rb') as f:
            content = f.read()
    
    item_list = metal_lib.parse_kitco_content(content, silver_price)

    if fetch_next_page:
        print("Not implemented!")
    
    for item in item_list:
        push_item = [item['name'], item['weight'], item['low price'], item['high price'], item['XAGTWD'], item['premium'], item['url']]
        csv_list.append(push_item)

    szTimeNow = datetime.now().strftime('%Y-%m-%d-%H-%M')
    with open(JSON_FILE_PATH.format(szTimeNow), 'w') as f:
        json.dump(item_list, f)
    
    with open(CSV_FILE_PATH.format(szTimeNow), 'w') as f:
        writer = csv.writer(f)
        writer.writerow(csv_fileds)
        writer.writerows(csv_list)

if __name__ == "__main__":
    main()