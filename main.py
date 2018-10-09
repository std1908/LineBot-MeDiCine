# -*- coding: utf-8 -*-

from flask import Flask, request, abort
import tempfile, os,shutil
import requests
import json
from os import path
from pymongo import MongoClient
import collections
from collections import OrderedDict
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,ImageMessage,
)
from function.QRtoDB import QRtoDB
from function.remindTake import *
import config

static_tmp_path = os.path.join(os.path.dirname(__file__),'temp')

app = Flask(__name__)

line_bot_api = LineBotApi(config.LineBotApi)
handler = WebhookHandler(config.WebhookHandler)

@app.route("/callback", methods=['POST'])
def index():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=(TextMessage,ImageMessage))
def handle_message(event):
    if isinstance(event.message, TextMessage):
        pass
    elif isinstance(event.message, ImageMessage):

        #decode QR & insert into DB
        QRresault  = QRtoDB().decode_QR(line_bot_api,event) 

        #show md info
        if(QRresault != None):
            rT = remindTake(QRresault,line_bot_api,TextSendMessage,event)
            for md in QRresault['用藥']:
                QR_med_name = list(md.items())[0][1]     #QR Code掃出的藥品名稱
                QR_QTY = list(md.items())[1][1]  #QR Code掃出的藥品用量
                QR_freq= list(md.items())[2][1]   #QR Code掃出的用藥頻率 'Q1MN'#'Q2D2AC1M'
                QR_route = list(md.items())[3][1]    #QR Code掃出的給藥途徑
                rT.remind_med(QR_med_name,QR_QTY,QR_freq,QR_route)

            

if __name__ == "__main__":
    app.run(host='127.0.0.1', port= 5000)