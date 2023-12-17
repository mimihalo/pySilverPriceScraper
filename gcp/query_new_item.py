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
from datetime import timedelta
from bs4 import BeautifulSoup
from google.cloud import bigquery

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "bq-key.json"

def query_items(date_str = None):
    project_id = '<Fill you GCP project>'
    
    client = bigquery.Client(project = project_id)

    query_str = """
    SELECT name, url
    FROM `<Fill you GCP table>`
    WHERE Date = '{0}'
    """.format(date_str)

    query_job = client.query(query_str)
    results = list(query_job.result())

    return results

def find_name_in_json_list(json_list, name):
    for json_item in json_list:
        if json_item['name'] == name:
            return json_item
    return None

def check_new_item(today_items, yesterday_items):
    new_items = []
    for today_item in today_items:
        if find_name_in_json_list(yesterday_items, today_item['name']) == None:
            new_items.append(today_item)
    return new_items

def main():
    today_items = query_items(date_str = datetime.now().strftime('%Y-%m-%d'))
    yesterday_items = query_items(date_str = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'))
    new_items = check_new_item(today_items, yesterday_items)
    print(new_items)

if __name__ == "__main__":
    main()