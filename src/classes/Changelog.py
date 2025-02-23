'''
 *  Project             :   Screenipy
 *  Author              :   Pranjal Joshi
 *  Created             :   28/04/2021
 *  Description         :   Class for maintaining changelog
'''

from classes.ColorText import colorText

VERSION = "2.26"

changelog = colorText.BOLD + '[ChangeLog]\n' + colorText.END + colorText.BLUE + '''
[1.00 - Beta]
1. Initial Release for beta testing
2. Minor Bug fixes

[1.01]
1. Inside Bar detection added.
2. OTA Software Update Implemented.
3. Stock shuffling added while screening
4. Results will be now also stored in the excel (screenipy-result.xlsx) file.
5. UI cosmetic updates for pretty-printing!

[1.02]
1. Feature added to screen only STAGE-2 stocks.
2. OTA update download bug-fixed.
3. Auto generate default config if not found.
4. Minor bug-fixes.

[1.03]
1. Result excel file will not be overwritten now. Each result file will be saved with timestamp.
2. Candlestick pattern recognition added.

[1.04]
1. OTA Software Update bug-fixed.
2. Minor Improvements.

[1.05]
1. More candlestick pattern added for recognition.
2. Option added to find stock with lowest volume in last 'N'-days to early detect possibility of breakout.
3. Last screened results will be stored and can be viewed with Option > 7.
4. Minor Bug-fixes and improvements.

[1.06]
1. Option > 0 added - Screen stocks by enterning it's name (stock code).
2. Stability fixes and improvements.
3. Last screened results will be stored and can be viewed with Option > 7.

[1.07]
1. Program Window will not automatically close now.
2. Bug fixes and improvements.

[1.08]
1. Prompt added for saving excel after screening.
2. Program back-end architecture updated.

[1.09]
1. RSI based screening added as Option > 5.
2. Minor Performance Improvements.

[1.10]
1. Trend detection for the timeframe of analysis added.

[1.11]
1. Option-6 -> Screen for stocks showing Reversal Signal added
2. Stage-2 Screening logic improved for identifying best stocks only.
3. Trend detection has been improved.
4. Bugs and Runtime warnings fixed.

[1.12]
1. MA now gives more info like Candle Crossing and At Support/Resistance.
2. More Patterns added for Reversal Detection.
4. Trend detection enhanced for the timeframe of analysis.
5. Runtime Warnings have been fixed.

[1.13]
1. Chart Pattern Detection added. Option > 7
2. Screen for Inside Bar Chart pattern.
3. Documentation updated and Performance fixes.

[1.14][1.15]
1. Screening stocks with parallel processing using all cores available in machine. (Thanks to @swarpatel23)
2. Minor Bug-fixes and Improvements.

[1.16]
1. Bullish Momentum Finder added. Option > 6 > 3
2. Stock Data Caching added. (Thanks to @swarpatel23)
3. Codefactoring Improved.
4. Ctrl+C crash fixed.

[1.17]
1. Breakout detection improved.
2. Progressbar added.
3. Watchlist creation in Excel file and its screening.

[1.18]
1. Cache and Performance fixes.
2. Breakout Calculation Enhanced.

[1.19]
1. New Feature: Search for Bullish Reversal at MA. Option > 6 > 4

[1.20]
1. Screen stocks as per your favorite index. (Thanks to @swarpatel23)

[1.21]
1. TradingView Hyperlink added for stock symbol.

[1.22]
1. Broken yfinance API fixed.

[1.23]
1. Bug fixed for DualCore CPU.
2. Dependencies updated.

[1.24]
1. IPO Base Breakout pattern added. Option > 7 > 3.
2. Data fetching interval fixed.
3. Permission bug-fixes for some windows users.
4. Result table optimized.

[1.25]
1. Default configuration parameters optimized.
2. Configuration generation on first time usage don't need restart anymore!
3. Minor bug-fixes.

[1.26]
1. New Feature: Screen for the MA Confluence pattern Option > 7 > 4.

[1.27]
1. Display more information about an update when it is available.
2. Minor Fixes (MA Confluence).

[1.28]
1. Volume Spread Analysis added for Bullish Reversals. Option > 6 > 5

[1.29]
1. VSA screening optimized.
2. Error handling and timeout optimized.
3. Build Test mode added for CI/CD.

[1.30]
1. New Tickers Group - Screen only for Newly Listed IPOs (Last 1 Yr)
2. Major bug fix - stage 2 criteria won't be applied for new listings.
3. Validation Fixed for Volume & MA Signal (Optimized for new listings)
4. Excel save header name bug fixed.

[1.31]
1. BugFixes for false detection of patterns - IPO Base, Inside Bar.
2. New Application Icon.
3. Experimental - VCP Detection : Option > 7 > 4

[1.32]
1. Performance Optimization.
2. Minor Improvements.
3. Argument added for Data download only : run screenipy.exe -d

[1.33]
1. Alternate Data source added.
2. Workflow added to create cache data on cloud.

[1.34]
1. New Reversal - Narrow Range : Try Option 6 > 6
2. Cache loading fixes for Pre-Market timings. Refer PR #103
3. Progressbar added for Alternate Source Cache Download.

[1.35]
1. Separate Algorithms for NR depending on Live/After-Market hours.
2. NRx results fixed in Momentum Gainer Screening.

[1.36]
1. Updated CSV URLs to New NSE Site. (#113)

[1.37]
1. New Chart Pattern -> Buy at Trendline : Try Option 7 > 5

[1.38]
1. Added AI based predictions for Nifty closing on next day : Select Index for Screening > N

[1.39]
1. Intraday Live Scanner - 5 EMA for Indices : Try Option `E`

[1.40]
1. Nifty AI Prediction - Model Accuracy Enhanced by new preprocessing - Better Gap predictions

[1.41]
1. Fetching of Stock Codes list fixed after NSE migration to newer website - Not using `nsetools` anymore

[1.42]
1. Down trend detection bug fixed
2. % Change added with LTP

[1.43]
1. New Index added - F&O Only stocks

[1.44]
1. Migrated ta-lib dependency to pandas_ta

[1.45]
1. Minor bug fixes after dependency change

[1.46]
1. TA-Lib reanabled. Dockerized for better distribution of the tool


[2.00]
1. Streamlit UI (WebApp) added
2. Multi-Arch Docker support enabled

[2.01]
1. Docker build fixed - Versioning critical bug fixed for further OTA updates

[2.02]
1. Newly Listed (IPO) index critical bug fixed
2. OTA Updates fixed for GUI
3. Cosmetic improvements
4. YouTube Video added to docs

[2.03]
1. AI based Nifty-50 Gap up/down prediction added to GUI
2. Cosmetic updates and minor bug-fixes
3. Search Similar Stock Added
4. Executables Deprecated now onwards

[2.04]
1. OTA update fixed - caching added in GUI
2. Moved to TA-Lib-Precompiled (0.4.25)
3. Progressbar added for screening to GUI
4. Documentation updated

[2.05]
1. Download Results button added
2. Configuration save bug fixed for checkboxes
3. Attempted to changed Docker DNS


[2.06]
1. Links added with cosmetic upgrade
2. Docs updated

[2.07]
1. US S&P 500 Index added - Try Index `15 > US S&P 500`
2. Minor improvemnets

[2.08]
1. Nifty Prediction enhanced - New AI model uses Crude and Gold data for Gap Prediction

[2.09]
1. Dependencies bumped to pandas-2.1.2 scikit-learn-1.3.2 for (pip install advanced-ta) compatibility
2. Added Lorentzian Classifier based screening criteria - Try Option `6 > Reversal signals and 7 > Lorentzian Classification` (Extending Gratitude towards Justin Dehorty and Loki Arya for Open-Sourcing this one ❤️)
3. MA-Confluence bug fixed

[2.10]
1. Position Size Calculator added as a new tab

[2.11]
1. Nifty Prediction issue fixed - Model is now trained on CPU instead of Apple-M1 GPU

[2.12]
1. Cosmetic Updates for Position Size Calculator
2. Python base bumped to 3.11.6-slim-bookworm

[2.13]
1. Date based Backtesting Added for Screening
2. Inside bar detection broken - bug fixed
3. Auto enhanced debug on console in dev release

[2.14]
1. Dropdowns added for duration and period in configration tab

[2.15]
1. MA Reversal improved for trend following (Inspired from Siddhart Bhanushali's 44 SMA)

[2.16]
1. Nifty Prediction NaN values handled gracefully with forward filling if data is absent
2. Ticker 0 > Search by Stock name - re-enabled in GUI

[2.17]
1. Backtest Report column added for backtest screening runs

[2.18]
1. Critical backtest bug fixed (dropna axis-1 removed from results)
2. Clear stock cached data button added

[2.19]
1. New Index (Group of Indices) `16 > Sectoral Indices` added

[2.20]
1. Bugfixes - Clear cache button random key added to fix re-rendering issues

[2.21]
1. Dependency updated - `advanced-ta` lib for bugfixes and performance improvement in Lorentzian Classifier

[2.22]
1. RSI and 9 SMA of RSI based reversal added - Momentum based execution strategy.

[2.23]
1. Changed Data Source for F&O Stocks - Using Zerodha Kite instead of Broken NSE Website

[2.24]
1. Added Filters to Result Table (Special Thanks to https://github.com/koalyptus/TableFilter)

[2.25]
1. Reduced docker image size by 50% (Special Thanks to https://github.com/smitpsanghavi)

[2.26]
1. Bugfixes - yfinance package updated to 0.2.54 to fix Yahoo Finance API issue
2. Minor Improvements to maintain backward compatibility of the yfinance df
''' + colorText.END
