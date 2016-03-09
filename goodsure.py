# -*- coding: utf-8 -*-
import mechanize
import re
import sys
import os
import codecs
import locale
import argparse
import time
import datetime
import traceback
from bs4 import BeautifulSoup
import settings
from time import sleep

# Wrap sys.stdout into a StreamWriter to allow writing unicode.
sys.stdout = codecs.getwriter(locale.getpreferredencoding())(sys.stdout) 
br = mechanize.Browser()
br.set_handle_equiv(False)
br.set_handle_robots(False)
br.set_handle_refresh(False)
user_agent = 'Mozilla/5.0 (iPhone; CPU iPhone OS 5_0 like Mac OS X) AppleWebKit/534.46 (KHTML, like Gecko) Version/5.1 Mobile/9A334 Safari/7534.48.3'
br.addheaders = [('User-agent', user_agent)]
FindInvestTime = 0
LastSubmitTime = 0
StartTime = 0
PayMoney = None
WaitTime = None
TimeDuration = None
MinPerCent = None
BorrowTypes = None
Tid = None
Shoudong = None

def print_with_time(str):
    print datetime.datetime.today().strftime("%Y-%m-%d %H:%M:%S") + ' ',
    print str
    sys.stdout.flush()

def find_element(soup, tag, attributes=None, index=0):
    i = 0
    for li in soup.find_all(tag):
        if attributes is not None:
            can_pass = True
            for k,v in attributes.items():
                if not li.has_attr(k):
                    can_pass = False
                    break
                if ' '.join(li[k]) != v:
                    can_pass = False
                    break
            if not can_pass:
                continue
        if i == index:
            return li
        i = i + 1

def get_first_string(soup):
    for s in soup.stripped_strings:
        return s

def check_run_time():
    global StartTime
    if time.time() - StartTime > 180:
        print_with_time("max run time, will exit")
        sys.exit()

def login():
    global StartTime
    StartTime = time.time()
    br.open("https://www.goodsure.cn/user/login.html")
        
    br.select_form(nr=0)
    
    br['keywords'] = settings.Username
    br['password'] = settings.Password
    
    data = br.submit().read().decode(br.encoding())
    msg = get_center_message(data)
    if msg is not None:
        print_with_time("User %s login failed: %s"%(settings.Username, msg))
        sys.exit()
    else:
        print_with_time("User %s login succeed"%(settings.Username))
        get_balance(data)

def get_center_message(data):
    soup = BeautifulSoup(data)
    try:
        divs = soup.find_all(style='line-height:30px;position:absolute;top:36%;box-sizing:border-box;padding:10px;width:100%;font-size:20px;text-align:center;color:#FFF;font-family:zaozi-c;')
        for div in divs:
            for s in div.stripped_strings:
                return s
        divs = soup.find_all(style='line-height:26px;position:absolute;top:30%;box-sizing:border-box;padding:6px;width:100%;font-size:16px;text-align:center;color:#FFF;font-family:zaozi-c;')
        for div in divs:
            for s in div.stripped_strings:
                return s
    except:
        pass
    return None

def get_balance(data):
    global PayMoney
    soup = BeautifulSoup(data)
    balance = None
    div = find_element(soup, 'div', {'class':'accounts-z'})
    li = find_element(div, 'li')
    span = find_element(li, 'span', None, 1)
    balance = int(float(span.string))
    if balance is not None:
        if PayMoney == 0 or PayMoney > balance:
            PayMoney = balance
    if PayMoney < 1:
        print_with_time("PayMoney=%d, will exit"%(PayMoney))
        sys.exit()
    else:
        print_with_time("PayMoney=%d"%(PayMoney))

def get_table_class(table):
    for parent in table.parents:
        try:
            return ' '.join(parent['class'])
        except:
            pass
    for parent in table.previous_siblings:
        try:
            return ' '.join(parent['class'])
        except:
            pass
    return ''

def find_investment():
    global FindInvestTime, TimeDuration, MinPerCent, BorrowTypes, Shoudong
#     borrow_types = [6, 0] #微信和普通标
#     borrow_types = [5] #新手标
    while True:
        for borrow_type in BorrowTypes:
            response = br.open('http://www.goodsure.cn//invest_list/main.html?borrow_type='+str(borrow_type))
            data = response.read().decode(br.encoding())
            soup = BeautifulSoup(data)
            for table in soup.find_all('table'):
                table_class = get_table_class(table)
                title = find_element(table, 'a').string
                lilvdiv = find_element(table, 'span', {'class':"f14 green"}, 1)
                lilv = float(get_first_string(lilvdiv))
                duration = float(find_element(table, 'span', {'class':"f14 green"}, 2).string)
                div = table.next_sibling.next_sibling
                percent = get_first_string(div)
                percent = float(percent[:-1])
                div = div.next_sibling.next_sibling
                start_str = get_first_string(div)
                Gotya = False
                if Shoudong == True:
                    if table_class.find("list_shou") >= 0 and percent < 100:
                        Gotya = True
                else:
                    if (TimeDuration == 0 or duration == TimeDuration) and lilv >= MinPerCent and percent < 100 and start_str == u'立即投标':
                        Gotya = True
                if Gotya:
                    FindInvestTime = time.time()
                    a = find_element(table, 'a')
                    link = a['href']
                    print_with_time('Find valid investment %s %.1f%% %d month, percent %.2f%%'%(title, lilv, duration, percent))
                    br.open(link).read()
                    return
        print_with_time('Not found valid investment')
        check_run_time()
        time.sleep(0.1)

def submit_tender(tid=None):
    global LastSubmitTime
    tender_remain = sys.maxint
    if tid is not None:
        br.open('http://www.goodsure.cn/invest/%d.html'%(tid)).read()
    url = br.geturl()
    while True:
#         while time.time() - LastSubmitTime < 1:
#             sleep(0.1)
        LastSubmitTime = time.time()
        br.select_form(nr=0)
        money = str(PayMoney)
        br['money'] = money
        br['paypassword'] = settings.PayPassword
        response = br.submit()
        print_with_time('Auto submit investment, Pay money %s'%(money))
        data = response.read().decode(br.encoding())
        message = get_center_message(data)
        print_with_time(message)
        if message is None:
            print_with_time(data)
            break
        # or message.find(u'此标尚未通过审核') >= 0
        if message.find(u'此标已满') >= 0 or message.find(u'投标成功') >= 0 or message.find(u'不满足投标条件') >= 0:
            break
        check_run_time()
        try:
            #之前的response要read，才能保证back不重新load
            br.back().read()
        except:
            br.open(url).read()

def wait_till_can_invest():
    global WaitTime
    print_with_time('Wait time to invest')
    while time.time() - FindInvestTime < WaitTime:
        time.sleep(0.1)

def parsearg():
    global PayMoney, WaitTime, TimeDuration, MinPerCent, BorrowTypes, Tid, Shoudong
    parser = argparse.ArgumentParser(description='goodsure auto invest')
    parser.add_argument('-i', '--tid', required=False, type=int, help=u'指定id，不用找标')
    parser.add_argument('-m', '--pay_money', required=False, type=int, default=0, help=u'指定投多少钱，不指定投所有余额')
    parser.add_argument('-w', '--wait_time', required=False, type=float, default=0, help='wait time')
    parser.add_argument('-t', '--time_duration', required=False, type=int, default=0, help=u'指定投几月标')
    parser.add_argument('-p', '--percent', required=False, type=float, default=12, help=u'最低收益')
    parser.add_argument('-b', '--borrow_types', required=False, type=int, nargs='*', default=[0], help='borrow_types')
    parser.add_argument('-s', '--shoudong', required=False, action='store_true', help=u'只投手动标')
    res = parser.parse_args()
    PayMoney = res.pay_money
    WaitTime = res.wait_time
    TimeDuration = res.time_duration
    MinPerCent = res.percent
    BorrowTypes = res.borrow_types
    Tid = res.tid
    Shoudong = res.shoudong

def main():
    global Tid
    parsearg()
    login()
    if Tid is None:
        find_investment()
        wait_till_can_invest()
        submit_tender()
    else:
        submit_tender(Tid)

def test():
    global BorrowTypes
    parsearg()
#     login()
    BorrowTypes = [4]
    find_investment()
    #wait_till_can_invest()
#     submit_tender()
    sys.exit()

if __name__ == '__main__':
#     test()
    main()
