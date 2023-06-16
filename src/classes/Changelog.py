'''
 *  Project             :   Screenipy
 *  Author              :   Pranjal Joshi
 *  Created             :   28/04/2021
 *  Description         :   Class for maintaining changelog
'''

from classes.ColorText import colorText

VERSION = "1.43"

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

--- END ---
''' + colorText.END
