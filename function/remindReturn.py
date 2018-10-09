# -*- coding: utf-8 -*-
"""
Created on Tue Jul 24 11:48:04 2018

提醒領藥
@author: 蔡念定

!pip install flask
!pip install pymongo
!pip install selenium
!pip install jieba
!pip install pygame
!pip install simplejson
!pip install pytagcloud
!pip install line-bot-sdk
!pip install apscheduler
"""

#!/usr/bin/python
#-*-coding:utf-8 -*
from flask import Flask,url_for,request
from operator import itemgetter
from urllib.parse import parse_qs
from linebot import LineBotApi
from linebot.models import *
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime,timedelta,date
from pymongo import MongoClient
import json,re,requests,jieba,os,datetime,time,threading

client = MongoClient(host='localhost', port=27017, document_class=dict, tz_aware=False, connect=True)
db=client["Medicine"]

user_task = {'user_id':'',
             'status': 1,
             'ask_count': 0,
             }

app = Flask(__name__)
global user_task_list,user_list
user_task_list = {}
user_list = []

line_bot_api = LineBotApi('PRdn4cTEXSpamN/HHh1kIVmiw0T2r90K+aE6Ww/FvEQCIHzc2ZaLHwEUwHugCC3K4qkYC59qqifOvqTm+iq6jJqKRzzHGNtvgbZbxl1ZMpj1f6UzVddzKVKnCzhsSRNfkFUdqCZHVDM8a8TBMKRwHgdB04t89/1O/w1cDnyilFU=')
temp = []

for i in range(1,5,1):
	template_data = CarouselColumn(
					thumbnail_image_url='https://example.com/item1.jpg',
					title='this is menu1',
					text='description1',
					actions=[
						PostbackTemplateAction(
							label=i,
							text='postback text1',
							data='action=buy&itemid=1'
						),
						MessageTemplateAction(
							label='message1',
							text='message text1'
						),
						URITemplateAction(
							label='uri1',
							uri='http://example.com/1'
						)
					]
				)
	temp.append(template_data)
carousel_template_message = TemplateSendMessage(
    alt_text='Carousel template',
    template=CarouselTemplate(
        columns=temp
    )
)

########## 提醒領藥 ##########

#qr=QRCode掃到的內容
qr="1131010011;2;4;王小明;A123456789;0521023;AD;1070826;0010;28;A12;403.90#586#280.9#274.9#780.59#564.0#;1131010011;;A034157100;1.00;BID;PO;56;B022951100;2.00;QD;PO;56;B023711100;1.00;QD;PO;28;A014228100;0.50;QD;PO;14;A002756100;3.00;BID;PO;168;B016504100;1.00;BID;P";
qr_Rx=qr.split(";")[1]  #處方箋:一般處方 1 ; 連續處方 2
qr_Name=qr.split(";")[3]    #病患姓名
qr_Date=str(int(qr.split(";")[7])+19110000) #就醫日期
qr_Date=datetime.datetime.strptime(qr_Date, '%Y%m%d')  #將就醫日期轉換成西元-月份-日期(包含時分秒)
qr_Days=qr.split(";")[9] #給藥日份
end_Date=qr_Date+datetime.timedelta(int(qr_Days)*3-1)   #處方箋過期日

# 宣告調度器
scheduler_only = BackgroundScheduler()
scheduler = BackgroundScheduler()
scheduler2 = BackgroundScheduler()

#取得QR_code
def remind_getMed(ttt,uid):   
    today = datetime.datetime.now() #抓取系統時間
    #判斷是否為連續處方箋
    if qr_Rx=="2":
        #判斷處方箋是否過期
        if today < end_Date:
            #添加定時任務(調度器:scheduler_only)
            scheduler_only.add_job(remind_job, 'interval', days=int(qr_Days)-7, id=uid, start_date=qr_Date+datetime.timedelta(hours=8), end_date=end_Date+datetime.timedelta(int(qr_Days)), args=[ttt,uid])
            line_bot_api.reply_message(ttt, TextSendMessage(text="此為連續處方籤，開啟提醒領藥功能\n如欲取消領藥提醒，請輸入\"取消\""))
        else:
            #print("此連續處方箋已經過期，無法領藥")
            line_bot_api.reply_message(ttt, TextSendMessage(text="此連續處方箋已經過期，無法領藥!"))
        #開始運行調度器:scheduler_only
        scheduler_only.start()

#scheduler_only/scheduler調度器呼叫(給藥日份屆滿前7日呼叫一次)
def remind_job(ttt,uid):
    #print("remind_job\n")
    today = datetime.datetime.now() #抓取系統時間(第1天提醒，共7天)
    endDay=date.today()+datetime.timedelta(7) #最後一天提醒領藥(共7天)
    
    #刪除scheduler_only的工作(第一次的領藥提醒天數需-7，故僅執行一次)
    if scheduler_only.get_jobs():
        scheduler_only.remove_job(uid)
    #判斷是否已添加scheduler
    if not(scheduler.get_jobs()):
        scheduler.add_job(remind_job, 'interval', days=int(qr_Days), id=uid, start_date=today, end_date=end_Date+datetime.timedelta(int(qr_Days)), args=[ttt,uid])
    
    #判斷是否已超過領藥次數(通常為3次)
    if today <= end_Date:
        scheduler2.add_job(remind_txt, 'interval', days=1, id=uid, start_date=today, end_date=endDay, args=[ttt,uid,endDay])
        #開始運行調度器2
        scheduler2.start()
    else:
        #print("連續處方箋領藥提醒\n"+qr_Name+"先生/小姐，連續處方籤通常只可領3次，請記得回醫院看診～\n\n如欲繼續領藥提醒，需重新掃描新的處方箋，謝謝！")
        line_bot_api.push_message(uid, TextSendMessage(text="連續處方箋領藥提醒\n"+qr_Name+"先生/小姐，連續處方籤通常只可領3次，請記得回醫院看診～\n\n如欲繼續提醒領藥功能，需重新掃描新的處方箋，謝謝！"))
        
        if scheduler.get_jobs():
            scheduler.remove_job(uid)
            if scheduler2.get_jobs():
                scheduler2.remove_job(uid)

#scheduler2調度器呼叫(每日呼叫一次，共7天)
def remind_txt(ttt,uid,endDay):
    today = date.today() #抓取系統時間
    #print("連續處方箋領藥提醒\n"+qr_Name+"先生/小姐，請記得於"+str(endDay)+"前至看診醫院或健保特約藥局領藥喔～\n\n如欲取消領藥提醒，請輸入\"取消\"")
    line_bot_api.push_message(uid, TextSendMessage(text="連續處方箋領藥提醒\n"+qr_Name+"先生/小姐，請記得於"+str(endDay)+"前至看診醫院或健保特約藥局領藥喔～\n\n如欲取消領藥提醒，請輸入\"取消\""))
    
    #判斷今日是否為此次領藥的最後一日
    if today < endDay:
        #詢問是否搜尋附近藥局
        confirm= TemplateSendMessage(
        alt_text='藥局導引詢問',
        template=ConfirmTemplate(
            title='藥局導引詢問',                
            text='是否搜尋附近藥局？',
            actions=[
                PostbackTemplateAction(
                    label='是',
                    text='是',
                    data='action=pharmacyGuide&status=yes'
                ),
                PostbackTemplateAction(
                    label='否',
                    text='否',
                    data='action=pharmacyGuide&status=no'
                )
            ])
        )
        line_bot_api.push_message(uid,confirm)

    else:
        line_bot_api.push_message(uid, TextSendMessage(text="今日為領藥期限最後一日，請盡速去領藥！"))
        #讓使用者自行傳送位置
        line_bot_api.push_message(uid, TextSendMessage(text="點選對話框旁邊的「+」並按「傳送位置訊息」，離你最近的藥局就會出現喔~"))
        if scheduler2.get_jobs():
            scheduler2.remove_job(uid)

#google map
def locationapi(ttt,uid,msg):
    #gmaps = googlemaps.Client(key='AIzaSyDeN9RAfTQpDIjbtsjWoQsWOznrPNTkb00')
    
    #Distance Matrix API 金鑰
    mapapi="AIzaSyACPkahPx9DAFXqgzaUFPk8YqyJofHNBFc"
    #呼叫資料庫
    collect=db["pharmacy"]
    #正規化地址,取得區域鄉鎮
    district=r'(\D+?(區|鎮區|[鄉鎮區]))'
    match=re.search(district,msg)
    loc=match.group().split('台灣')[1]
    loc=loc.replace('台','臺') 
    mapurl='https://maps.googleapis.com/maps/api/distancematrix/json?units=imperial&origins='+msg+'&destinations='
    pharmacy=collect.find({'city':loc}).limit(60) #max=66
    newlist=[]
    for i in pharmacy:
        mapurl=mapurl+i['address']+'|'
        newlist.append(i)
    mapurl=mapurl+'&units=metric&key='+mapapi
    res=requests.get(mapurl)
    res_json =json.loads(res.text)
    print(res_json)
    num=0
    for i in res_json['rows'][0]['elements']:
        if(i['status']!="NOT_FOUND"):
            newlist[num]["distance"]=i["distance"]['value']
            newlist[num]["time"]=i["duration"]['text']
        else:
            newlist[num]["distance"]=99999
            newlist[num]["time"]=99999
        num=num+1	
    newlist=sorted(newlist,key=itemgetter('distance'))
    addressinfo=[]
    for i in range(0,len(newlist)):
        if(i==5):
            break;
        addressinfo.append(CarouselColumn(
	               title=newlist[i]['name'],
	               text=newlist[i]['address']+'，距離你共'+str(newlist[i]['distance'])+'公尺，走路'+newlist[i]['time'].replace("mins","分")+'鐘即可抵達',
	               actions=[
	                   PostbackTemplateAction(
	                       label='店家資訊',
	                       data='action=pharmacy&address='+newlist[i]['address']
	                   ),
	                   URITemplateAction(
	                       label='Google map導航',
	                       uri='https://www.google.com.tw/maps/dir/'+msg+'/'+newlist[i]['address']
	                   )
	               ]
	           ))
    print(addressinfo)
    carousel_template_message = TemplateSendMessage(
	   alt_text='藥局選單',
	   template=CarouselTemplate(
	       columns=addressinfo
	   )
    )
    line_bot_api.reply_message(ttt,carousel_template_message)

#藥局資訊
def pharmacyinfo(ttt,name):
    collect=db["pharmacy"]
    pharmacy=collect.find_one({'address':name})
    medtext=("藥局名稱:"+pharmacy["name"]+'\n'
            "地址:"+pharmacy["address"]+'\n'
            "負責人:"+pharmacy["boss"]+' '+pharmacy["sex"]+'士\n'
            "聯絡電話:"+pharmacy["number"]+'\n'
            "是否為健保特約藥局:"+pharmacy["official"])
    line_bot_api.reply_message(ttt,TextSendMessage(text=medtext))

#藥局資訊 使用者輸入藥局名稱
def pharmacyname(ttt,name,count=0):
    #切割文字
    pharmacymsg=name.split("藥局")
    #呼叫資料庫並查詢
    collect=db["pharmacy"]
    pharmacy=collect.find({'name':pharmacymsg[0]+"藥局"})
    if(pharmacy.count(True)==1):
        for i in pharmacy:
            pharmacyinfo(ttt,i["address"])
            return True
    elif(pharmacy.count(True)>1):
        tmplist=[]
        time=0
        for i in pharmacy:
            if(time<count):
                time=time+1
                continue
            if(time==count+3):
                tmplist.append(PostbackTemplateAction(label="再顯示其他縣市",data='action=pharmacylist&pharmacyname='+name+'&time='+str(time)))
                break
            tmplist.append(PostbackTemplateAction(label=i["city"],data='action=pharmacy&address='+i['address']))
            time=time+1
        
        confirm_template_message = TemplateSendMessage(
            alt_text='相同藥局名稱',
            template=ButtonsTemplate(
                title='藥局查詢',
                text='因為找到兩個以上的藥局名稱，所以請選擇縣市區域',
                actions=tmplist
            )  
        )
        line_bot_api.reply_message(ttt, confirm_template_message)
        return True
    return False

#詢問明日是否需要領藥提醒
def remindTMR(ttt,uid):
    #print("明日是否需要提醒您領藥呢？(是/否)")
    confirm= TemplateSendMessage(
        alt_text='明日是否需要提醒您領藥呢？',
        template=ConfirmTemplate(
        text='明日是否需要提醒您領藥呢？',
        actions=[
            PostbackTemplateAction(
                label='是，繼續提醒',
                data='action=remind_TMR&status=yes'
            ),
            PostbackTemplateAction(
                label='否，不需提醒',
                data='action=remind_TMR&status=no'
            )
        ])
    )
    line_bot_api.push_message(uid,confirm)


@app.route('/callback',methods=['POST'])
def callback():
    temp = request.get_json()
    print(temp)
    for i in temp['events']:
        #取得回覆ID,一個回覆只能用一次		
        ttt =  i['replyToken']
        uid=i['source']['userId']
        #msg = i['message']['text']
        if(i['type']!='postback' and i['message']['type']!='location'):
            msg = i['message']['text']
        #文字
        if i['type']=='postback': #判斷等待的參數是哪個
            pos=parse_qs(i['postback']['data'])
            print(pos)
            if pos['action'][0]=='pharmacyGuide':
                if pos['status'][0]=="yes":
                    #領藥提醒:使用者選擇執行藥局搜尋
                    line_bot_api.reply_message(ttt, TextSendMessage(text="點選對話框旁邊的「+」並按「傳送位置訊息」，離你最近的藥局就會出現喔~"))
                    if scheduler2.get_jobs():
                        scheduler2.remove_job(uid)
                elif pos['status'][0]=="no":
                    #領藥提醒:使用者選擇不執行藥局搜尋
                    remindTMR(ttt,uid)
            elif pos['action'][0]=='remind_TMR':
                if pos['status'][0]=="yes":
                    line_bot_api.reply_message(ttt, TextSendMessage(text='了解～\n明日會繼續提醒您領藥'))
                elif pos['status'][0]=="no":
                    line_bot_api.reply_message(ttt, TextSendMessage(text='了解～\n取消本次的領藥提醒'))
                    if scheduler2.get_jobs():
                        scheduler2.remove_job(uid)
            elif pos['action'][0]=='pharmacy':
                #顯示藥局資訊
                pharmacyinfo(ttt,pos['address'][0])
            elif pos['action'][0]=='pharmacylist':
                pharmacyname(ttt,pos['pharmacyname'][0],int(pos['time'][0]))
        if i['message']['type']=='text':
            if uid not in user_list:
                msg = TextSendMessage(text='您好 歡迎使用藥事助理-梅德森')
                user_list.append(uid)
                user_task_list[uid] = user_task
                user_task_list[uid]['user_id'] = uid
                line_bot_api.reply_message(ttt, msg)
                line_bot_api.push_message(uid, TextSendMessage(text='提醒領藥功能'))
            elif uid in user_list:               
                if user_task_list[uid]['status'] == 1 and msg != "取消" and not(msg.endswith("藥局")):                    
                    remind_getMed(ttt,uid)                    	
                elif msg == "取消":
                    if scheduler_only.get_jobs():
                        scheduler_only.remove_job(uid)
                    if scheduler.get_jobs():
                        scheduler.remove_job(uid)
                    if scheduler2.get_jobs():
                        scheduler2.remove_job(uid)
                    line_bot_api.reply_message(ttt, TextSendMessage(text='關閉提醒領藥功能～\n若需開啟提醒領藥功能，請重新掃描處方箋'))
                elif msg.endswith("藥局"):
                    #資料庫藥局搜尋
                    issearchpharmacyname=pharmacyname(ttt,msg)
                    if(not issearchpharmacyname):
                        line_bot_api.reply_message(ttt, TextSendMessage(text='未找到該藥局'))
                else:
                    line_bot_api.reply_message(ttt, TextSendMessage(text='祝您身體安康，萬事如意～'))
        
        #位置
        if i['message']['type']=='location':
            #地址
            if 'address' in i['message'].keys():
                msg = i['message']['address']
            elif 'latitude' in i['message'].keys():
                geocodingapi="AIzaSyACPkahPx9DAFXqgzaUFPk8YqyJofHNBFc"
                res=requests.get('https://maps.googleapis.com/maps/api/geocode/json?latlng='+str(i['message']['latitude'])+','+str(i['message']['longitude'])+'&key='+geocodingapi+'&language=zh-TW')
                #print('https://maps.googleapis.com/maps/api/geocode/json?latlng='+str(i['message']['latitude'])+','+str(i['message']['longitude'])+'&key='+geocodingapi+'&language=zh-TW')
                res_geo = json.loads(res.text)
                #print(res_geo["results"][0]['formatted_address'])
                msg =res_geo["results"][0]['formatted_address']
            locationapi(ttt,uid,msg)
   
    return "" ,200


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

