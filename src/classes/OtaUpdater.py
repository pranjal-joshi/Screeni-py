'''
 *  Project             :   Screenipy
 *  Author              :   Pranjal Joshi
 *  Created             :   21/04/2021
 *  Description         :   Class for handling OTA updates
'''

from classes.ColorText import colorText
import requests
import os
import platform
import sys
import subprocess

class OTAUpdater:

    # Download and replace exe through other process for windows
    def updateForWindows(url):
        batFile = """@echo off
color a
echo [+] Screenipy Software Updater!
echo [+] Downloading Software Update...
echo [+] This may take some time as per your Internet Speed, Please Wait...
powershell.exe -Command (new-object System.Net.WebClient).DownloadFile('""" + url + """','screenipy.exe')
echo [+] Software Update Completed! You can now run 'Screenipy.exe' as usual!
pause
del updater.bat & exit
        """
        f = open("updater.bat",'w')
        f.write(batFile)
        f.close()
        subprocess.Popen('start updater.bat', shell=True)
        sys.exit(0)

    # Download and replace exe through other process for windows
    def updateForLinux(url):
        bashFile = """#!/bin/bash
echo ""
echo "[+] Starting Screeni-py updater, Please Wait..."
sleep 3
echo "[+] Screenipy Software Updater!"
echo "[+] Downloading Software Update..."
echo "[+] This may take some time as per your Internet Speed, Please Wait..."
wget -q """ + url + """ -O screenipy.bin
echo "[+] Update Completed!"
rm updater.sh
        """
        f = open("updater.sh",'w')
        f.write(bashFile)
        f.close()
        subprocess.Popen('bash updater.sh', shell=True)
        sys.exit(0)

    # Check for update and download if available
    def checkForUpdate(proxyServer, VERSION="1.0"):
        OTAUpdater.checkForUpdate.url = None
        try:
            resp = None
            now = float(VERSION)
            if proxyServer:
                resp = requests.get("https://api.github.com/repos/pranjal-joshi/Screeni-py/releases/latest",proxies={'https':proxyServer})
            else:
                resp = requests.get("https://api.github.com/repos/pranjal-joshi/Screeni-py/releases/latest")
            OTAUpdater.checkForUpdate.url = resp.json()['assets'][1]['browser_download_url']
            size = int(resp.json()['assets'][1]['size']/(1024*1024))
            if platform.system() != 'Windows':
                OTAUpdater.checkForUpdate.url = resp.json()['assets'][0]['browser_download_url']
                size = int(resp.json()['assets'][0]['size']/(1024*1024))
            if(float(resp.json()['tag_name']) > now):
                action = str(input(colorText.BOLD + colorText.WARN + ('\n[+] New Software update (v%s) available. Download Now (Size: %dMB)? [Y/N]: ' % (str(resp.json()['tag_name']),size)))).lower()
                if(action == 'y'):
                    try:
                        if platform.system() == 'Windows':
                            OTAUpdater.updateForWindows(OTAUpdater.checkForUpdate.url)
                        else:
                            OTAUpdater.updateForLinux(OTAUpdater.checkForUpdate.url)
                    except Exception as e:
                        print(colorText.BOLD + colorText.WARN + '[+] Error occured while updating!' + colorText.END)
                        raise(e)
                        input('')
                        sys.exit(1)
            elif(float(resp.json()['tag_name']) < now):
                print(colorText.BOLD + colorText.FAIL + ('[+] This version (v%s) is in Development mode and unreleased!' % VERSION) + colorText.END)
        except Exception as e:
            print(colorText.BOLD + colorText.FAIL + "[+] Failure while checking update!" + colorText.END)
            print(e)
            if OTAUpdater.checkForUpdate.url != None:
                print(colorText.BOLD + colorText.BLUE + ("[+] Download update manually from %s\n" % OTAUpdater.checkForUpdate.url) + colorText.END)