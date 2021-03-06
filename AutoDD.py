#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""" AutoDD: Automatically does the so called Due Diligence for you. """

#AutoDD - Automatically does the "due diligence" for you.
#Copyright (C) 2020  Fufu Fang

#This program is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.

#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.

#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <https://www.gnu.org/licenses/>.

__author__ = "Fufu Fang"
__copyright__ = "The GNU General Public License v3.0"

from psaw import PushshiftAPI
from datetime import datetime, timedelta
import re
import constants as const
from pytz import timezone
import time
import json
from pathlib import Path
import urllib.request

def get_submission(n):
    """Returns a generator for the submission in past n days"""
    api = PushshiftAPI()
    s_date = datetime.today() - timedelta(days=n)
    s_timestamp = int(s_date.timestamp())
    gen = api.search_submissions(after=s_timestamp,
                                 subreddit='pennystocks',
                                 filter=['title', 'selftext'])
    return gen


def get_freq_list(gen):
    """
    Return the frequency list for the past n days

    :param int gen: The generator for subreddit submission
    :returns:
        - all_tbl - frequency table for all stock mentions
    """

    # Python regex pattern for stocks codes
    pattern = "[A-Z]{3,4}"
    # Dictionary containing the summaries
    all_dict = {}

    for i in gen:
        if hasattr(i, 'title'):
            title = ' ' + i.title + ' '
            title_extracted = re.findall(pattern, title)
            for j in title_extracted:
                if j in all_dict:
                    all_dict[j] += 1
                else:
                    all_dict[j] = 1

        if hasattr(i, 'selftext'):
            selftext = ' ' + i.selftext + ' '
            selftext_extracted = re.findall(pattern, selftext)
            for j in selftext_extracted:
                if j in all_dict:
                    all_dict[j] += 1
                else:
                    all_dict[j] = 1

    all_tbl = sorted(all_dict.items(), key=lambda x: x[1], reverse=True)
    all_tbl = [list(item) for item in all_tbl] 

    return all_tbl

def extract_company_name(stk_name):
    BANNED_WORDS = ['&#x20;LP', '&#x20;LLC', '&#x20;INDUSTRIES', '&#x20;INC', '&#x20;INCORPORATED', '&#x20;CORP', '&#x20;LTD']
    for item in BANNED_WORDS:
        if item in stk_name:
            stk_name = stk_name.replace(item,'')
            stk_name = stk_name.replace('&#x20;','%20')
    return stk_name
    
def retrieve_news(stk_name):
     stk_news_data = [None,None,None]
     weburl = urllib.request.urlopen("https://news.google.com/search?q=%22" + stk_name + "%22%20when%3A30d&hl=en-US&gl=US&ceid=US%3Aen")
     data = str(weburl.read())
     count = 0
     news_list = []
     while (count < const.news_item_count):
        if "?hl=en-US&amp;gl=US&amp;ceid=US%3Aen\" class=\"DY5T1d\" >" in data:
            start = data.index("?hl=en-US&amp;gl=US&amp;ceid=US%3Aen\" class=\"DY5T1d\" >") + len("?hl=en-US&amp;gl=US&amp;ceid=US%3Aen\" class=\"DY5T1d\" >")
            regex = re.compile('</a></h.><div jsname=\"')
            end = data.index(re.findall(regex,data)[0], start )
            stk_news_data[0] = (data[start:end])
            #print(stk_news_data[0])
            start = data.index("class=\"wEwyrc AVN2gc uQIVzc Sksgp\">") + len("class=\"wEwyrc AVN2gc uQIVzc Sksgp\">")
            end = data.index("</a><time class=\"", start )
            stk_news_data[1] = (data[start:end])
            regex = re.compile('datetime=\"2...-..-..T..:..:..Z\">')
            #print (re.findall(regex,data)[0])
            start = data.index(re.findall(regex,data)[0]) + len(re.findall(regex,data)[0])
            end = data.index("</time></div>", start )
            stk_news_data[2] = (data[start:end])
            data = data[end:]
            news_list.append(stk_news_data[:])
            count += 1
     return news_list


def get_fidelity_stk_vals(stock):
        weburl = urllib.request.urlopen("https://eresearch.fidelity.com/eresearch/goto/evaluate/snapshot.jhtml?symbols=" + stock + "&type=sq-NavBar")
        data = str(weburl.read())
        stk_data = [None,None,None]
        if ("cannot be found" not in data and "symbol-value-sub\">" in data):
            start = data.index("symbol-value-sub\">") + len("symbol-value-sub\">")
            end = data.index("</span><span id=", start )
            stk_data[0] = float(data[start:end])
            if ("Volume</th>" in data):
                start = data.index("Volume</th>") + len("Volume</th>") + 49
                end = data.index("</td>", start )
                stk_data[1] = int(data[start:end].replace(',',''))
            else:
                stk_data[1] = 0
            if ("companyName\">" in data):
                start = data.index("companyName\">") + len("companyName\">")
                end = data.index("</h2>", start )
                stk_data[2] = data[start:end]
                #print(stk_data[2])
                #stk_data[2] = extract_company_name(stk_data[2])
                #retrieve_news(stk_data[2])
            else:
                stk_data[2] = ""
        return stk_data


def filter_tbl(tbl, min):
    """
    Filter a frequency table

    :param list tbl: the table to be filtered
    :param int min: the number of days in the past
    :returns: the filtered table
    """
    BANNED_WORDS = [
        'THE', 'FUCK', 'ING', 'CEO', 'USD', 'WSB', 'FDA', 'NEWS', 'FOR', 'YOU',
        'BUY', 'HIGH', 'ADS', 'FOMO', 'THIS', 'OTC', 'ELI', 'IMO',
        'CBS', 'SEC', 'NOW', 'OVER', 'ROPE', 'MOON', 'NYSE', 'ESPN','HELP','ETF','FCC','FAA','USPS'
    ]
    tbl = [row for row in tbl if (int(row[1]) > min and row[0] not in BANNED_WORDS)]
    for row in tbl:
        [price,volume,name] = get_fidelity_stk_vals(row[0])
        if (price != None):
            row.append(volume)
            row.append(price)
            row.append(name)
        else:
            row.append(0)
            row.append(0)
            row.append("")
    tbl = [x for x in tbl if (x[2] != 0)]
    return tbl
    
def prev_compare(new_tbl,old_tbl):
    count_tbl = []
    for new_row in new_tbl:
        count_tbl.append([0,0,0])
        for old_row in old_tbl:
            if (new_row[0] == old_row[0]):
                count_tbl[len(count_tbl)-1][0] = new_row[1] - old_row[1]
                if (float(old_row[2]) != 0):
                    count_tbl[len(count_tbl)-1][1] = 100*(int(float(new_row[2])) /int(float(old_row[2])) -1)
                else:
                    count_tbl[len(count_tbl)-1][1] = 0
                if (float(old_row[3]) != 0):
                    count_tbl[len(count_tbl)-1][2] = 100.0*(float(new_row[3])/float(old_row[3]) - 1.0)
                else:
                    count_tbl[len(count_tbl)-1][2] = 0                
    return count_tbl
    
def long_compare(new_tbl, old_data):
    long_count_tbl = []
    for key, value in sorted(list(old_data.items()), key=lambda x:x[0].lower(), reverse=True):
        if (datetime.now(timezone('EST')) - datetime.fromisoformat(key)).total_seconds() > const.long_duration_hrs*3600:
            long_count_tbl = []
            long_count_tbl = prev_compare(new_tbl,old_data[key])
            break
    return long_count_tbl     
    
def text_colorizer(num):
    string_to_print = str(num)
    if num > 0.0:
        string_to_print = "\033[1;32;40m " + str(num) + "\033[0m"
    elif num < 0.0:
        string_to_print = "\033[1;31;40m " + str(num) + "\033[0m"
    return string_to_print

def clean_log(log_data):
    for key in list(log_data):
        if ((datetime.now(timezone('EST')) - datetime.fromisoformat(key)).total_seconds()) > (3600*const.data_expiry_duration_hrs):
            log_data.pop(key)
    return log_data

def clean_append_log(tbl, file_name):
    newitem = {str(datetime.now(timezone('EST'))): tbl}
    oldData = {}
    if Path(file_name).is_file():
        with open(file_name, 'r') as json_file:
            data = json_file.read()
            if (data != None and data != '' and data != 'null' and data != 'l'):
                oldData = json.loads(data)
                oldData = clean_log(oldData)
    with open(file_name, 'w') as json_file:
        oldData[str(datetime.now(timezone('EST')))] = tbl
        jsoned_data = json.dumps(oldData)
        json_file.write(jsoned_data)
    return oldData

def print_tbl(tbl, short_diff,long_diff):
    print(datetime.now(timezone('EST')))
    print("Rank\tStock\tMentions\t" + str(int(const.short_duration_min)) + " min. diff\t"  + str(int(const.long_duration_hrs)) + " hr. diff\tVolume\t\t" + str(int(const.short_duration_min)) + " min. %diff\t"  + str(int(const.long_duration_hrs)) + "hr. %diff\tPrice\t" + str(int(const.short_duration_min)) + " min. %diff\t"  + str(int(const.long_duration_hrs)) +  "hr. %diff\n==================================================================================================================================================")
    count = 0

    for row in tbl:
        padding = ""
        if len(row[0]) < 4:
            padding = ' '
        if count < const.list_length:
            long_mention = "-"
            short_mention = "-"
            long_vol = "-"
            short_vol = "-"
            long_price = "-"
            short_price = "-"
            if (len(long_diff)>0):
                long_mention = text_colorizer(long_diff[count][0])
                long_vol = text_colorizer(round(long_diff[count][1],0))
                long_price = text_colorizer(round(long_diff[count][2],2))
            if (len(short_diff)>0) :
                short_mention = text_colorizer(short_diff[count][0])
                short_vol = text_colorizer(round(short_diff[count][1],0))
                short_price = text_colorizer(round(short_diff[count][2],2))
            vol = round(float(row[2]),0)
            print(str(count+1) + ": " + padding + "\t" + str(row[0]) + padding + "\t" + str(row[1]) + padding + "\t\t" + short_mention  + padding + "\t\t" + long_mention + padding + "\t\t" + f"{vol:,}"+ padding + "\t" + short_vol  + padding + "\t\t" + long_vol + padding + "\t\t" + str(round(float(row[3]),2)) + padding + "\t" + short_price  + padding + "\t" + long_price)
            print('-------------------------------------------------------------------------------------------------------------------------------------------------------')
        count += 1
        
def print_news_list(tbl):
    count = 0
    for row in tbl:
        if count < const.list_length:
            print(row[0])
            cleaned_stk_name = extract_company_name(row[4])
            news_list = retrieve_news(cleaned_stk_name)
            #print(news_list)
            for item in news_list:
                print(item[0] + ", " + item[1] + ", " + item[2])
        count += 1

def time_to_sleep():
    day = datetime.utcnow().isoweekday()
    hour =  datetime.utcnow().hour
    minute = datetime.utcnow().minute
    second = datetime.utcnow().second
    tts = const.short_duration_min*60
    if (day in range(1,7)):
        if (hour in range(0,23)):
            tts = const.short_duration_min*60
    ''' elif (hour > 22):#mon-fri 3pm-12am, sleep till 910 am
            tts = (38 - hour)*3600 - minute*60 - second + 600
        elif (hour < 14):#mon-fri pre-8am, sleep till 910 am
            tts = (14-hour)*3600 - minute*60 - second + 600
    elif (day > 5):#weekend, sleep till monday 910am
        tts = (7-day)*24*3600 + (38-hour)*3600 - minute*60 - second + 600'''
    #if tts > const.short_duration:
        #d = datetime(1,1,1) + timedelta(seconds=tts)
        #print("Sleeping for ")
        #print("%d:%d:%d:%d" % (d.day-1, d.hour, d.minute, d.second))
        #d = datetime.utcnow() + timedelta(seconds=tts)
        #print("Wake up at " + d.strftime("%A"))
        #print("%d:%d:%d" % (d.hour, d.minute, d.second))
    return tts

if __name__ == '__main__':
    prev_tbl = {}
    while True:
        start_time = datetime.utcnow()
        print("Gathering data...")
        gen = get_submission(1)  # Get 1 day worth of submission
        all_tbl = get_freq_list(gen)
        all_tbl = filter_tbl(all_tbl, 2)
        log_data = clean_append_log(all_tbl,"rps.json")
        short_comp_tbl = prev_compare(all_tbl, prev_tbl)
        long_comp_tbl = long_compare(all_tbl,log_data)
        print_tbl(all_tbl, short_comp_tbl, long_comp_tbl)
        print_news_list(all_tbl)
        prev_tbl = all_tbl
 
        sleep_duration = time_to_sleep()
        compute_time = (datetime.utcnow() - start_time).seconds + (datetime.utcnow() - start_time).microseconds/1000000.0
        print("Run time: " + str(compute_time/60.0) + " minutes")
        time.sleep(max(0.1,(sleep_duration-compute_time)))
