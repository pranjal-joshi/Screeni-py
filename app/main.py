from flask import Flask, render_template, request, redirect, url_for
import sys
sys.path.insert(0, "../src/")
from screenipy import *

app = Flask(__name__)

@app.route('/')
def home():
    return "Flask Server is Working!"

@app.route('/index.html')
def index():
    return render_template('pages/index.html',msg='Screeni-py Flask Server')

@app.route('/screenipy.html',methods=['GET','POST'])
def screener():
    if request.method == 'GET':
        return render_template('pages/screenipy.html')
    else:
        return request.form

@app.route('/screenipy.html/startScreening',methods=['POST'])
def startScreening():
    global screenResults, saveResults, screeningDictionary, saveDictionary
    return tabulate(saveResults, headers='keys', tablefmt='html')
