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
from scipy.signal import argrelextrema
from classes.ColorText import colorText
from classes.SuppressOutput import SuppressOutput

# Exception for newly listed stocks with candle nos < daysToLookback
class StockDataNotAdequate(Exception):
    pass

# This Class contains methods for stock analysis and screening validation
class tools:

    def __init__(self, configManager) -> None:
        self.configManager = configManager

    # Private method to find candle type
    # True = Bullish, False = Bearish
    def getCandleType(self, dailyData):
        return bool(dailyData['Close'][0] >= dailyData['Open'][0])
            

    # Preprocess the acquired data
    def preprocessData(self, data, daysToLookback=None):
        if daysToLookback is None:
            daysToLookback = self.configManager.daysToLookback
        if self.configManager.useEMA:
            sma = talib.EMA(data['Close'],timeperiod=50)
            lma = talib.EMA(data['Close'],timeperiod=200)
            data.insert(6,'SMA',sma)
            data.insert(7,'LMA',lma)
        else:
            sma = data.rolling(window=50).mean()
            lma = data.rolling(window=200).mean()
            data.insert(6,'SMA',sma['Close'])
            data.insert(7,'LMA',lma['Close'])
        vol = data.rolling(window=20).mean()
        rsi = talib.RSI(data['Close'], timeperiod=14)
        data.insert(8,'VolMA',vol['Volume'])
        data.insert(9,'RSI',rsi)
        data = data[::-1]               # Reverse the dataframe
        # data = data.fillna(0)
        # data = data.replace([np.inf, -np.inf], 0)
        fullData = data
        trimmedData = data.head(daysToLookback)
        return (fullData, trimmedData)

    # Validate LTP within limits
    def validateLTP(self, data, screenDict, saveDict, minLTP=None, maxLTP=None):
        if minLTP is None:
            minLTP = self.configManager.minLTP
        if maxLTP is None:
            maxLTP = self.configManager.maxLTP
        data = data.fillna(0)
        data = data.replace([np.inf, -np.inf], 0)
        recent = data.head(1)
        ltp = round(recent['Close'][0],2)
        saveDict['LTP'] = str(ltp)
        verifyStageTwo = True
        if(self.configManager.stageTwo):
            yearlyLow = data.head(300).min()['Close']
            yearlyHigh = data.head(300).max()['Close']
            if ltp < (2 * yearlyLow) or ltp < (0.75 * yearlyHigh):
                verifyStageTwo = False
        if(ltp >= minLTP and ltp <= maxLTP and verifyStageTwo):
            screenDict['LTP'] = colorText.GREEN + ("%.2f" % ltp) + colorText.END
            return True
        screenDict['LTP'] = colorText.FAIL + ("%.2f" % ltp) + colorText.END
        return False

    # Validate if share prices are consolidating
    def validateConsolidation(self, data, screenDict, saveDict, percentage=10):
        data = data.fillna(0)
        data = data.replace([np.inf, -np.inf], 0)
        hc = data.describe()['Close']['max']
        lc = data.describe()['Close']['min']
        if ((hc - lc) <= (hc*percentage/100) and (hc - lc != 0)):
            screenDict['Consolidating'] = colorText.BOLD + colorText.GREEN + "Range = " + str(round((abs((hc-lc)/hc)*100),2))+"%" + colorText.END
        else:
            screenDict['Consolidating'] = colorText.BOLD + colorText.FAIL + "Range = " + str(round((abs((hc-lc)/hc)*100),2)) + "%" + colorText.END
        saveDict['Consolidating'] = str(round((abs((hc-lc)/hc)*100),2))+"%"
        return round((abs((hc-lc)/hc)*100),2)

    # Validate Moving averages and look for buy/sell signals
    def validateMovingAverages(self, data, screenDict, saveDict, maRange=2.5):
        data = data.fillna(0)
        data = data.replace([np.inf, -np.inf], 0)
        recent = data.head(1)
        if(recent['SMA'][0] > recent['LMA'][0] and recent['Close'][0] > recent['SMA'][0]):
            screenDict['MA-Signal'] = colorText.BOLD + colorText.GREEN + 'Bullish' + colorText.END
            saveDict['MA-Signal'] = 'Bullish'
        elif(recent['SMA'][0] < recent['LMA'][0]):
            screenDict['MA-Signal'] = colorText.BOLD + colorText.FAIL + 'Bearish' + colorText.END
            saveDict['MA-Signal'] = 'Bearish'
        else:
            screenDict['MA-Signal'] = colorText.BOLD + colorText.WARN + 'Neutral' + colorText.END
            saveDict['MA-Signal'] = 'Neutral'

        smaDev = data['SMA'][0] * maRange / 100
        lmaDev = data['LMA'][0] * maRange / 100
        open, high, low, close, sma, lma = data['Open'][0], data['High'][0], data['Low'][0], data['Close'][0], data['SMA'][0], data['LMA'][0]
        maReversal = 0
        # Taking Support 50
        if close > sma and low <= (sma + smaDev):
            screenDict['MA-Signal'] = colorText.BOLD + colorText.GREEN + '50MA-Support' + colorText.END
            saveDict['MA-Signal'] = '50MA-Support'
            maReversal = 1
        # Validating Resistance 50
        elif close < sma and high >= (sma - smaDev):
            screenDict['MA-Signal'] = colorText.BOLD + colorText.FAIL + '50MA-Resist' + colorText.END
            saveDict['MA-Signal'] = '50MA-Resist'
            maReversal = -1
        # Taking Support 200
        elif close > lma and low <= (lma + lmaDev):
            screenDict['MA-Signal'] = colorText.BOLD + colorText.GREEN + '200MA-Support' + colorText.END
            saveDict['MA-Signal'] = '200MA-Support'
            maReversal = 1
        # Validating Resistance 200
        elif close < lma and high >= (lma - lmaDev):
            screenDict['MA-Signal'] = colorText.BOLD + colorText.FAIL + '200MA-Resist' + colorText.END
            saveDict['MA-Signal'] = '200MA-Resist'
            maReversal = -1
        # For a Bullish Candle
        if self.getCandleType(data):
            # Crossing up 50
            if open < sma and close > sma:
                screenDict['MA-Signal'] = colorText.BOLD + colorText.GREEN + 'BullCross-50MA' + colorText.END
                saveDict['MA-Signal'] = 'BullCross-50MA'
                maReversal = 1            
            # Crossing up 200
            elif open < lma and close > lma:
                screenDict['MA-Signal'] = colorText.BOLD + colorText.GREEN + 'BullCross-200MA' + colorText.END
                saveDict['MA-Signal'] = 'BullCross-200MA'
                maReversal = 1
        # For a Bearish Candle
        elif not self.getCandleType(data):
            # Crossing down 50
            if open > sma and close < sma:
                screenDict['MA-Signal'] = colorText.BOLD + colorText.FAIL + 'BearCross-50MA' + colorText.END
                saveDict['MA-Signal'] = 'BearCross-50MA'
                maReversal = -1         
            # Crossing up 200
            elif open > lma and close < lma:
                screenDict['MA-Signal'] = colorText.BOLD + colorText.FAIL + 'BearCross-200MA' + colorText.END
                saveDict['MA-Signal'] = 'BearCross-200MA'
                maReversal = -1
        return maReversal

    # Validate if volume of last day is higher than avg
    def validateVolume(self, data, screenDict, saveDict, volumeRatio=2.5):
        data = data.fillna(0)
        data = data.replace([np.inf, -np.inf], 0)
        recent = data.head(1)
        if recent['VolMA'][0] == 0: # Handles Divide by 0 warning
            return False
        ratio = round(recent['Volume'][0]/recent['VolMA'][0],2)
        saveDict['Volume'] = str(ratio)+"x"
        if(ratio >= volumeRatio and ratio != np.nan and (not math.isinf(ratio)) and (ratio != 20)):
            screenDict['Volume'] = colorText.BOLD + colorText.GREEN + str(ratio) + "x" + colorText.END
            return True
        screenDict['Volume'] = colorText.BOLD + colorText.FAIL + str(ratio) + "x" + colorText.END
        return False

    # Find accurate breakout value
    def findBreakout(self, data, screenDict, saveDict, daysToLookback):
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
                    screenDict['Breaking-Out'] = colorText.BOLD + colorText.GREEN + "BO: " + str(hc) + " R: " + str(hs) + colorText.END
                    return True and self.getCandleType(recent)
                screenDict['Breaking-Out'] = colorText.BOLD + colorText.FAIL + "BO: " + str(hc) + " R: " + str(hs) + colorText.END
                return False
            noOfHigherShadows = len(data[data.High > hc])
            if(daysToLookback/noOfHigherShadows <= 3):
                saveDict['Breaking-Out'] = str(hs)
                if rc >= hs:
                    screenDict['Breaking-Out'] = colorText.BOLD + colorText.GREEN + "BO: " + str(hs) + colorText.END
                    return True and self.getCandleType(recent)
                screenDict['Breaking-Out'] = colorText.BOLD + colorText.FAIL + "BO: " + str(hs) + colorText.END
                return False
            saveDict['Breaking-Out'] = str(hc) + ", " + str(hs)
            if rc >= hc:
                screenDict['Breaking-Out'] = colorText.BOLD + colorText.GREEN + "BO: " + str(hc) + " R: " + str(hs) + colorText.END
                return True and self.getCandleType(recent)
            screenDict['Breaking-Out'] = colorText.BOLD + colorText.FAIL + "BO: " + str(hc) + " R: " + str(hs) + colorText.END
            return False
        else:
            saveDict['Breaking-Out'] = str(hc)
            if rc >= hc:
                screenDict['Breaking-Out'] = colorText.BOLD + colorText.GREEN + "BO: " + str(hc) + colorText.END
                return True and self.getCandleType(recent)
            screenDict['Breaking-Out'] = colorText.BOLD + colorText.FAIL + "BO: " + str(hc) + colorText.END
            return False

    # Validate 'Inside Bar' structure for recent days
    def validateInsideBar(self, data, screenDict, saveDict, bullBear=1, daysToLookback=5):
        orgData = data
        for i in range(daysToLookback, round(daysToLookback*0.5)-1, -1):
            if i == 2:
                return 0        # Exit if only last 2 candles are left
            if bullBear == 1:
                if "Up" in saveDict['Trend'] and ("Bull" in saveDict['MA-Signal'] or "Support" in saveDict['MA-Signal']):
                    data = orgData.head(i)
                    refCandle = data.tail(1)
                    if (len(data.High[data.High > refCandle.High.item()]) == 0) and (len(data.Low[data.Low < refCandle.Low.item()]) == 0) and (len(data.Open[data.Open > refCandle.High.item()]) == 0) and (len(data.Close[data.Close < refCandle.Low.item()]) == 0):
                        screenDict['Pattern'] = colorText.BOLD + colorText.WARN + ("Inside Bar (%d)" % i) + colorText.END
                        saveDict['Pattern'] = "Inside Bar (%d)" % i
                        return i
                else:
                    return 0
            else:
                if "Down" in saveDict['Trend'] and ("Bear" in saveDict['MA-Signal'] or "Resist" in saveDict['MA-Signal']):
                    data = orgData.head(i)
                    refCandle = data.tail(1)
                    if (len(data.High[data.High > refCandle.High.item()]) == 0) and (len(data.Low[data.Low < refCandle.Low.item()]) == 0) and (len(data.Open[data.Open > refCandle.High.item()]) == 0) and (len(data.Close[data.Close < refCandle.Low.item()]) == 0):
                        screenDict['Pattern'] = colorText.BOLD + colorText.WARN + ("Inside Bar (%d)" % i) + colorText.END
                        saveDict['Pattern'] = "Inside Bar (%d)" % i
                        return i
                else:
                    return 0
        return 0
    
    # Validate if recent volume is lowest of last 'N' Days
    def validateLowestVolume(self, data, daysForLowestVolume):
        data = data.fillna(0)
        data = data.replace([np.inf, -np.inf], 0)
        if daysForLowestVolume is None:
            daysForLowestVolume = 30
        data = data.head(daysForLowestVolume)
        recent = data.head(1)
        if((recent['Volume'][0] <= data.describe()['Volume']['min']) and recent['Volume'][0] != np.nan):
            return True
        return False

    # validate if RSI is within given range
    def validateRSI(self, data, screenDict, saveDict, minRSI, maxRSI):
        data = data.fillna(0)
        data = data.replace([np.inf, -np.inf], 0)
        rsi = int(data.head(1)['RSI'][0])
        saveDict['RSI'] = rsi
        if(rsi >= minRSI and rsi <= maxRSI) and (rsi <= 70 and rsi >= 30):
            screenDict['RSI'] = colorText.BOLD + colorText.GREEN + str(rsi) + colorText.END
            return True
        screenDict['RSI'] = colorText.BOLD + colorText.FAIL + str(rsi) + colorText.END
        return False

    # Find out trend for days to lookback
    def findTrend(self, data, screenDict, saveDict, daysToLookback=None,stockName=""):
        if daysToLookback is None:
            daysToLookback = self.configManager.daysToLookback
        data = data.head(daysToLookback)
        data = data[::-1]
        data = data.set_index(np.arange(len(data)))
        data = data.fillna(0)
        data = data.replace([np.inf, -np.inf], 0)
        with SuppressOutput(suppress_stdout=True,suppress_stderr=True):
            data['tops'] = data['Close'].iloc[list(argrelextrema(np.array(data['Close']), np.greater_equal, order=1)[0])]
        data = data.fillna(0)
        data = data.replace([np.inf, -np.inf], 0)
        try:
            try:
                if len(data) < daysToLookback:
                    raise StockDataNotAdequate
                slope,c = np.polyfit(data.index[data.tops > 0], data['tops'][data.tops > 0], 1)
            except Exception as e:
                slope,c = 0,0
            angle = np.rad2deg(np.arctan(slope))
            if (angle == 0):
                screenDict['Trend'] = colorText.BOLD + "Unknown" + colorText.END
                saveDict['Trend'] = 'Unknown'
            elif (angle <= 30 and angle >= -30):
                screenDict['Trend'] = colorText.BOLD + colorText.WARN + "Sideways" + colorText.END
                saveDict['Trend'] = 'Sideways'
            elif (angle >= 30 and angle < 61):
                screenDict['Trend'] = colorText.BOLD + colorText.GREEN + "Weak Up" + colorText.END
                saveDict['Trend'] = 'Weak Up'
            elif angle >= 60:
                screenDict['Trend'] = colorText.BOLD + colorText.GREEN + "Strong Up" + colorText.END
                saveDict['Trend'] = 'Strong Up'
            elif (angle >= -30 and angle < -61):
                screenDict['Trend'] = colorText.BOLD + colorText.FAIL + "Weak Down" + colorText.END
                saveDict['Trend'] = 'Weak Down'
            elif angle <= -60:
                screenDict['Trend'] = colorText.BOLD + colorText.FAIL + "Strong Down" + colorText.END
                saveDict['Trend'] = 'Strong Down'
        except np.linalg.LinAlgError:
            screenDict['Trend'] = colorText.BOLD + "Unknown" + colorText.END
            saveDict['Trend'] = 'Unknown'
        return saveDict['Trend']

    # Find if stock gaining bullish momentum
    def validateMomentum(self, data, screenDict, saveDict):
        try:
            data = data.head(3)
            for row in data.iterrows():
                # All 3 candles should be Green and NOT Circuits
                if row[1]['Close'].item() <= row[1]['Open'].item():
                    return False
            openDesc = data.sort_values(by=['Open'], ascending=False)
            closeDesc = data.sort_values(by=['Close'], ascending=False)
            volDesc = data.sort_values(by=['Volume'], ascending=False)
            try:
                if data.equals(openDesc) and data.equals(closeDesc) and data.equals(volDesc):
                    if (data['Open'][0].item() >= data['Close'][1].item()) and (data['Open'][1].item() >= data['Close'][2].item()):
                        screenDict['Pattern'] = colorText.BOLD + colorText.GREEN + 'Momentum Gainer' + colorText.END
                        saveDict['Pattern'] = 'Momentum Gainer'
                        return True
            except IndexError:
                pass
            return False
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False

    '''
    # Find out trend for days to lookback
    def validateVCP(data, screenDict, saveDict, daysToLookback=ConfigManager.daysToLookback, stockName=None):
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
    
