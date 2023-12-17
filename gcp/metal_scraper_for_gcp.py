#!/bin/python3

import urllib.request
import sys
import json
import csv
import re
import glob
import os
import requests
import io

from fractions import Fraction
from datetime import datetime
from bs4 import BeautifulSoup
from google.cloud import bigquery

SILVER_PRICE_DBG = float(713.9)
DEBUG = False
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "bq-key.json"

def get_oz_weight(item_name):
    regex = re.compile(r'[0-9./]{1,8} *盎司')
    res = regex.search(item_name)
    if res is not None:
        tmpWeight = res.group(0).replace(' ', '').replace('盎司', '')
        tmpWeight = float(Fraction(tmpWeight).numerator / Fraction(tmpWeight).denominator)
        return float(tmpWeight)
    
    regex = re.compile(r'[0-9./]{1,8} *公克')
    res = regex.search(item_name)
    if res is not None:
        tmpWeight = res.group(0).replace(' ', '').replace('公克', '')
        tmpWeight = float(Fraction(tmpWeight).numerator / Fraction(tmpWeight).denominator)
        return float(tmpWeight / 31.1034768)
    
    regex = re.compile(r'[0-9./]{1,8} *公斤')
    res = regex.search(item_name)
    if res is not None:
        tmpWeight = res.group(0).replace(' ', '').replace('公斤', '')
        tmpWeight = float(Fraction(tmpWeight).numerator / Fraction(tmpWeight).denominator)
        return float(tmpWeight * 1000 / 31.1034768)

    return 'N/A'

def fetch(url):
    HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)',
           'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7,ja-JP;q=0.6,ja;q=0.5',
            }
    print("fetching url: " + url)
    req = urllib.request.Request(url=url, headers=HEADERS)
    content = urllib.request.urlopen(req).read()
    return content

def get_silver_price():
    price = None
    global SILVER_PRICE_DBG, DEBUG
    if DEBUG is True:
        return SILVER_PRICE_DBG

    print("fetching silver price...")
    url = "https://currency26.p.rapidapi.com/rate/XAG/TWD"

    headers = {
    	"X-RapidAPI-Key": "",
	    "X-RapidAPI-Host": "currency26.p.rapidapi.com"
    }

    response = requests.get(url, headers=headers)
    price = response.json()['rt']

    print("silver price: {0}".format(price))
    return price

def parse_truney_content(content, silver_price, domain):
    item_list = []
    soup = BeautifulSoup(content, "html5lib")
    res = soup.find_all("div", class_="card-body p-0 o_wsale_product_information")
    for node in res:
        szName = node.find("h6", itemprop="name").get_text()
        szOz = get_oz_weight(szName)
        szPriceLow = node.find("meta", itemprop="lowPrice")['content']
        szPriceHigh = node.find("meta", itemprop="highPrice")['content']
        szAvailability = node.find("meta", itemprop="availability")['content']
        szUrl = domain + node.find("link", itemprop="url")['href']
        if szOz != 'N/A':
            premium = (float(szPriceLow) / float(szOz) / float(silver_price)) - 1
        else:
            szOz = "-1"
            premium = -1

        szTimeToday = datetime.now().strftime('%Y-%m-%d')
        obj = { 'name' : szName,
                'weight' : float(szOz),
                'low price' : float(szPriceLow),  
                'high price' : float(szPriceHigh),
                'XAGTWD' : float(silver_price),
                'premium' : premium,
                'availability' : szAvailability,
                'url' : szUrl,
                'vender' : 'Truney',
                'Date' : szTimeToday,
              }
        item_list.append(obj)
    return item_list

def parse_kitco_content(content, silver_price):
    item_list = []
    soup = BeautifulSoup(content, "html5lib")
    res = soup.find_all("div", class_="production")
    for node in res:
        szName = node.find("p", class_="title-1").get_text()
        szOz = get_oz_weight(szName)
        szPriceHigh = node.find("p", class_="price").get_text().replace(' ', '').replace('台幣', '').replace('$', '').replace(',', '')
        #TO Fix
        szPriceLow = szPriceHigh
        szUrl = node.find("a")['href']
        if szOz != 'N/A':
            premium = (float(szPriceLow) / float(szOz) / float(silver_price)) - 1
        else:
            szOz = "-1"
            premium = -1

        szTimeToday = datetime.now().strftime('%Y-%m-%d')
        obj = { 'name' : szName,
                'weight' : float(szOz),
                'low price' : float(szPriceLow),  
                'high price' : float(szPriceHigh),
                'XAGTWD' : float(silver_price),
                'premium' : premium,
                'availability' : '-',
                'url' : szUrl,
                'vender' : 'Kitco',
                'Date' : szTimeToday,
              }
        item_list.append(obj)
    return item_list

def get_truney_next_page_url(content):
    soup = BeautifulSoup(content, "html5lib")
    res = soup.find_all("a", class_="page-link")
    if res is None:
        return None

    for node in res:
        if node.find("i", class_="lnr lnr-chevron-right") is not None:
            url = node['href']
            if url.find('attr') == -1:
                return None
            if url.find('&sas=pre_order') == -1 :
                url = url + '&sas=pre_order'
            return url
    return None

def get_csv_fields():
    return ['名稱', '重量(Oz)', '最低價格', '最高價格', '銀價(TWD/Oz)', '溢價', 'Link']

def read_latest_truney_json():
    list_of_files = glob.glob('json/truney*.json')
    latest_file = max(list_of_files, key=os.path.getmtime)
    with open(latest_file) as json_file:
        jsonObj = json.load(json_file)
    return jsonObj

def extract_premium(jsonObj):
    value = jsonObj['premium']
    try:
        if value < 0:
            return 100
        return value
    except KeyError:
        return 100

def get_json_by_oz(json_obj, weight):
    new_obj = []
    for item in json_obj:
        if item['weight'] == weight:
            new_obj.append(item)
    return new_obj

def get_json_1kg(json_obj):
    new_obj = []
    
    regex = re.compile(r'(1|一) *(([Kk][Gg])|(公斤))')
    for item in json_obj:
        res = regex.search(item['name'])
        if res is not None:
            new_obj.append(item)
    return new_obj

def get_truney_price(silver_price):
    DOMAIN = "https://www.truney.com"
    ROOT_URL = "https://www.truney.com/shop?search=&sas=available&sas=pre_order&attrib=2-4"
    HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)',
           'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7,ja-JP;q=0.6,ja;q=0.5',
            }
    fetch_next_page = True
    item_list = []
    csv_fileds = get_csv_fields()
    csv_list = []

    # main
    content = fetch(ROOT_URL)  
    item_list = parse_truney_content(content, silver_price, DOMAIN)

    if fetch_next_page:
        while get_truney_next_page_url(content) is not None:
            url = DOMAIN + get_truney_next_page_url(content)
            if url == DOMAIN:
                break
            content = fetch(url)
            item_list.extend(parse_truney_content(content, silver_price, DOMAIN))
    
    for item in item_list:
        push_item = [item['name'], item['weight'], item['low price'], item['high price'], item['XAGTWD'], item['premium'], item['url']]
        csv_list.append(push_item)

    return item_list, csv_list

def get_kitco_price(silver_price):
    DOMAIN = "https://kitcoasiametals.com/"
    ROOT_URL = "https://kitcoasiametals.com/tw/ProductCategory/silver"

    fetch_next_page = False
    item_list = []
    csv_fileds = get_csv_fields()
    csv_list = []

    # main
    content = fetch(ROOT_URL)
    item_list = parse_kitco_content(content, silver_price)

    if fetch_next_page:
        print("Not implemented!")
    
    for item in item_list:
        push_item = [item['name'], item['weight'], item['low price'], item['high price'], item['XAGTWD'], item['premium'], item['url']]
        csv_list.append(push_item)

    return item_list, csv_list

def get_today_low_price(truney_json):
    oz1_items = get_json_by_oz(truney_json, 1)
    min_1oz = sorted(oz1_items, key=extract_premium)[0]
    
    oz10_items = get_json_by_oz(truney_json, 10)
    min_10oz = sorted(oz10_items, key=extract_premium)[0]
    
    kg_items = get_json_1kg(truney_json)
    min_1kg = sorted(kg_items, key=extract_premium)[0]
    
    szTimeToday = datetime.now().strftime('%Y-%m-%d')
    today_item_json = {
        'Date' : szTimeToday,
        'XAG_TWD': min_1oz['XAGTWD'],
        'price_1oz': min_1oz['low price'],
        'price_10oz': min_10oz['low price'],
        'price_1kg': min_1kg['low price'],
        'premium_1oz': min_1oz['premium'],
        'premium_10oz': min_10oz['premium'],
        'premium_1kg': min_1kg['premium'],
        'lowest_1oz_item': min_1oz['name'],
        'lowest_1oz_item_link': min_1oz['url']
    }
    today_item_csv = [szTimeToday, min_1oz['XAGTWD'], min_1oz['low price'], min_10oz['low price'], min_1kg['low price'], min_1oz['premium'], min_10oz['premium'], min_1kg['premium'], min_1oz['name'], min_1oz['url']]
    
    return today_item_json, today_item_csv

def insert_price_record_to_bigquery(json_item_list):
    table_id = ''
    project_id = ''
    
    client = bigquery.Client(project = project_id)

    errors = client.insert_rows_json(table_id, json_item_list)
    if errors == []:
        print("record new rows have been added.")
    else:
        print("Encountered errors while inserting rows: {}".format(errors))

def insert_lowprice_item_to_bigquery(json_item):
    table_id = ''
    data_rows = [json_item]
    project_id = ''
    
    client = bigquery.Client(project = project_id)

    errors = client.insert_rows_json(table_id, data_rows)
    if errors == []:
        print("lowprice new rows have been added.")
    else:
        print("Encountered errors while inserting rows: {}".format(errors))


def main():
    global DEBUG
    if DEBUG == True:
        today_low_json = {
            'Date': '2023-12-13',
            'XAG_TWD': float(713.9),
            'price_1oz': float(830.84),
            'price_10oz': float(8140.94),
            'price_1kg': float(24519.33),
            'premium_1oz': float(0.16),
            'premium_10oz': float(0.14),
            'premium_1kg': float(0.07),
            'lowest_1oz_item': '2024奧地利維也納愛樂銀幣1盎司',
            'lowest_1oz_item_link': 'https://www.truney.com/shop/product/pr-08440-2024ao-di-li-wei-ye-na-ai-le-yin-bi-1ang-si-9199'
        }
    else:
        silver_price = get_silver_price()
        truney_json, truney_csv = get_truney_price(silver_price)
        kitco_json, kitco_csv = get_kitco_price(silver_price)
        all_item_json = truney_json + kitco_json
        today_low_json, today_low_csv = get_today_low_price(all_item_json)
        insert_price_record_to_bigquery(all_item_json)
    #insert_lowprice_item_to_bigquery(today_low_json)

if __name__ == "__main__":
    main()