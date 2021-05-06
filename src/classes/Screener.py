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
import talib
import classes.ConfigManager as ConfigManager
from scipy.signal import argrelextrema
from classes.ColorText import colorText
from classes.SuppressOutput import SuppressOutput

# This Class contains methods for stock analysis and screening validation
class tools:

    # Preprocess the acquired data
    def preprocessData(data, daysToLookback=ConfigManager.daysToLookback):
        sma = data.rolling(window=50).mean()
        lma = data.rolling(window=200).mean()
        vol = data.rolling(window=20).mean()
        rsi = talib.RSI(data['Close'], timeperiod=14)
        data.insert(6,'SMA',sma['Close'])
        data.insert(7,'LMA',lma['Close'])
        data.insert(8,'VolMA',vol['Volume'])
        data.insert(9,'RSI',rsi)
        data = data[::-1]               # Reverse the dataframe
        # data = data.fillna(0)
        # data = data.replace([np.inf, -np.inf], 0)
        fullData = data
        trimmedData = data.head(daysToLookback)
        return (fullData, trimmedData)

    # Validate LTP within limits
    def validateLTP(data, dict, saveDict, minLTP=ConfigManager.minLTP, maxLTP=ConfigManager.maxLTP):
        data = data.fillna(0)
        data = data.replace([np.inf, -np.inf], 0)
        recent = data.head(1)
        ltp = round(recent['Close'][0],2)
        saveDict['LTP'] = str(ltp)
        verifyStageTwo = True
        if(ConfigManager.stageTwo):
            yearlyLow = data.head(300).min()['Close']
            yearlyHigh = data.head(300).max()['Close']
            if ltp < (2 * yearlyLow) or ltp < (0.75 * yearlyHigh):
                verifyStageTwo = False
        if(ltp >= minLTP and ltp <= maxLTP and verifyStageTwo):
            dict['LTP'] = colorText.GREEN + ("%.2f" % ltp) + colorText.END
            return True
        else:
            dict['LTP'] = colorText.FAIL + ("%.2f" % ltp) + colorText.END
            return False

    # Validate if share prices are consolidating
    def validateConsolidation(data, dict, saveDict, percentage=10):
        data = data.fillna(0)
        data = data.replace([np.inf, -np.inf], 0)
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
        data = data.fillna(0)
        data = data.replace([np.inf, -np.inf], 0)
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
        data = data.fillna(0)
        data = data.replace([np.inf, -np.inf], 0)
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
        data = data.fillna(0)
        data = data.replace([np.inf, -np.inf], 0)
        recent = data.head(1)
        data = data[1:]
        hs = round(data.describe()['High']['max'],2)
        hc = round(data.describe()['Close']['max'],2)
        rc = round(recent['Close'][0],2)
        if hs > hc:
            if ((hs - hc) <= (hs*2/100)):
                saveDict['Breaking-Out'] = str(hc)
                if rc >= hc:
                    dict['Breaking-Out'] = colorText.BOLD + colorText.GREEN + "BO: " + str(hc) + " R: " + str(hs) + colorText.END
                    return True
                else:
                    dict['Breaking-Out'] = colorText.BOLD + colorText.FAIL + "BO: " + str(hc) + " R: " + str(hs) + colorText.END
                    return False
            else:    
                noOfHigherShadows = len(data[data.High > hc])
                if(daysToLookback/noOfHigherShadows <= 3):
                    saveDict['Breaking-Out'] = str(hs)
                    if rc >= hs:
                        dict['Breaking-Out'] = colorText.BOLD + colorText.GREEN + "BO: " + str(hs) + colorText.END
                        return True
                    else:
                        dict['Breaking-Out'] = colorText.BOLD + colorText.FAIL + "BO: " + str(hs) + colorText.END
                        return False
                else:
                    saveDict['Breaking-Out'] = str(hc) + ", " + str(hs)
                    if rc >= hc:
                        dict['Breaking-Out'] = colorText.BOLD + colorText.GREEN + "BO: " + str(hc) + " R: " + str(hs) + colorText.END
                        return True
                    else:
                        dict['Breaking-Out'] = colorText.BOLD + colorText.FAIL + "BO: " + str(hc) + " R: " + str(hs) + colorText.END
                        return False
        else:
            saveDict['Breaking-Out'] = str(hc)
            if rc >= hc:
                dict['Breaking-Out'] = colorText.BOLD + colorText.GREEN + "BO: " + str(hc) + colorText.END
                return True
            else:
                dict['Breaking-Out'] = colorText.BOLD + colorText.FAIL + "BO: " + str(hc) + colorText.END
                return False

    # Validate 'Inside Bar' structure for recent days
    def validateInsideBar(data, dict, saveDict, daysToLookback=4):
        data = data.fillna(0)
        data = data.replace([np.inf, -np.inf], 0)
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
        data = data.fillna(0)
        data = data.replace([np.inf, -np.inf], 0)
        if daysForLowestVolume == None:
            daysForLowestVolume = 30
        data = data.head(daysForLowestVolume)
        recent = data.head(1)
        if((recent['Volume'][0] <= data.describe()['Volume']['min']) and recent['Volume'][0] != np.nan):
            return True
        return False

    # validate if RSI is within given range
    def validateRSI(data, dict, saveDict, minRSI, maxRSI):
        data = data.fillna(0)
        data = data.replace([np.inf, -np.inf], 0)
        rsi = int(data.head(1)['RSI'][0])
        saveDict['RSI'] = rsi
        if(rsi >= minRSI and rsi <= maxRSI) and (rsi <= 70 and rsi >= 30):
            dict['RSI'] = colorText.BOLD + colorText.GREEN + str(rsi) + colorText.END
            return True
        dict['RSI'] = colorText.BOLD + colorText.FAIL + str(rsi) + colorText.END
        return False

    # Find out trend for days to lookback
    def findTrend(data, dict, saveDict, daysToLookback=ConfigManager.daysToLookback):
        data = data.head(daysToLookback)
        data = data[::-1]
        data = data.set_index(np.arange(len(data)))
        data = data.fillna(0)
        data = data.replace([np.inf, -np.inf], 0)
        data['tops'] = data['Close'].iloc[list(argrelextrema(np.array(data['Close']), np.greater_equal, order=1)[0])]
        try:
            try:
                with SuppressOutput(suppress_stdout=True,suppress_stderr=True):
                    slope,c = np.polyfit(data.index[data.tops > 0], data['tops'][data.tops > 0], 1)
            except np.RankWarning:
                slope,c = 0,0
            angle = np.rad2deg(np.arctan(slope))
            if (angle == 0):
                dict['Trend'] = colorText.BOLD + "Unknown" + colorText.END
                saveDict['Trend'] = 'Unknown'
            elif (angle <= 30 and angle >= -30):
                dict['Trend'] = colorText.BOLD + colorText.WARN + "Sideways" + colorText.END
                saveDict['Trend'] = 'Sideways'
            elif (angle >= 30 and angle < 61):
                dict['Trend'] = colorText.BOLD + colorText.GREEN + "Weak Up" + colorText.END
                saveDict['Trend'] = 'Weak Up'
            elif angle >= 60:
                dict['Trend'] = colorText.BOLD + colorText.GREEN + "Strong Up" + colorText.END
                saveDict['Trend'] = 'Strong Up'
            elif (angle >= -30 and angle < -61):
                dict['Trend'] = colorText.BOLD + colorText.FAIL + "Weak Down" + colorText.END
                saveDict['Trend'] = 'Weak Down'
            elif angle <= -60:
                dict['Trend'] = colorText.BOLD + colorText.FAIL + "Strong Down" + colorText.END
                saveDict['Trend'] = 'Strong Down'
        except np.linalg.LinAlgError:
            dict['Trend'] = colorText.BOLD + "Unknown" + colorText.END
            saveDict['Trend'] = 'Unknown'
        return saveDict['Trend']
        
        # Debugging - Experiment with data
        # import matplotlib.pyplot as plt
        # print(saveDict['Trend'])
        # print(slope)
        # print(math.degrees(math.atan(slope)))
        # plt.scatter(data.index[data.tops > 0], data['tops'][data.tops > 0], c='r')
        # plt.plot(data.index, data['Close'])
        # plt.plot(data.index, slope*data.index+c,)
        # plt.show()

    '''
    # Find out trend for days to lookback
    def validateVCP(data, dict, saveDict, daysToLookback=ConfigManager.daysToLookback, stockName=None):
        data = data.head(daysToLookback)
        data = data[::-1]
        data = data.set_index(np.arange(len(data)))
        data = data.fillna(0)
        data = data.replace([np.inf, -np.inf], 0)
        data['tops'] = data['Close'].iloc[list(argrelextrema(np.array(data['Close']), np.greater_equal, order=3)[0])]
        data['bots'] = data['Close'].iloc[list(argrelextrema(np.array(data['Close']), np.less_equal, order=3)[0])]
        try:
            try:
                top_slope,top_c = np.polyfit(data.index[data.tops > 0], data['tops'][data.tops > 0], 1)
                bot_slope,bot_c = np.polyfit(data.index[data.bots > 0], data['bots'][data.bots > 0], 1)
                topAngle = math.degrees(math.atan(top_slope))
                vcpAngle = math.degrees(math.atan(bot_slope) - math.atan(top_slope))

                # print(math.degrees(math.atan(top_slope)))
                # print(math.degrees(math.atan(bot_slope)))
                # print(vcpAngle)
                # print(topAngle)
                # print(data.max()['bots'])
                # print(data.max()['tops'])
                if (vcpAngle > 20 and vcpAngle < 70) and (topAngle > -10 and topAngle < 10) and (data['bots'].max() <= data['tops'].max()) and (len(data['bots'][data.bots > 0]) > 1):
                    print("---> GOOD VCP %s at %sRs" % (stockName, top_c))
                    import os
                    os.system("echo %s >> vcp_plots\VCP.txt" % stockName)

                    import matplotlib.pyplot as plt                
                    plt.scatter(data.index[data.tops > 0], data['tops'][data.tops > 0], c='g')
                    plt.scatter(data.index[data.bots > 0], data['bots'][data.bots > 0], c='r')
                    plt.plot(data.index, data['Close'])
                    plt.plot(data.index, top_slope*data.index+top_c,'g--')
                    plt.plot(data.index, bot_slope*data.index+bot_c,'r--')
                    if stockName != None:
                        plt.title(stockName)
                    # plt.show()
                    plt.savefig('vcp_plots\%s.png' % stockName)
                    plt.clf()
            except np.RankWarning:
                pass
        except np.linalg.LinAlgError:
            return False
    '''
    