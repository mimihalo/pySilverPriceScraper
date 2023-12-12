import urllib.request
import sys
import json
import csv
import re
import requests
from fractions import Fraction
from datetime import datetime
from bs4 import BeautifulSoup

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

def update_silver_price():
    silver_price = None

    print("fetching silver price...")
    url = "https://currency26.p.rapidapi.com/rate/XAG/TWD"

    headers = {
    	"X-RapidAPI-Key": "",
	    "X-RapidAPI-Host": "currency26.p.rapidapi.com"
    }

    response = requests.get(url, headers=headers)
    silver_price = response.json()['rt']

    return silver_price

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
            premium = format((float(szPriceLow) / float(szOz) / float(silver_price)) - 1, ".0%")
        else:
            premium = '-'

        obj = { 'name' : szName,
                'weight' : szOz,
                'low price' : szPriceLow,
                'high price' : szPriceHigh,
                'XAGTWD' : silver_price,
                'premium' : premium,
                'availability' : szAvailability,
                'url' : szUrl,
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
            premium = format((float(szPriceLow) / float(szOz) / float(silver_price)) - 1, ".0%")
        else:
            premium = '-'

        obj = { 'name' : szName,
                'weight' : szOz,
                'low price' : szPriceLow,  
                'high price' : szPriceHigh,
                'XAGTWD' : silver_price,
                'premium' : premium,
                'availability' : '-',
                'url' : szUrl,
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
            return node['href']
    return None

def get_csv_fields():
    return ['名稱', '重量(Oz)', '最低價格', '最高價格', '銀價(TWD/Oz)', '溢價', 'Link']