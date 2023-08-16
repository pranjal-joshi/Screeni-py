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
# import talib
import joblib
import keras
import classes.Utility as Utility
from sklearn.preprocessing import StandardScaler
from scipy.signal import argrelextrema
from scipy.stats import linregress
from classes.ColorText import colorText
from classes.SuppressOutput import SuppressOutput
from classes.ScreenipyTA import ScreenerTA


# Exception for newly listed stocks with candle nos < daysToLookback
class StockDataNotAdequate(Exception):
    pass

# Exception for only downloading stock data and not screening
class DownloadDataOnly(Exception):
    pass

# Exception for stocks which are not newly listed when screening only for Newly Listed
class NotNewlyListed(Exception):
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
            sma = ScreenerTA.EMA(data['Close'],timeperiod=50)
            lma = ScreenerTA.EMA(data['Close'],timeperiod=200)
            data.insert(6,'SMA',sma)
            data.insert(7,'LMA',lma)
        else:
            sma = data.rolling(window=50).mean()
            lma = data.rolling(window=200).mean()
            data.insert(6,'SMA',sma['Close'])
            data.insert(7,'LMA',lma['Close'])
        vol = data.rolling(window=20).mean()
        rsi = ScreenerTA.RSI(data['Close'], timeperiod=14)
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

        pct_change = (data[::-1]['Close'].pct_change() * 100).iloc[-1]
        if pct_change > 0.2:
            pct_change = colorText.GREEN + (" (%.1f%%)" % pct_change) + colorText.END
        elif pct_change < -0.2:
            pct_change = colorText.FAIL + (" (%.1f%%)" % pct_change) + colorText.END
        else:
            pct_change = colorText.WARN + (" (%.1f%%)" % pct_change) + colorText.END
            
        ltp = round(recent['Close'][0],2)
        saveDict['LTP'] = str(ltp)
        verifyStageTwo = True
        if self.configManager.stageTwo and len(data) > 250:
            yearlyLow = data.head(250).min()['Close']
            yearlyHigh = data.head(250).max()['Close']
            if ltp < (2 * yearlyLow) or ltp < (0.75 * yearlyHigh):
                verifyStageTwo = False
        if(ltp >= minLTP and ltp <= maxLTP and verifyStageTwo):
            screenDict['LTP'] = colorText.GREEN + ("%.2f" % ltp) + pct_change + colorText.END
            return True
        screenDict['LTP'] = colorText.FAIL + ("%.2f" % ltp) + pct_change + colorText.END
        return False

    # Validate if share prices are consolidating
    def validateConsolidation(self, data, screenDict, saveDict, percentage=10):
        data = data.fillna(0)
        data = data.replace([np.inf, -np.inf], 0)
        hc = data.describe()['Close']['max']
        lc = data.describe()['Close']['min']
        if ((hc - lc) <= (hc*percentage/100) and (hc - lc != 0)):
            screenDict['Consolidating'] = colorText.BOLD + colorText.GREEN + "Range = " + str(round((abs((hc-lc)/hc)*100),1))+"%" + colorText.END
        else:
            screenDict['Consolidating'] = colorText.BOLD + colorText.FAIL + "Range = " + str(round((abs((hc-lc)/hc)*100),1)) + "%" + colorText.END
        saveDict['Consolidating'] = str(round((abs((hc-lc)/hc)*100),1))+"%"
        return round((abs((hc-lc)/hc)*100),1)

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
        elif(recent['SMA'][0] == 0):
            screenDict['MA-Signal'] = colorText.BOLD + colorText.WARN + 'Unknown' + colorText.END
            saveDict['MA-Signal'] = 'Unknown'
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
            saveDict['Volume'] = "Unknown"
            screenDict['Volume'] = colorText.BOLD + colorText.WARN + "Unknown" + colorText.END
            return True
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
        if np.isnan(hc) or np.isnan(hs):
            saveDict['Breaking-Out'] = 'BO: Unknown'
            screenDict['Breaking-Out'] = colorText.BOLD + colorText.WARN + 'BO: Unknown' + colorText.END
            return False
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
    def validateInsideBar(self, data, screenDict, saveDict, chartPattern=1, daysToLookback=5):
        orgData = data
        for i in range(daysToLookback, round(daysToLookback*0.5)-1, -1):
            if i == 2:
                return 0        # Exit if only last 2 candles are left
            if chartPattern == 1:
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
                screenDict['Trend'] = colorText.BOLD + colorText.WARN + "Unknown" + colorText.END
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
            elif (angle <= -30 and angle > -61):
                screenDict['Trend'] = colorText.BOLD + colorText.FAIL + "Weak Down" + colorText.END
                saveDict['Trend'] = 'Weak Down'
            elif angle <= -60:
                screenDict['Trend'] = colorText.BOLD + colorText.FAIL + "Strong Down" + colorText.END
                saveDict['Trend'] = 'Strong Down'
        except np.linalg.LinAlgError:
            screenDict['Trend'] = colorText.BOLD + colorText.WARN + "Unknown" + colorText.END
            saveDict['Trend'] = 'Unknown'
        return saveDict['Trend']

    # Find if stock is validating volume spread analysis
    def validateVolumeSpreadAnalysis(self, data, screenDict, saveDict):
        try:
            data = data.head(2)
            try:
                # Check for previous RED candles
                # Current candle = 0th, Previous Candle = 1st for following logic
                if data.iloc[1]['Open'] >= data.iloc[1]['Close']:
                    spread1 = abs(data.iloc[1]['Open'] - data.iloc[1]['Close'])
                    spread0 = abs(data.iloc[0]['Open'] - data.iloc[0]['Close'])
                    lower_wick_spread0 = max(data.iloc[0]['Open'], data.iloc[0]['Close']) - data.iloc[0]['Low']
                    vol1 = data.iloc[1]['Volume']
                    vol0 = data.iloc[0]['Volume']
                    if spread0 > spread1 and vol0 < vol1 and data.iloc[0]['Volume'] < data.iloc[0]['VolMA'] and data.iloc[0]['Close'] <= data.iloc[1]['Open'] and spread0 < lower_wick_spread0 and data.iloc[0]['Volume'] <= int(data.iloc[1]['Volume']*0.75):
                        screenDict['Pattern'] = colorText.BOLD + colorText.GREEN + 'Supply Drought' + colorText.END
                        saveDict['Pattern'] = 'Supply Drought'
                        return True
                    if spread0 < spread1 and vol0 > vol1 and data.iloc[0]['Volume'] > data.iloc[0]['VolMA'] and data.iloc[0]['Close'] <= data.iloc[1]['Open']:
                        screenDict['Pattern'] = colorText.BOLD + colorText.GREEN + 'Demand Rise' + colorText.END
                        saveDict['Pattern'] = 'Demand Rise'
                        return True
            except IndexError:
                pass
            return False
        except:
            import traceback
            traceback.print_exc()
            return False

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

    # Find stock reversing at given MA
    def findReversalMA(self, data, screenDict, saveDict, maLength, percentage=0.015):
        if maLength is None:
            maLength = 20
        data = data[::-1]
        if self.configManager.useEMA:
            maRev = ScreenerTA.EMA(data['Close'],timeperiod=maLength)
        else:
            maRev = ScreenerTA.MA(data['Close'],timeperiod=maLength)
        data.insert(10,'maRev',maRev)
        data = data[::-1].head(3)
        if data.equals(data[(data.Close >= (data.maRev - (data.maRev*percentage))) & (data.Close <= (data.maRev + (data.maRev*percentage)))]) and data.head(1)['Close'][0] >= data.head(1)['maRev'][0]:
            screenDict['MA-Signal'] = colorText.BOLD + colorText.GREEN + f'Reversal-{maLength}MA' + colorText.END
            saveDict['MA-Signal'] = f'Reversal-{maLength}MA'
            return True
        return False

    # Find IPO base
    def validateIpoBase(self, stock, data, screenDict, saveDict, percentage=0.3):
        listingPrice = data[::-1].head(1)['Open'][0]
        currentPrice = data.head(1)['Close'][0]
        ATH = data.describe()['High']['max']
        if ATH > (listingPrice + (listingPrice * percentage)):
            return False
        away = round(((currentPrice - listingPrice)/listingPrice)*100, 1)
        if((listingPrice - (listingPrice * percentage)) <= currentPrice <= (listingPrice + (listingPrice * percentage))):
            if away > 0:
                screenDict['Pattern'] = colorText.BOLD + colorText.GREEN + f'IPO Base ({away} %)' + colorText.END
            else:
                screenDict['Pattern'] = colorText.BOLD + colorText.GREEN + 'IPO Base ' + colorText.FAIL + f'({away} %)' + colorText.END
            saveDict['Pattern'] = f'IPO Base ({away} %)'
            return True
        return False

    # Find Conflucence
    def validateConfluence(self, stock, data, screenDict, saveDict, percentage=0.1):
        recent = data.head(1)
        if(abs(recent['SMA'][0] - recent['LMA'][0]) <= (recent['SMA'][0] * percentage)):
            difference = round(abs(recent['SMA'][0] - recent['LMA'][0])/recent['Close'][0] * 100,2)
            if recent['SMA'][0] >= recent['LMA'][0]:
                screenDict['MA-Signal'] = colorText.BOLD + colorText.GREEN + f'Confluence ({difference}%)' + colorText.END
                saveDict['MA-Signal'] = f'Confluence ({difference}%)'
            else:
                screenDict['MA-Signal'] = colorText.BOLD + colorText.FAIL + f'Confluence ({difference}%)' + colorText.END
                saveDict['MA-Signal'] = f'Confluence ({difference}%)'
            return True
        return False

    # Find if stock is newly listed
    def validateNewlyListed(self, data, daysToLookback):
        daysToLookback = int(daysToLookback[:-1])
        recent = data.head(1)
        if len(data) < daysToLookback and (recent['Close'][0] != np.nan and recent['Close'][0] > 0):
            return True
        return False

    # Find stocks approching to long term trendlines
    def findTrendlines(self, data, screenDict, saveDict, percentage = 0.05):
        period = int(''.join(c for c in self.configManager.period if c.isdigit()))
        if len(data) < period:
            return False

        data = data[::-1]
        data['Number'] = np.arange(len(data))+1
        data_high = data.copy()
        data_low = data.copy()
        points = 30

        ''' Ignoring the Resitance for long-term purpose
        while len(data_high) > points:
            slope, intercept, r_value, p_value, std_err = linregress(x=data_high['Number'], y=data_high['High'])
            data_high = data_high.loc[data_high['High'] > slope * data_high['Number'] + intercept]
        slope, intercept, r_value, p_value, std_err = linregress(x=data_high['Number'], y=data_high['Close'])
        data['Resistance'] = slope * data['Number'] + intercept
        '''

        while len(data_low) > points:
            slope, intercept, r_value, p_value, std_err = linregress(x=data_low['Number'], y=data_low['Low'])
            data_low = data_low.loc[data_low['Low'] < slope * data_low['Number'] + intercept]
        
        slope, intercept, r_value, p_value, std_err = linregress(x=data_low['Number'], y=data_low['Close'])
        data['Support'] = slope * data['Number'] + intercept
        now = data.tail(1)

        limit_upper = now['Support'][0].item() + (now['Support'][0].item() * percentage)
        limit_lower = now['Support'][0].item() - (now['Support'][0].item() * percentage)

        if limit_lower < now['Close'][0].item() < limit_upper and slope > 0.15:
            screenDict['Pattern'] = colorText.BOLD + colorText.GREEN + 'Trendline-Support' + colorText.END
            saveDict['Pattern'] = 'Trendline-Support'
            return True

        ''' Plots for debugging
        import matplotlib.pyplot as plt
        fig, ax1 = plt.subplots(figsize=(15,10))
        color = 'tab:green'
        xdate = [x.date() for x in data.index]
        ax1.set_xlabel('Date', color=color)
        ax1.plot(xdate, data.Close, label="close", color=color)
        ax1.tick_params(axis='x', labelcolor=color)

        ax2 = ax1.twiny() # ax2 and ax1 will have common y axis and different x axis, twiny
        ax2.plot(data.Number, data.Resistance, label="Res")
        ax2.plot(data.Number, data.Support, label="Sup")

        plt.legend()
        plt.grid()
        plt.show()
        '''
        return False


    # Find NRx range for Reversal
    def validateNarrowRange(self, data, screenDict, saveDict, nr=4):
        if Utility.tools.isTradingTime():
            rangeData = data.head(nr+1)[1:]
            now_candle = data.head(1)
            rangeData['Range'] = abs(rangeData['Close'] - rangeData['Open'])
            recent = rangeData.head(1)
            if recent['Range'][0] == rangeData.describe()['Range']['min']:
                if self.getCandleType(recent) and now_candle['Close'][0] >= recent['Close'][0]:
                    screenDict['Pattern'] = colorText.BOLD + colorText.GREEN + f'Buy-NR{nr}' + colorText.END
                    saveDict['Pattern'] = f'Buy-NR{nr}'
                    return True
                elif not self.getCandleType(recent) and now_candle['Close'][0] <= recent['Close'][0]:
                    screenDict['Pattern'] = colorText.BOLD + colorText.FAIL + f'Sell-NR{nr}' + colorText.END
                    saveDict['Pattern'] = f'Sell-NR{nr}'
                    return True
            return False
        else:
            rangeData = data.head(nr)
            rangeData['Range'] = abs(rangeData['Close'] - rangeData['Open'])
            recent = rangeData.head(1)
            if recent['Range'][0] == rangeData.describe()['Range']['min']:
                screenDict['Pattern'] = colorText.BOLD + colorText.GREEN + f'NR{nr}' + colorText.END
                saveDict['Pattern'] = f'NR{nr}'
                return True
            return False

    # Validate VPC
    def validateVCP(self, data, screenDict, saveDict, stockName=None, window=3, percentageFromTop=3):
        try:
            percentageFromTop /= 100
            data.reset_index(inplace=True)
            data.rename(columns={'index':'Date'}, inplace=True)
            data['tops'] = data['High'].iloc[list(argrelextrema(np.array(data['High']), np.greater_equal, order=window)[0])].head(4)
            data['bots'] = data['Low'].iloc[list(argrelextrema(np.array(data['Low']), np.less_equal, order=window)[0])].head(4)
            data = data.fillna(0)
            data = data.replace([np.inf, -np.inf], 0)
            tops = data[data.tops > 0]
            bots = data[data.bots > 0]
            highestTop = round(tops.describe()['High']['max'],1)
            filteredTops = tops[tops.tops > (highestTop-(highestTop*percentageFromTop))]
            # print(tops)
            # print(filteredTops)
            # print(tops.sort_values(by=['tops'], ascending=False))
            # print(tops.describe())
            # print(f"Till {highestTop-(highestTop*percentageFromTop)}")
            if(filteredTops.equals(tops)):      # Tops are in the range
                lowPoints = []
                for i in range(len(tops)-1):
                    endDate = tops.iloc[i]['Date']
                    startDate = tops.iloc[i+1]['Date']
                    lowPoints.append(data[(data.Date >= startDate) & (data.Date <= endDate)].describe()['Low']['min'])
                lowPointsOrg = lowPoints
                lowPoints.sort(reverse=True)
                lowPointsSorted = lowPoints
                ltp = data.head(1)['Close'][0]
                if lowPointsOrg == lowPointsSorted and  ltp < highestTop and ltp > lowPoints[0]:
                    screenDict['Pattern'] = colorText.BOLD + colorText.GREEN + f'VCP (BO: {highestTop})' + colorText.END
                    saveDict['Pattern'] = f'VCP (BO: {highestTop})'
                    return True
        except Exception as e:
            import traceback
            print(traceback.format_exc())
        return False

    def getNiftyPrediction(self, data, proxyServer):
        import warnings 
        warnings.filterwarnings("ignore")
        model, pkl = Utility.tools.getNiftyModel(proxyServer=proxyServer)
        with SuppressOutput(suppress_stderr=True, suppress_stdout=True):
            data = data[pkl['columns']]
            ### v2 Preprocessing
            data['High'] = data['High'].pct_change() * 100
            data['Low'] = data['Low'].pct_change() * 100
            data['Open'] = data['Open'].pct_change() * 100
            data['Close'] = data['Close'].pct_change() * 100
            data = data.iloc[-1] 
            ###
            data = pkl['scaler'].transform([data])
            pred = model.predict(data)[0]
        if pred > 0.5:
            out = colorText.BOLD + colorText.FAIL + "BEARISH" + colorText.END + colorText.BOLD
            sug = "Hold your Short position!"
        else:
            out = colorText.BOLD + colorText.GREEN + "BULLISH" + colorText.END + colorText.BOLD
            sug = "Stay Bullish!"
        if not Utility.tools.isClosingHour():
            print(colorText.BOLD + colorText.WARN + "Note: The AI prediction should be executed After 3 PM or Near to Closing time as the Prediction Accuracy is based on the Closing price!" + colorText.END)
        print(colorText.BOLD + colorText.BLUE + "\n" + "[+] Nifty AI Prediction -> " + colorText.END + colorText.BOLD + "Market may Open {} next day! {}".format(out, sug) + colorText.END)
        print(colorText.BOLD + colorText.BLUE + "\n" + "[+] Nifty AI Prediction -> " + colorText.END + "Probability/Strength of Prediction = {}%".format(Utility.tools.getSigmoidConfidence(pred[0])))
        return pred

    def monitorFiveEma(self, proxyServer, fetcher, result_df, last_signal, risk_reward = 3):
        col_names = ['High', 'Low', 'Close', '5EMA']
        data_list = ['nifty_buy', 'banknifty_buy', 'nifty_sell', 'banknifty_sell']

        data_tuple = fetcher.fetchFiveEmaData()
        for cnt in range(len(data_tuple)):
            d = data_tuple[cnt]
            d['5EMA'] = ScreenerTA.EMA(d['Close'],timeperiod=5)
            d = d[col_names]
            d = d.dropna().round(2)

            with SuppressOutput(suppress_stderr=True, suppress_stdout=True):
                if 'sell' in data_list[cnt]:
                    streched = d[(d.Low > d['5EMA']) & (d.Low - d['5EMA'] > 0.5)]
                    streched['SL'] = streched.High
                    validate = d[(d.Low.shift(1) > d['5EMA'].shift(1)) & (d.Low.shift(1) - d['5EMA'].shift(1) > 0.5)]
                    old_index = validate.index
                else:
                    mask = (d.High < d['5EMA']) & (d['5EMA'] - d.High > 0.5)  # Buy
                    streched = d[mask]
                    streched['SL'] = streched.Low
                    validate = d.loc[mask.shift(1).fillna(False)]
                    old_index = validate.index
            tgt = pd.DataFrame((validate.Close.reset_index(drop=True) - ((streched.SL.reset_index(drop=True) - validate.Close.reset_index(drop=True)) * risk_reward)),columns=['Target'])
            validate = pd.concat([
                            validate.reset_index(drop=True),
                            streched['SL'].reset_index(drop=True),
                            tgt,
                            ],
                        axis=1
                        )
            validate = validate.tail(len(old_index))
            validate = validate.set_index(old_index)
            if 'sell' in data_list[cnt]:
                final = validate[validate.Close < validate['5EMA']].tail(1)
            else:
                final = validate[validate.Close > validate['5EMA']].tail(1)


            if data_list[cnt] not in last_signal:
                last_signal[data_list[cnt]] = final
            elif data_list[cnt] in last_signal:
                try:
                    condition = last_signal[data_list[cnt]][0]['SL'][0]
                except KeyError:
                    condition = last_signal[data_list[cnt]]['SL'][0]
                # if last_signal[data_list[cnt]] is not final:          # Debug - Shows all conditions
                if condition != final['SL'][0]:
                    # Do something with results
                    try:
                        result_df = pd.concat([
                            result_df, 
                            pd.DataFrame([
                                    [
                                        colorText.BLUE + str(final.index[0]) + colorText.END,
                                        colorText.BOLD + colorText.WARN + data_list[cnt].split('_')[0].upper() + colorText.END,
                                        (colorText.BOLD + colorText.FAIL + data_list[cnt].split('_')[1].upper() + colorText.END) if 'sell' in data_list[cnt] else (colorText.BOLD + colorText.GREEN + data_list[cnt].split('_')[1].upper() + colorText.END),
                                        colorText.FAIL + str(final.SL[0]) + colorText.END,
                                        colorText.GREEN + str(final.Target[0]) + colorText.END,
                                        f'1:{risk_reward}'
                                    ]
                                ], columns=result_df.columns)
                            ], axis=0)
                        result_df.reset_index(drop=True, inplace=True)
                    except Exception as e:
                        pass
                    # Then update
                    last_signal[data_list[cnt]] = [final]
        result_df.drop_duplicates(keep='last', inplace=True)
        result_df.sort_values(by='Time', inplace=True)
        return result_df[::-1]
            

    '''
    # Find out trend for days to lookback
    def validateVCP(data, screenDict, saveDict, daysToLookback=ConfigManager.daysToLookback, stockName=None):
        // De-index date
        data.reset_index(inplace=True)
        data.rename(columns={'index':'Date'}, inplace=True)
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
    
