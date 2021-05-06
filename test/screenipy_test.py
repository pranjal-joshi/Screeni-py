'''
 *  Project             :   Screenipy
 *  Author              :   Pranjal Joshi
 *  Created             :   29/04/2021
 *  Description         :   Automated Test Script for Screenipy
'''

import pytest
import sys
import os
import numpy as np
import pandas as pd
import configparser
import requests
import json
import platform

sys.path.append(os.path.abspath('../src'))
from screenipy import *
import classes.ConfigManager as ConfigManager

last_release = 0


def test_if_release_version_increamented():
    global last_release
    r = requests.get("https://api.github.com/repos/pranjal-joshi/Screeni-py/releases/latest")
    last_release = float(r.json()['tag_name'])
    assert float(VERSION) > last_release

# Generate default configuration if not exist
def test_generate_default_config(mocker, capsys):
    mocker.patch('builtins.input',side_effect=['\n'])
    with pytest.raises(SystemExit):
        ConfigManager.tools.setConfig(ConfigManager.parser,default=True)
    out, err = capsys.readouterr()
    assert err == ''

def test_option_0(mocker):
    try:
        mocker.patch('builtins.input',side_effect=['0', TEST_STKCODE,'y'])
        main(testing=True)
        assert len(screenResults) == 1
    except StopIteration:
        pass

def test_option_1(mocker):
    try:
        mocker.patch('builtins.input',side_effect=['1','y'])
        main(testing=True)
        assert len(screenResults) > 0
    except StopIteration:
        pass

def test_option_2(mocker):
    try:
        mocker.patch('builtins.input',side_effect=['2','y'])
        main(testing=True)
        assert len(screenResults) > 0
    except StopIteration:
        pass

def test_option_3(mocker):
    try:
        mocker.patch('builtins.input',side_effect=['3','y'])
        main(testing=True)
        assert len(screenResults) > 0
    except StopIteration:
        pass

def test_option_4(mocker):
    try:
        mocker.patch('builtins.input',side_effect=['4','7','y'])
        main(testing=True)
        assert len(screenResults) > 0
    except StopIteration:
        pass

def test_option_5(mocker):
    try:
        mocker.patch('builtins.input',side_effect=['5','30','70'])
        main(testing=True)
        assert len(screenResults) > 0
    except StopIteration:
        pass

def test_option_6(mocker):
    try:
        mocker.patch('builtins.input',side_effect=['6','1','y'])
        main(testing=True)
        assert len(screenResults) > 0
    except StopIteration:
        pass

def test_option_7(mocker, capsys):
    try:
        mocker.patch('builtins.input',side_effect=[
            '7',
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

def test_option_8():
    ConfigManager.tools.getConfig(ConfigManager.parser)
    assert ConfigManager.duration != None
    assert ConfigManager.period != None
    assert ConfigManager.consolidationPercentage != None

def test_option_9(mocker):
    try:
        mocker.patch('builtins.input',side_effect=['9'])
        main(testing=True)
        assert len(screenResults) > 0
    except StopIteration:
        pass

def test_option_11(mocker, capsys):
    try:
        mocker.patch('builtins.input',side_effect=['11'])
        with pytest.raises(SystemExit):
            main(testing=True)
        out, err = capsys.readouterr()
        assert err == ''
    except StopIteration:
        pass

def test_ota_updater():
    try:
        OTAUpdater.checkForUpdate(proxyServer, VERSION)
        assert ("exe" in OTAUpdater.checkForUpdate.url or "bin" in OTAUpdater.checkForUpdate.url)
    except StopIteration:
        pass

def test_release_readme_urls():
    global last_release
    f = open('../src/release.md','r')
    contents = f.read()
    f.close()
    failUrl = [f"https://github.com/pranjal-joshi/Screeni-py/releases/download/{last_release}/screenipy.bin", f"https://github.com/pranjal-joshi/Screeni-py/releases/download/{last_release}/screenipy.exe"]
    passUrl = [f"https://github.com/pranjal-joshi/Screeni-py/releases/download/{VERSION}/screenipy.bin", f"https://github.com/pranjal-joshi/Screeni-py/releases/download/{VERSION}/screenipy.exe"]
    for url in failUrl:
        assert not url in contents
    for url in passUrl:
        assert url in contents

def test_delete_xlsx():
    if platform.platform() == 'Windows':
        os.system("del *.xlsx")
    else:
        os.system("rm *.xlsx")