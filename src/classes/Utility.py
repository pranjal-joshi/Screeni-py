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