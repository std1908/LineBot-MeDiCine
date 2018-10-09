# -*- coding: utf-8 -*-

from flask import Flask, request, abort
import tempfile, os,shutil
import requests
import json
from os import path
from pymongo import MongoClient
import collections
from collections import OrderedDict

client = MongoClient('localhost',27017)
db = client["MeDiCine"]
collection = db["Patient-Info"]
static_tmp_path = os.path.join(os.path.dirname(__file__),'temp')

app = Flask(__name__)

class QRtoDB():

    def __init__(self):
        pass

    def decode_QR(self,line_bot_api,event):
            userId=event.source.user_id
            ext = 'jpg'
            message_content = line_bot_api.get_message_content(event.message.id)
            with tempfile.NamedTemporaryFile(dir=static_tmp_path, prefix=ext + '-', delete=False) as tf:
                for chunk in message_content.iter_content():
                    tf.write(chunk)
                tempfile_path = tf.name
            dist_path = userId+"#"+ '.' + ext
            os.rename(tempfile_path, dist_path)
            filepath = os.path.join(os.path.abspath('.'),dist_path)
            fo = open(filepath,'rb')
            file={'qrcode':fo}
            compile_url="https://zxing.org/w/decode"
            response = requests.post(compile_url,files=file)
            response.encoding='utf-8'
            head=response.text.find("<pre>")
            last=response.text.find("</pre>")
            rawBytes=response.text[head+5:last]
            fo.close()
            if(rawBytes[0:5]=="CTYPE"):
                rawBytes="Error"
                return u"無法辨識這張處方籤上的QRCODE哦，請再拍得更清晰些。"

            if(rawBytes!="CTYPE"):
                In_data=OrderedDict()
                In_data['userId']=userId

                arr_data = rawBytes.split(';')
        
                In_data['病患姓名']=arr_data[3]
                In_data['出生日期']=arr_data[5]
                In_data['身分證字號']=arr_data[4]
                In_data['就醫日期']=arr_data[7]
                In_data['給藥日份']=arr_data[9]
                In_data['用藥']=[]
                In_data['用藥'].append(OrderedDict([('藥品代號', arr_data[14]),('藥品用量', arr_data[15]), ('用藥頻率', arr_data[16]),
                                                ('途徑', arr_data[17]),('總數量', arr_data[18])]) )
                if len(arr_data)>20:
                    for i in range(19,len(arr_data)-1,5):
                        In_data['用藥'].append(OrderedDict([('藥品代號', arr_data[i]),('藥品用量', arr_data[i+1]), ('用藥頻率', arr_data[i+2]),
                                                    ('途徑', arr_data[i+3]),('總數量', arr_data[i+4])]) )
                os.remove(filepath)
                resault = collection.find_one(In_data)
                if(resault == None):
                    # collection.insert_one(In_data)
                    return In_data
                else:
                    return None
                    
