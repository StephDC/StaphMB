#! /usr/bin/env python3

import sqldb
import urllib.error as ue
import urllib.request as ur
import urllib.parse as up
import json
import datetime
import time
import sys
import os

__version__ = '0.1'
__doc__ = '''StaphMB - A Telegram Group Management Bot infected by _S. aureus_

Synopsis:\n\tStaphMbot.py sqlite.db API-Key

Version:\n\t'''+str(__version__)

class APIError(Exception):
    def __init__(self,module,info):
        self.info = info
    def __str__(self):
        return 'Telegram Bot '+self.module+' Exception: '+self.info
    def __repr__(self):
        return '<TGBot Exception="'+self.module+'" Info="'+self.info+'" />'

class stdOut():
    def __init__(self):
        pass
    def writeln(self,data):
        print(data)

class tgapi:
    __doc__ = 'tgapi - Telegram Chat Bot HTTPS API Wrapper'

    def __init__(self,apikey,logger=None,maxRetry=5):
        self.logOut = stdOut() if logger is None else logger
        self.target = 'https://api.telegram.org/bot'+apikey+'/'
        self.retry = maxRetry
        self.info = self.query('getMe')
        if self.info is None:
            raise APIError('API', 'Initialization Self-test Failed')
        self.logOut.writeln("Bot "+self.info["username"]+" connected to the Telegram API.")

    def query(self,met,parameter=None,retry=None):
        req = ur.Request(self.target+met,method='POST')
        req.add_header('User-Agent','StaphMbot/0.1 (+https://github.com/StephDC/StaphMbot)')
        if parameter is not None:
            req.add_header('Content-Type','application/json')
            req.data = json.dumps(parameter).encode('UTF-8')
        #            print(req.data.decode('UTF-8'))
        retryCount = 0
        maxRetry = retry if retry is not None else self.retry
        failed = True
        while failed:
            try:
                resp = ur.urlopen(req)
            except ue.HTTPError:
                if retryCount >= maxRetry:
                    raise APIError('API','Query HTTP Error')
            except ue.URLError:
                if retryCount >= maxRetry:
                    raise APIError('API','Query DNS Error')
            else:
                failed = False
                break
            self.logOut.writeln("Query failed. Try again in 5 sec.")
            time.sleep(5)
            retryCount += 1
        data = json.loads(resp.read().decode('UTF-8'))
        #print(data)
        return data['result'] if data['ok'] else None
    
    def sendMessage(self,target,text,misc={}):
        misc['text'] = text
        misc['chat_id'] = target
        data = self.query('sendMessage',misc)
        if data and data['text'] == text:
            return data['message_id']
        else:
            return False

def initiateDB(fName,outdev):
    try:
        conf = sqldb.sqliteDB(fName,'config')
    except sqldb.sqliteDBError:
        raise APIError('DB','Corrupted configuration table')
    if conf.getItem('dbver','value') != '1.0':
        raise APIError('DB','Database schema version is incompatible')
    try:
        group = sqldb.sqliteDB(conf.db,'group')
    except sqldb.sqliteDBError:
        raise APIError('DB','Corrupted group table')
    try:
        warn = sqldb.sqliteDB(conf.db,'warn')
    except sqldb.sqliteDBError:
        raise APIError('DB','Corrupted warn table')
    outdev.writeln('DB File '+fName+' loaded.')
    return (conf,group,warn)

def addGroup(gid,db,outdev):
    if not db[1].hasItem(gid):
        db[1].addItem([str(gid)]+[str(i) for i in db[1].data.execute('select * from "group" where header="default"').fetchone()[1:]])
        outdev.writeln('I\'ve been added to a new group '+str(gid)) #+': '+message['message']['chat']['title']+'.')
    else:
        outdev.writeln('I\'ve been added back to group '+str(gid)) #+': '+message['message']['chat']['title']+'.')

def randomID():
    return hex(int.from_bytes(os.urandom(8),'big'))[2:]

def countWarn(db,gid,uid):
    return db[2].data.execute('select count(header) from warn where user=? and "group"=?',(str(uid),str(gid))).fetchone()[0]

def getName(uid,gid,api,lookup={}):
    if uid in lookup:
        return '@'+lookup[uid]
    try:
        result = api.query('getChatMember',{'chat_id':int(gid),'user_id':int(uid)},retry=1)
    except APIError:
        return 'a former admin of this group'
    return getNameRep(result['user'])

def getNameRep(userObj):
    if 'username' in userObj:
        return '@'+userObj['username']
    elif 'last_name' in userObj:
        return '@'+userObj['first_name']+userObj['last_name']

def processWarn(db,api,uid,gid,ts,reply):
    api.logOut.writeln('Processing actual punishment...')
    warnNum = countWarn(db,gid,uid)
    if warnNum == 0:
        api.logOut.writeln("It does not qualify any warning.")
        return
    if warnNum > 5:
        warnNum = 5
    api.logOut.writeln(gid,db[1].hasItem(str(gid)),'warning'+str(warnNum))
    punish = db[1].getItem(str(gid),'warning'+str(warnNum)).split('|')
    api.logOut.writeln(punish)
    # 0 - Nothing
    # 1 - Mute
    # 2 - Kick
    if punish[0] == '1':
        if len(punish) == 1 or punish[1] == '0':
            # Forever
            api.logOut.writeln(api.query('restrictChatMember',{'chat_id':gid,'user_id':uid,'until_date':int(time.time()+10),'can_send_messages':False}))
            api.sendMessage(gid,'該用戶已被永久禁言。',{'reply_to_message_id':reply})
        elif int(ts)+int(punish[1]) - time.time() < 60:
            api.sendMessage(gid,'該用戶應當被禁言至 '+datetime.datetime.fromtimestamp(int(ts)+int(punish[1])).isoformat()+' 然而由於處理時間已過，故此不作處分。',{'reply_to_message_id':reply})
        else:
            api.logOut.writeln(api.query('restrictChatMember',{'chat_id':gid,'user_id':uid,'until_date':int(ts)+int(punish[1]),'can_send_messages':False}))
            api.sendMessage(gid,'該用戶已被禁言至 '+datetime.datetime.fromtimestamp(int(ts)+int(punish[1])).isoformat()+' 。',{'reply_to_message_id':reply})
    if punish[0] == '3':
        if len(punish) == 1 or punish[1] == '0':
            api.logOut.writeln(api.query('kickChatMember',{'chat_id':gid,'user_id':uid,'until_date':int(time.time()+10)}))
            api.sendMessage(gid,'該用戶已被永久封禁。',{'reply_to_message_id':reply})
        elif int(ts)+int(punish[1]) - time.time() < 60:
            api.sendMessage(gid,'該用戶應當被封禁至 '+datetime.datetime.fromtimestamp(int(ts)+int(punish[1])).isoformat()+' 然而由於處理時間已過，故此不作處分。',{'reply_to_message_id':reply})
        else:
            api.logOut.writeln(api.query('kickChatMember',{'chat_id':gid,'user_id':uid,'until_date':int(ts)+int(punish[1])}))
            api.sendMessage(gid,'該用戶已被封禁至 '+datetime.datetime.fromtimestamp(int(ts)+int(punish[1])).isoformat()+' 。',{'reply_to_message_id':reply})

def processRule(gid,db):
    result = '警告與懲罰規則：\n'
    data = [db[1].getItem(str(gid),'warning'+str(i)).split('|') for i in range(1,6)]
    while len(data) > 1 and data[-1] == data[-2]:
        data.pop() # Makes the list more compact
    for item in range(len(data)):
        if item == len(data)-1:
            result += str(item+1)+' 個或更多個警告：'
        else:
            result += str(item+1)+' 個警告：'
        if data[item][0] == '0':
            result += '口頭警告\n'
        elif data[item][0] == '1':
            if data[item][1] == '0':
                result += '永久禁言\n'
            else:
                result += '禁言 '+str(datetime.timedelta(seconds=int(data[item][1])))+'\n'
        elif data[item][0] == '2':
            result += '封禁 '+str(datetime.timedelta(seconds=int(data[item][1])))+'\n'
        elif data[item][0] == '3':
            result += '永久封禁\n'
    data = db[1].getItem(str(gid),'fade').split('|')
    if data[0] == '0':
        result += '警告期限：警告永不過期'
    elif data[0] == '1':
        result += '警告期限：'+str(datetime.timedelta(seconds=int(data[1])))
    elif data[0] == '2':
        result += '警告期限：每月 1 日解除 '+data[1]+' 個警告。'
    return result

def processCheck(msg,api,db):
    if message['message']['chat']['type'] == 'private':
    # Check the warnings for the user itself across the globe
        api.sendMessage(message['message']['chat']['id'],'Checking your warnings... Not Implemented D:',{'reply_to_message_id':message['message']['message_id']})
    elif message['message']['chat']['type'] == 'supergroup':
    # Check the warnings for the user itself within the group
        data = db[2].data
        api.sendMessage(message['message']['chat']['id'],'Checking your warnings... Not Implemented.',{'reply_to_message_id':message['message']['message_id']})

def processItem(message,db,api):
    api.logOut.writeln(message['update_id'],'being processed...')
    if 'message' not in message:
        return
    if 'text' in message['message'] and message['message']['text']:
        # Process bot command
        if message['message']['text'][0] == '/':
            stripText = message['message']['text']
            if '@'+api.info['username'] in stripText:
                stripText=stripText[:-len(api.info['username'])-1]
            if stripText == '/ping':
                api.sendMessage(message['message']['chat']['id'],'Hell o\'world!',{'reply_to_message_id':message['message']['message_id']})
            elif stripText == '/groupid':
                api.sendMessage(message['message']['chat']['id'],'Group ID: '+str(message['message']['chat']['id']),{'reply_to_message_id':message['message']['message_id']})
            elif stripText == '/warnrule':
                api.sendMessage(message['message']['chat']['id'],processRule(message['message']['chat']['id'],db),{'reply_to_message_id':message['message']['message_id']})
            elif stripText == '/warncheck':
                processCheck(message,api,db)
        # Process hashtag
        elif message['message']['text'][0] == '#':
            if len(message['message']['text'])>4 and message['message']['text'][1:5].lower() == 'warn':
                if message['message']['chat']['type']!='supergroup':
                    api.sendMessage(message['message']['chat']['id'],'抱歉，警告功能僅在超級群組有效。',{'reply_to_message_id':message['message']['message_id']})
                else:
                    adminList = {i['user']['id']:getNameRep(i['user']) for i in api.query('getChatAdministrators',{'chat_id':message['message']['chat']['id']})}
                    if message['message']['from']['id'] not in adminList:
                        api.sendMessage(message['message']['chat']['id'],'抱歉，僅有濫權管理員方可使用 #WARN 警告其他用戶。',{'reply_to_message_id':message['message']['message_id']})
                    elif 'reply_to_message' not in message['message']:
                        api.sendMessage(message['message']['chat']['id'],'用法錯誤：請回覆需要被警告的訊息。',{'reply_to_message_id':message['message']['message_id']})
                    elif db[2].data.execute('SELECT count(header) from warn where "group"=? and "text"=?',(str(message['message']['chat']['id']),str(message['message']['reply_to_message']['message_id']))).fetchone()[0]:
                        warnInfo = db[2].data.execute('SELECT time,admin,reason from warn where "group"=? and "text"=?',(str(message['message']['chat']['id']),str(message['message']['reply_to_message']['message_id']))).fetchone()
                        api.sendMessage(message['message']['chat']['id'],'抱歉，該條訊息已於 '+datetime.datetime.fromtimestamp(int(warnInfo[0])).isoformat()+' 被 '+getName(warnInfo[1],message['message']['chat']['id'],api,adminList)+' 以理由「 '+warnInfo[2]+' 」警告過。',{'reply_to_message_id':message['message']['message_id']})
                    else:
                        warnInfo = [int(time.time()),message['message']['chat']['id'],message['message']['reply_to_message']['from']['id'],message['message']['reply_to_message']['message_id'],message['message']['from']['id'],message['message']['text'][5:].strip()]
                        if not warnInfo[-1]:
                            api.sendMessage(message['message']['chat']['id'],'用法錯誤：請提供警告理由，使對方明白何處做錯。',{'reply_to_message_id':message['message']['message_id']})
                        elif warnInfo[2] in adminList:
                            api.sendMessage(message['message']['chat']['id'],'竟敢試圖警告管理員，你的請求被濫權掉了。',{'reply_to_message_id':message['message']['message_id']})
                        elif warnInfo[2] == api.info['id'] or message['message']['reply_to_message']['from']['is_bot']:
                            api.sendMessage(message['message']['chat']['id'],'竟敢試圖警告機器人，你的請求被濫權掉了。',{'reply_to_message_id':message['message']['message_id']})
                        else:
                            notUnique = True
                            while notUnique:
                                id = [randomID()]
                                notUnique = db[2].hasItem(id[0])
                            db[2].addItem(id+warnInfo)
                            rep = api.sendMessage(message['message']['chat']['id'],'警告成功。該用戶現在共有 '+str(countWarn(db,warnInfo[1],warnInfo[2]))+' 個警告。',{'reply_to_message_id':message['message']['message_id']})
                            api.logOut.writeln('Warned '+getNameRep(message['message']['reply_to_message']['from'])+' in group '+message['message']['chat']['id'])
                            processWarn(db,api,warnInfo[2],warnInfo[1],message['message']['reply_to_message']['date'],rep)
            elif len(message['message']['text'])>7 and message['message']['text'][1:8].lower() == 'delwarn':
                if message['message']['chat']['type']!='supergroup':
                    api.sendMessage(message['message']['chat']['id'],'抱歉，警告功能僅在超級群組有效。',{'reply_to_message_id':message['message']['message_id']})
                else:
                    adminList = {i['user']['id']:getNameRep(i['user']) for i in api.query('getChatAdministrators',{'chat_id':message['message']['chat']['id']})}
                    if message['message']['from']['id'] not in adminList:
                        api.sendMessage(message['message']['chat']['id'],'抱歉，僅有濫權管理員方可使用 #DELWARN 解除對其他用戶的警告。',{'reply_to_message_id':message['message']['message_id']})
                    elif 'reply_to_message' not in message['message']:
                        api.sendMessage(message['message']['chat']['id'],'用法錯誤：請回覆被警告用戶發送的原始訊息。',{'reply_to_message_id':message['message']['message_id']})
                    elif db[2].data.execute('SELECT count(header) from warn where "group"=? and "text"=?',(str(message['message']['chat']['id']),str(message['message']['reply_to_message']['message_id']))).fetchone()[0] == 0:
                        api.sendMessage(message['message']['chat']['id'],'用法錯誤：該條訊息並未被警告過，請回覆被警告用戶發送的原始訊息。',{'reply_to_message_id':message['message']['message_id']})
                    else:
                        warnInfo = db[2].data.execute('SELECT time,admin,reason,header from warn where "group"=? and "text"=?',(str(message['message']['chat']['id']),str(message['message']['reply_to_message']['message_id']))).fetchone()
                        #print(db[2].remItem(warnInfo[-1]))
                        db[2].remItem(warnInfo[-1])
                        api.logOut.writeln('Removed warning for '+getNameRep(message['message']['reply_to_message']['from'])+' in group '+message['message']['chat']['id'])
                        api.sendMessage(message['message']['chat']['id'],'該條訊息曾於 '+datetime.datetime.fromtimestamp(int(warnInfo[0])).isoformat()+' 被 '+getName(warnInfo[1],message['message']['chat']['id'],api,adminList)+' 以理由「 '+warnInfo[2]+' 」警告過。警告現已取消。該用戶現有 '+str(countWarn(db,message['message']['chat']['id'],message['message']['reply_to_message']['from']['id']))+' 個警告。如該用戶已因警告遭致處分，請管理員亦一同處置。',{'reply_to_message_id':message['message']['message_id']})
    elif 'new_chat_participant' in message['message']:
        if message['message']['new_chat_participant']['id'] == api.info["id"]:
            addGroup(message['message']['chat']['id'],db,api.logOut)
    db[0].addItem(['lastid',message['update_id']])
    db[0].addItem(['lasttime',message['message']['date']])

def run(db,api):
    data = api.query('getUpdates')
    resPos = int(db[0].getItem('lastid','value'))
    for item in range(len(data)):
        if data[item]['update_id'] == resPos:
            data = data[item+1:]
            api.logOut.writeln('Skipping '+str(item+1)+' processed messages.')
            break
    for item in data:
        processItem(item,db,api)
    api.logOut.writeln('All pending messages processed.')
    while True:
        time.sleep(2) #Max frequency 30 messages/group
        data = api.query('getUpdates',{'offset':int(db[0].getItem('lastid','value'))+1,'timeout':20})
        for item in data:
            processItem(item,db,api)

def main(args):
    outdev = open(args[2],'a') if len(args)==3 else stdOut()
    if len(args) not in (2,3):
        print('FATAL ERROR: Incorrect number of parameters given.')
        print(__doc__)
        sys.exit(1)
    try:
        api = tgapi(args[1],outdev)
    except APIError:
        print('FATAL ERROR: API Initialization Self-test Failed.')
        sys.exit(2)
    try:
        db = initiateDB(args[0],outdev)
    except APIError:
        print('FATAL ERROR: Corrupted database or wrong parameter given.')
        sys.exit(3)
    print('The configurations have been loaded successfully.')
    run(db,api)

if __name__ == '__main__':
    main(sys.argv[1:])
