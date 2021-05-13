'''
 *  Project             :   Screenipy
 *  Author              :   Pranjal Joshi
 *  Created             :   28/04/2021
 *  Description         :   Class for managing misc and utility methods
'''

import os
import sys
import platform
import datetime
import pandas as pd
from tabulate import tabulate
from classes.ColorText import colorText
from classes.Changelog import *

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
        print(colorText.BOLD + colorText.WARN + "\n[+] Developer: Pranjal Joshi." + colorText.END)
        print(colorText.BOLD + colorText.WARN + ("[+] Version: %s" % VERSION) + colorText.END)
        print(colorText.BOLD + colorText.WARN + "[+] More: https://github.com/pranjal-joshi/Screeni-py" + colorText.END)
        print(colorText.BOLD + colorText.WARN + "[+] Post Feedback/Issues here: https://github.com/pranjal-joshi/Screeni-py/issues" + colorText.END)
        print(colorText.BOLD + colorText.WARN + "[+] Download latest software from https://github.com/pranjal-joshi/Screeni-py/releases/latest" + colorText.END)
        input('')

    # Save last screened result to pickle file
    def setLastScreenedResults(df):
        try:
            df.sort_values(by=['Stock'], ascending=True, inplace=True)
            df.to_pickle(lastScreened)
        except:
            input(colorText.BOLD + colorText.FAIL + '[+] Failed to save recently screened result table on disk! Skipping..' + colorText.END)

    # Load last screened result to pickle file
    def getLastScreenedResults():
        try:
            df = pd.read_pickle(lastScreened)
            print(colorText.BOLD + colorText.GREEN + '\n[+] Showing recently screened results..\n' + colorText.END)
            print(tabulate(df, headers='keys', tablefmt='psql'))
            print(colorText.BOLD + colorText.WARN + "[+] Note: Trend calculation is based on number of recent days to screen as per your configuration." + colorText.END)
            input(colorText.BOLD + colorText.GREEN + '[+] Press any key to continue..' + colorText.END)
        except:
            print(colorText.BOLD + colorText.FAIL + '[+] Failed to load recently screened result table from disk! Skipping..' + colorText.END)

    # Save screened results to excel
    def promptSaveResults(df):
        try:
            response = str(input(colorText.BOLD + colorText.WARN + '[>] Do you want to save the results in excel file? [Y/N]: ')).upper()
        except ValueError:
            response = 'Y'
        if response != 'N':
            filename = 'screenipy-result_'+datetime.datetime.now().strftime("%d-%m-%y_%H.%M.%S")+".xlsx"
            df.to_excel(filename)
            print(colorText.BOLD + colorText.GREEN + ("[+] Results saved to %s" % filename) + colorText.END)

    # Prompt for asking RSI
    def promptRSIValues():
        try:
            minRSI, maxRSI = int(input(colorText.BOLD + colorText.WARN + "\n[+] Enter Min RSI value: " + colorText.END)), int(input(colorText.BOLD + colorText.WARN + "[+] Enter Max RSI value: " + colorText.END))
            if (minRSI >= 0 and minRSI <= 100) and (maxRSI >= 0 and maxRSI <= 100) and (minRSI <= maxRSI):
                return (minRSI, maxRSI)
            else:
                raise ValueError
        except ValueError:
            return (0,0)

    # Prompt for Reversal screening
    def promptReversalScreening():
        try:
            resp = int(input(colorText.BOLD + colorText.WARN + """\n[+] Select Option:
    1 > Screen for Buy Signal (Bullish Reversal)
    2 > Screen for Sell Signal (Bearish Reversal)
    0 > Cancel
[+] Select option: """ + colorText.END))
            if resp >= 0 and resp <= 2:
                return resp
            else:
                raise ValueError
        except ValueError:
            return None

    # Prompt for Reversal screening
    def promptChartPatterns():
        try:
            resp = int(input(colorText.BOLD + colorText.WARN + """\n[+] Select Option:
    1 > Screen for Bullish Inside Bar (Flag) Pattern
    2 > Screen for Bearish Inside Bar (Flag) Pattern
    0 > Cancel
[+] Select option: """ + colorText.END))
            if resp == 1 or resp == 2:
                candles = int(input(colorText.BOLD + colorText.WARN + "\n[+] How many candles (TimeFrame) to look back Inside Bar formation? : " + colorText.END))
                return (resp, candles)
            if resp >= 0 and resp <= 2:
                return resp
            else:
                raise ValueError
        except ValueError:
            input(colorText.BOLD + colorText.FAIL + "\n[+] Invalid Option Selected. Press Any Key to Continue..." + colorText.END)
            return (None, None)