'''
 *  Project             :   Screenipy
 *  Author              :   Pranjal Joshi
 *  Created             :   28/04/2021
 *  Description         :   Class for managing misc and utility methods
'''

from decimal import DivisionByZero
from genericpath import isfile
import os
import sys
import platform
import datetime
import pytz
import pickle
import requests
import time
import joblib
import keras
import pandas as pd
from alive_progress import alive_bar
from tabulate import tabulate
from time import sleep
from classes.ColorText import colorText
from classes.Changelog import VERSION, changelog
import classes.ConfigManager as ConfigManager

art = colorText.GREEN + '''
     .d8888b.                                             d8b                   
    d88P  Y88b                                            Y8P                   
    Y88b.                                                                       
     "Y888b.    .d8888b 888d888 .d88b.   .d88b.  88888b.  888 88888b.  888  888 
        "Y88b. d88P"    888P"  d8P  Y8b d8P  Y8b 888 "88b 888 888 "88b 888  888 
          "888 888      888    88888888 88888888 888  888 888 888  888 888  888 
    Y88b  d88P Y88b.    888    Y8b.     Y8b.     888  888 888 888 d88P Y88b 888 
     "Y8888P"   "Y8888P 888     "Y8888   "Y8888  888  888 888 88888P"   "Y88888 
                                                              888           888 
                                                              888      Y8b d88P 
                                                              888       "Y88P"  

''' + colorText.END

lastScreened = 'last_screened_results.pkl'

# Class for managing misc and utility methods


class tools:

    def clearScreen():
        if platform.system() == 'Windows':
            os.system('cls')
        else:
            os.system('clear')
        print(art)

    # Print about developers and repository
    def showDevInfo():
        print('\n'+changelog)
        print(colorText.BOLD + colorText.WARN +
              "\n[+] Developer: Pranjal Joshi." + colorText.END)
        print(colorText.BOLD + colorText.WARN +
              ("[+] Version: %s" % VERSION) + colorText.END)
        print(colorText.BOLD +
              "[+] Home Page: https://github.com/pranjal-joshi/Screeni-py" + colorText.END)
        print(colorText.BOLD + colorText.FAIL +
              "[+] Read/Post Issues here: https://github.com/pranjal-joshi/Screeni-py/issues" + colorText.END)
        print(colorText.BOLD + colorText.GREEN +
              "[+] Join Community Discussions: https://github.com/pranjal-joshi/Screeni-py/discussions" + colorText.END)
        print(colorText.BOLD + colorText.BLUE +
              "[+] Download latest software from https://github.com/pranjal-joshi/Screeni-py/releases/latest" + colorText.END)
        input('')

    # Save last screened result to pickle file
    def setLastScreenedResults(df):
        try:
            df.sort_values(by=['Stock'], ascending=True, inplace=True)
            df.to_pickle(lastScreened)
        except IOError:
            input(colorText.BOLD + colorText.FAIL +
                  '[+] Failed to save recently screened result table on disk! Skipping..' + colorText.END)

    # Load last screened result to pickle file
    def getLastScreenedResults():
        try:
            df = pd.read_pickle(lastScreened)
            print(colorText.BOLD + colorText.GREEN +
                  '\n[+] Showing recently screened results..\n' + colorText.END)
            print(tabulate(df, headers='keys', tablefmt='psql'))
            print(colorText.BOLD + colorText.WARN +
                  "[+] Note: Trend calculation is based on number of recent days to screen as per your configuration." + colorText.END)
            input(colorText.BOLD + colorText.GREEN +
                  '[+] Press any key to continue..' + colorText.END)
        except FileNotFoundError:
            print(colorText.BOLD + colorText.FAIL +
                  '[+] Failed to load recently screened result table from disk! Skipping..' + colorText.END)

    def isTradingTime():
        curr = datetime.datetime.now(pytz.timezone('Asia/Kolkata'))
        openTime = curr.replace(hour=9, minute=15)
        closeTime = curr.replace(hour=15, minute=30)
        return ((openTime <= curr <= closeTime) and (0 <= curr.weekday() <= 4))

    def isClosingHour():
        curr = datetime.datetime.now(pytz.timezone('Asia/Kolkata'))
        openTime = curr.replace(hour=15, minute=00)
        closeTime = curr.replace(hour=15, minute=30)
        return ((openTime <= curr <= closeTime) and (0 <= curr.weekday() <= 4))

    def saveStockData(stockDict, configManager, loadCount):
        curr = datetime.datetime.now(pytz.timezone('Asia/Kolkata'))
        openTime = curr.replace(hour=9, minute=15)
        cache_date = datetime.date.today()  # for monday to friday
        weekday = datetime.date.today().weekday()
        if curr < openTime:  # for monday to friday before 9:15
            cache_date = datetime.datetime.today() - datetime.timedelta(1)
        if weekday == 0 and curr < openTime:  # for monday before 9:15
            cache_date = datetime.datetime.today() - datetime.timedelta(3)
        if weekday == 5 or weekday == 6:  # for saturday and sunday
            cache_date = datetime.datetime.today() - datetime.timedelta(days=weekday - 4)
        cache_date = cache_date.strftime("%d%m%y")
        cache_file = "stock_data_" + str(cache_date) + ".pkl"
        configManager.deleteStockData(excludeFile=cache_file)

        if not os.path.exists(cache_file) or len(stockDict) > (loadCount+1):
            with open(cache_file, 'wb') as f:
                try:
                    pickle.dump(stockDict.copy(), f)
                    print(colorText.BOLD + colorText.GREEN +
                          "=> Done." + colorText.END)
                except pickle.PicklingError:
                    print(colorText.BOLD + colorText.FAIL +
                          "=> Error while Caching Stock Data." + colorText.END)
        else:
            print(colorText.BOLD + colorText.GREEN +
                  "=> Already Cached." + colorText.END)

    def loadStockData(stockDict, configManager, proxyServer=None):
        curr = datetime.datetime.now(pytz.timezone('Asia/Kolkata'))
        openTime = curr.replace(hour=9, minute=15)
        last_cached_date = datetime.date.today()  # for monday to friday after 3:30
        weekday = datetime.date.today().weekday()
        if curr < openTime:  # for monday to friday before 9:15
            last_cached_date = datetime.datetime.today() - datetime.timedelta(1)
        if weekday == 5 or weekday == 6:  # for saturday and sunday
            last_cached_date = datetime.datetime.today() - datetime.timedelta(days=weekday - 4)
        if weekday == 0 and curr < openTime:  # for monday before 9:15
            last_cached_date = datetime.datetime.today() - datetime.timedelta(3)
        last_cached_date = last_cached_date.strftime("%d%m%y")
        cache_file = "stock_data_" + str(last_cached_date) + ".pkl"
        if os.path.exists(cache_file):
            with open(cache_file, 'rb') as f:
                try:
                    stockData = pickle.load(f)
                    print(colorText.BOLD + colorText.GREEN +
                          "[+] Automatically Using Cached Stock Data due to After-Market hours!" + colorText.END)
                    for stock in stockData:
                        stockDict[stock] = stockData.get(stock)
                except pickle.UnpicklingError:
                    print(colorText.BOLD + colorText.FAIL +
                          "[+] Error while Reading Stock Cache." + colorText.END)
                except EOFError:
                    print(colorText.BOLD + colorText.FAIL +
                          "[+] Stock Cache Corrupted." + colorText.END)
        elif ConfigManager.default_period == configManager.period and ConfigManager.default_duration == configManager.duration:
            cache_url = "https://raw.github.com/pranjal-joshi/Screeni-py/actions-data-download/actions-data-download/" + cache_file
            if proxyServer is not None:
                resp = requests.get(cache_url, stream=True, proxies={'https':proxyServer})
            else:
                resp = requests.get(cache_url, stream=True)
            if resp.status_code == 200:
                print(colorText.BOLD + colorText.FAIL +
                      "[+] After-Market Stock Data is not cached.." + colorText.END)
                print(colorText.BOLD + colorText.GREEN +
                      "[+] Downloading cache from Screenipy server for faster processing, Please Wait.." + colorText.END)
                try:
                    chunksize = 1024*1024*1
                    filesize = int(int(resp.headers.get('content-length'))/chunksize)
                    bar, spinner = tools.getProgressbarStyle()
                    f = open(cache_file, 'wb')
                    dl = 0
                    with alive_bar(filesize, bar=bar, spinner=spinner, manual=True) as progressbar:
                        for data in resp.iter_content(chunk_size=chunksize):
                            dl += 1
                            f.write(data)
                            progressbar(dl/filesize)
                            if dl >= filesize:
                                progressbar(1.0)
                    f.close()
                except Exception as e:
                    print("[!] Download Error - " + str(e))
                print("")
                tools.loadStockData(stockDict, configManager, proxyServer)
            else:
                print(colorText.BOLD + colorText.FAIL +
                      "[+] Cache unavailable on Screenipy server, Continuing.." + colorText.END)

    # Save screened results to excel
    def promptSaveResults(df):
        try:
            response = str(input(colorText.BOLD + colorText.WARN +
                                 '[>] Do you want to save the results in excel file? [Y/N]: ')).upper()
        except ValueError:
            response = 'Y'
        if response != 'N':
            filename = 'screenipy-result_' + \
                datetime.datetime.now().strftime("%d-%m-%y_%H.%M.%S")+".xlsx"
            df.to_excel(filename)
            print(colorText.BOLD + colorText.GREEN +
                  ("[+] Results saved to %s" % filename) + colorText.END)

    # Prompt for asking RSI
    def promptRSIValues():
        try:
            minRSI, maxRSI = int(input(colorText.BOLD + colorText.WARN + "\n[+] Enter Min RSI value: " + colorText.END)), int(
                input(colorText.BOLD + colorText.WARN + "[+] Enter Max RSI value: " + colorText.END))
            if (minRSI >= 0 and minRSI <= 100) and (maxRSI >= 0 and maxRSI <= 100) and (minRSI <= maxRSI):
                return (minRSI, maxRSI)
            raise ValueError
        except ValueError:
            return (0, 0)

    # Prompt for Reversal screening
    def promptReversalScreening():
        try:
            resp = int(input(colorText.BOLD + colorText.WARN + """\n[+] Select Option:
    1 > Screen for Buy Signal (Bullish Reversal)
    2 > Screen for Sell Signal (Bearish Reversal)
    3 > Screen for Momentum Gainers (Rising Bullish Momentum)
    4 > Screen for Reversal at Moving Average (Bullish Reversal)
    5 > Screen for Volume Spread Analysis (Bullish VSA Reversal)
    6 > Screen for Narrow Range (NRx) Reversal
    0 > Cancel
[+] Select option: """ + colorText.END))
            if resp >= 0 and resp <= 6:
                if resp == 4:
                    try:
                        maLength = int(input(colorText.BOLD + colorText.WARN +
                                             '\n[+] Enter MA Length (E.g. 50 or 200): ' + colorText.END))
                        return resp, maLength
                    except ValueError:
                        print(colorText.BOLD + colorText.FAIL +
                              '\n[!] Invalid Input! MA Lenght should be single integer value!\n' + colorText.END)
                        raise ValueError
                elif resp == 6:
                    try:
                        maLength = int(input(colorText.BOLD + colorText.WARN +
                                             '\n[+] Enter NR timeframe [Integer Number] (E.g. 4, 7, etc.): ' + colorText.END))
                        return resp, maLength
                    except ValueError:
                        print(colorText.BOLD + colorText.FAIL + '\n[!] Invalid Input! NR timeframe should be single integer value!\n' + colorText.END)
                        raise ValueError
                return resp, None
            raise ValueError
        except ValueError:
            return None, None

    # Prompt for Reversal screening
    def promptChartPatterns():
        try:
            resp = int(input(colorText.BOLD + colorText.WARN + """\n[+] Select Option:
    1 > Screen for Bullish Inside Bar (Flag) Pattern
    2 > Screen for Bearish Inside Bar (Flag) Pattern
    3 > Screen for the Confluence (50 & 200 MA/EMA)
    4 > Screen for VCP (Experimental)
    5 > Screen for Buying at Trendline (Ideal for Swing/Mid/Long term)
    0 > Cancel
[+] Select option: """ + colorText.END))
            if resp == 1 or resp == 2:
                candles = int(input(colorText.BOLD + colorText.WARN +
                                    "\n[+] How many candles (TimeFrame) to look back Inside Bar formation? : " + colorText.END))
                return (resp, candles)
            if resp == 3:
                percent = float(input(colorText.BOLD + colorText.WARN +
                                      "\n[+] Enter Percentage within which all MA/EMAs should be (Ideal: 1-2%)? : " + colorText.END))
                return (resp, percent/100.0)
            if resp >= 0 and resp <= 5:
                return resp, 0
            raise ValueError
        except ValueError:
            input(colorText.BOLD + colorText.FAIL +
                  "\n[+] Invalid Option Selected. Press Any Key to Continue..." + colorText.END)
            return (None, None)

    def getProgressbarStyle():
        bar = 'smooth'
        spinner = 'waves'
        if 'Windows' in platform.platform():
            bar = 'classic2'
            spinner = 'dots_recur'
        return bar, spinner

    def getNiftyModel(proxyServer=None):
        files = ['nifty_model_v2.h5', 'nifty_model_v2.pkl']
        urls = [
            "https://raw.github.com/pranjal-joshi/Screeni-py/new-features/src/ml/nifty_model_v2.h5",
            "https://raw.github.com/pranjal-joshi/Screeni-py/new-features/src/ml/nifty_model_v2.pkl"
        ]
        if os.path.isfile(files[0]) and os.path.isfile(files[1]):
            file_age = (time.time() - os.path.getmtime(files[0]))/604800
            if file_age > 1:
                download = True
                os.remove(files[0])
                os.remove(files[1])
            else:
                download = False
        else:
            download = True
        if download:
            for file_url in urls:
                if proxyServer is not None:
                    resp = requests.get(file_url, stream=True, proxies={'https':proxyServer})
                else:
                    resp = requests.get(file_url, stream=True)
                if resp.status_code == 200:
                    print(colorText.BOLD + colorText.GREEN +
                            "[+] Downloading AI model (v2) for Nifty predictions, Please Wait.." + colorText.END)
                    try:
                        chunksize = 1024*1024*1
                        filesize = int(int(resp.headers.get('content-length'))/chunksize)
                        filesize = 1 if not filesize else filesize
                        bar, spinner = tools.getProgressbarStyle()
                        f = open(file_url.split('/')[-1], 'wb')
                        dl = 0
                        with alive_bar(filesize, bar=bar, spinner=spinner, manual=True) as progressbar:
                            for data in resp.iter_content(chunk_size=chunksize):
                                dl += 1
                                f.write(data)
                                progressbar(dl/filesize)
                                if dl >= filesize:
                                    progressbar(1.0)
                        f.close()
                    except Exception as e:
                        print("[!] Download Error - " + str(e))
            time.sleep(3)
        model = keras.models.load_model(files[0])
        pkl = joblib.load(files[1])
        return model, pkl

    def getSigmoidConfidence(x):
        out_min, out_max = 0, 100
        if x > 0.5:
            in_min = 0.50001
            in_max = 1
        else:
            in_min = 0
            in_max = 0.5
        return round(((x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min),3)

    def alertSound(beeps=3, delay=0.2):
        for i in range(beeps):
            print('\a')
            sleep(delay)