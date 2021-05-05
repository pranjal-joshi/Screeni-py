'''
 *  Project             :   Screenipy
 *  Author              :   Pranjal Joshi
 *  Created             :   28/04/2021
 *  Description         :   Class for analyzing and validating stocks
'''

import sys
import math
import numpy as np
import pandas as pd
import classes.ConfigManager as ConfigManager
from classes.ColorText import colorText

# This Class contains methods for stock analysis and screening validation
class tools:

    # Preprocess the acquired data
    def preprocessData(data, daysToLookback=ConfigManager.daysToLookback):
        sma = data.rolling(window=50).mean()
        lma = data.rolling(window=200).mean()
        vol = data.rolling(window=20).mean()
        data.insert(6,'SMA',sma['Close'])
        data.insert(7,'LMA',lma['Close'])
        data.insert(8,'VolMA',vol['Volume'])
        data = data[::-1]               # Reverse the dataframe
        fullData = data
        trimmedData = data.head(daysToLookback)
        data = data.replace(np.nan, 0)
        return (fullData, trimmedData)

    # Validate LTP within limits
    def validateLTP(data, dict, saveDict, minLTP=ConfigManager.minLTP, maxLTP=ConfigManager.maxLTP):
        recent = data.head(1)
        ltp = round(recent['Close'][0],2)
        saveDict['LTP'] = str(ltp)
        verifyStageTwo = True
        if(ConfigManager.stageTwo):
            yearlyLow = data.head(300).min()['Low']
            if ltp < (2 * yearlyLow):
                verifyStageTwo = False
        if(ltp >= minLTP and ltp <= maxLTP and verifyStageTwo):
            dict['LTP'] = colorText.GREEN + ("%.2f" % ltp) + colorText.END
            return True
        else:
            dict['LTP'] = colorText.FAIL + ("%.2f" % ltp) + colorText.END
            return False

    # Validate if share prices are consolidating
    def validateConsolidation(data, dict, saveDict, percentage=10):
        hc = data.describe()['Close']['max']
        lc = data.describe()['Close']['min']
        if ((hc - lc) <= (hc*percentage/100) and (hc - lc != 0)):
            dict['Consolidating'] = colorText.BOLD + colorText.GREEN + "Range = " + str(round((abs((hc-lc)/hc)*100),2))+"%" + colorText.END
        else:
            dict['Consolidating'] = colorText.BOLD + colorText.FAIL + "Range = " + str(round((abs((hc-lc)/hc)*100),2)) + "%" + colorText.END
        saveDict['Consolidating'] = str(round((abs((hc-lc)/hc)*100),2))+"%"
        return round((abs((hc-lc)/hc)*100),2)

    # Validate Moving averages
    def validateMovingAverages(data, dict, saveDict):
        recent = data.head(1)
        if(recent['SMA'][0] > recent['LMA'][0] and recent['Close'][0] > recent['SMA'][0]):
            dict['MA-Signal'] = colorText.BOLD + colorText.GREEN + 'Bullish' + colorText.END
            saveDict['MA-Signal'] = 'Bullish'
        elif(recent['SMA'][0] < recent['LMA'][0]):
            dict['MA-Signal'] = colorText.BOLD + colorText.FAIL + 'Bearish' + colorText.END
            saveDict['MA-Signal'] = 'Bearish'
        else:
            dict['MA-Signal'] = colorText.BOLD + colorText.WARN + 'Neutral' + colorText.END
            saveDict['MA-Signal'] = 'Neutral'

    # Validate if volume of last day is higher than avg
    def validateVolume(data, dict, saveDict, volumeRatio=2.5):
        recent = data.head(1)
        ratio = round(recent['Volume'][0]/recent['VolMA'][0],2)
        saveDict['Volume'] = str(ratio)+"x"
        if(ratio >= volumeRatio and ratio != np.nan and (not math.isinf(ratio)) and (ratio != 20)):
            dict['Volume'] = colorText.BOLD + colorText.GREEN + str(ratio) + "x" + colorText.END
            return True
        else:
            dict['Volume'] = colorText.BOLD + colorText.FAIL + str(ratio) + "x" + colorText.END
            return False

    # Find accurate breakout value
    def findBreakout(data, dict, saveDict, daysToLookback):
        recent = data.head(1)
        data = data[1:]
        hs = round(data.describe()['High']['max'],2)
        hc = round(data.describe()['Close']['max'],2)
        rc = round(recent['Close'][0],2)
        if hs > hc:
            if ((hs - hc) <= (hs*2/100)):
                saveDict['Breaking-Out'] = str(hc)
                if rc >= hc:
                    dict['Breaking-Out'] = colorText.BOLD + colorText.GREEN + "Yes (BO: " + str(hc) + " R: " + str(hs) + ")" + colorText.END
                    return True
                else:
                    dict['Breaking-Out'] = colorText.BOLD + colorText.FAIL + "NO (BO: " + str(hc) + " R: " + str(hs) + ")" + colorText.END
                    return False
            else:    
                noOfHigherShadows = len(data[data.High > hc])
                if(daysToLookback/noOfHigherShadows <= 3):
                    saveDict['Breaking-Out'] = str(hs)
                    if rc >= hs:
                        dict['Breaking-Out'] = colorText.BOLD + colorText.GREEN + "Yes (BO: " + str(hs) + ")" + colorText.END
                        return True
                    else:
                        dict['Breaking-Out'] = colorText.BOLD + colorText.FAIL + "NO (BO: " + str(hs) + ")" + colorText.END
                        return False
                else:
                    saveDict['Breaking-Out'] = str(hc) + ", " + str(hs)
                    if rc >= hc:
                        dict['Breaking-Out'] = colorText.BOLD + colorText.GREEN + "Yes (BO: " + str(hc) + " R: " + str(hs) + ")" + colorText.END
                        return True
                    else:
                        dict['Breaking-Out'] = colorText.BOLD + colorText.FAIL + "NO (BO: " + str(hc) + " R: " + str(hs) + ")" + colorText.END
                        return False
        else:
            saveDict['Breaking-Out'] = str(hc)
            if rc >= hc:
                dict['Breaking-Out'] = colorText.BOLD + colorText.GREEN + "Yes (BO: " + str(hc) + ")" + colorText.END
                return True
            else:
                dict['Breaking-Out'] = colorText.BOLD + colorText.FAIL + "NO (BO: " + str(hc) + ")" + colorText.END
                return False

    # Validate 'Inside Bar' structure for recent days
    def validateInsideBar(data, dict, saveDict, daysToLookback=4):
        data = data.head(daysToLookback)
        lowsData = data.sort_values(by=['Low'], ascending=False)
        highsData = data.sort_values(by=['High'], ascending=True)
        if(highsData.equals(lowsData)):
            dict['Pattern'] = colorText.BOLD + colorText.GREEN + ("Inside Bar (%d days)" % daysToLookback) + colorText.END
            saveDict['Pattern'] = "Inside Bar (%d days)" % daysToLookback
            return True
        dict['Pattern'] = ''
        saveDict['Pattern'] = ''
        return False

    # Validate if recent volume is lowest of last 'N' Days
    def validateLowestVolume(data, daysForLowestVolume):
        if daysForLowestVolume == None:
            daysForLowestVolume = 30
        data = data.head(daysForLowestVolume)
        recent = data.head(1)
        if((recent['Volume'][0] <= data.describe()['Volume']['min']) and recent['Volume'][0] != np.nan):
            return True
        return False