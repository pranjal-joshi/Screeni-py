'''
 *  Project             :   Screenipy
 *  Author              :   Pranjal Joshi
 *  Created             :   29/04/2021
 *  Description         :   Automated Test Script for Screenipy
'''

import pytest
from _pytest.monkeypatch import MonkeyPatch
import sys
import os
import numpy as np
import pandas as pd
import configparser

sys.path.append(os.path.abspath('../src'))
from screenipy import *
import classes.ConfigManager as ConfigManager

monkeypatch = MonkeyPatch()

def test_option_0(mocker):
    try:
        mocker.patch('builtins.input',side_effect=['0', TEST_STKCODE])
        main(testing=True)
        assert len(screenResults) == 1
    except StopIteration:
        pass

def test_option_1(mocker):
    try:
        mocker.patch('builtins.input',side_effect=['1'])
        main(testing=True)
        assert len(screenResults) > 0
    except StopIteration:
        pass

def test_option_2(mocker):
    try:
        mocker.patch('builtins.input',side_effect=['2'])
        main(testing=True)
        assert len(screenResults) > 0
    except StopIteration:
        pass

def test_option_3(mocker):
    try:
        mocker.patch('builtins.input',side_effect=['3'])
        main(testing=True)
        assert len(screenResults) > 0
    except StopIteration:
        pass

def test_option_4(mocker):
    try:
        mocker.patch('builtins.input',side_effect=['4','7'])
        main(testing=True)
        assert len(screenResults) > 0
    except StopIteration:
        pass

def test_option_5(mocker, capsys):
    try:
        mocker.patch('builtins.input',side_effect=[
            '5',
            str(ConfigManager.period),
            str(ConfigManager.daysToLookback),
            str(ConfigManager.duration),
            str(ConfigManager.minLTP),
            str(ConfigManager.maxLTP),
            str(ConfigManager.volumeRatio),
            str(ConfigManager.consolidationPercentage),
            'y',
            'y',
        ])
        with pytest.raises((SystemExit, configparser.DuplicateSectionError)):
            main(testing=True)
        out, err = capsys.readouterr()
        assert err == 0 or err == ''
    except StopIteration:
        pass

def test_option_6():
    ConfigManager.tools.getConfig(ConfigManager.parser)
    assert ConfigManager.duration != None
    assert ConfigManager.period != None
    assert ConfigManager.consolidationPercentage != None

def test_option_7(mocker):
    try:
        mocker.patch('builtins.input',side_effect=['7'])
        main(testing=True)
        assert len(screenResults) > 0
    except StopIteration:
        pass

def test_option_9(mocker, capsys):
    try:
        mocker.patch('builtins.input',side_effect=['9'])
        with pytest.raises(SystemExit):
            main(testing=True)
        out, err = capsys.readouterr()
        assert err == ''
    except StopIteration:
        pass

def test_ota_updater():
    try:
        OTAUpdater.checkForUpdate(proxyServer, VERSION)
        assert OTAUpdater.checkForUpdate.url != None
    except StopIteration:
        pass