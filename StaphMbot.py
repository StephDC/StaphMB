#! /usr/bin/env python3

import base64
import datetime
import json
import os
import queue
import sqldb
import subprocess
import sys
import threading
import time
import urllib.error as ue
import urllib.request as ur
import urllib.parse as up

__version__ = '0.1'
__doc__ = '''StaphMB - A Telegram Group Management Bot infected by _S. aureus_

Synopsis:\n\tStaphMbot.py sqlite.db API-Key

Version:\n\t'''+str(__version__)

class APIError(Exception):
    def __init__(self,module,info):
        self.module = module
        self.info = info
    def __str__(self):
        return 'Telegram Bot '+self.module+' Exception: '+self.info
    def __repr__(self):
        return '<TGBot Exception="'+self.module+'" Info="'+self.info+'" />'

class stdOut():
    def __init__(self,fName=None):
        self.fh = None if fName is None else open(fName,'a',1)
    def writeln(self,data):
        if self.fh is None:
            print('['+str(int(time.time()))+'] '+str(data))
        else:
            self.fh.write('['+str(int(time.time()))+'] '+str(data)+'\n')

class tgapi:
    __doc__ = 'tgapi - Telegram Chat Bot HTTPS API Wrapper'

    def __init__(self,apikey,logger=None,maxRetry=5):
        self.logOut = stdOut() if logger is None else logger
        self.target = 'https://api.telegram.org/bot'+apikey+'/'
        self.retry = maxRetry
        self.qthread = []
        self.msgAF = {}
        self.info = self.query('getMe')
        if self.info is None:
            raise APIError('API', 'Initialization Self-test Failed')
        self.logOut.writeln("Bot "+self.info["username"]+" connected to the Telegram API.")

    def query(self,met,parameter=None,retry=None):
        'Query Telegram Bot API'
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
            self.logOut.writeln("Failed Request:\nMethod: "+met+"\nParameters: "+str(parameter))
            time.sleep(5)
            retryCount += 1
        data = json.loads(resp.read().decode('UTF-8'))
        #print(data)
        return data['result'] if data['ok'] else None
    
    def sendMessage(self,target,text,misc={}):
        if int(target) in self.msgAF:
            delay = self.msgAF[int(target)] + 3 - time.time()
            if delay > 0.5:
                time.sleep(delay)
        misc['text'] = text
        misc['chat_id'] = target
        misc['parse_mode'] = misc['parse_mode'] if 'parse_mode' in misc else 'HTML'
        try:
            data = self.query('sendMessage',misc,retry=0)
        except APIError:
            tmp = self.query("getChatMember",{"chat_id":target,"user_id":self.info['id']})
            if 'can_send_messages' in tmp and tmp['can_send_messages'] == False:
                self.query("leaveChat",{"chat_id":target})
                self.logOut.writeln("Leaving group "+str(target)+" because I am restricted from send messages.")
            else:
                if 'reply_to_message_id' in misc:
                    misc.pop('reply_to_message_id')
                data = self.query('sendMessage',misc,retry=self.retry-1)
        self.msgAF[int(target)] = time.time()
        if data and data['text'] == text:
            return data['message_id']
        else:
            return False

    def sendAction(self,target,duration,action):
        if action not in ('typing','upload_photo','record_video','upload_video','record_audio','upload_audio','upload_document','find_location','record_video_note','upload_video_note'):
            raise APIError('API','Illegal action '+action)
        self.query('sendChatAction',{'chat_id':target,'action':action})
        time.sleep(target % 5)
        target -= target % 5
        while target:
            self.query('sendChatAction',{'chat_id':target,'action':action})
            time.sleep(5)
            target -= 5

    def dQuery(self,delay,query,param=None,retry=None):
        'blocking sleep - query'
        time.sleep(delay)
        return self.query(query,param,retry)

    def dBQuery(self,delay,batchQuery,afDelay):
        'Execute a batch of queries after a delay - blocking'
        time.sleep(delay)
        for item in batchQuery:
            try:
                self.query(item[0],item[1] if len(item) > 1 else None,item[2] if len(item) > 2 else None)
                time.sleep(afDelay)
            except APIError:
                pass

    def delayBatchQuery(self,delay,batchQuery,afDelay=0.5):
        th = threading.Thread(target=self.dBQuery,args=(delay,batchQuery,afDelay))
        th.start()
        self.qthread.append(th)

    def delayQuery(self,delay,query,param=None,retry=None):
        th = threading.Thread(target=self.dQuery,args=(delay,query,param,retry))
        th.start()
        self.qthread.append(th)

    def clearDelayQuery(self):
        result = 0
        for item in self.qthread:
            if item.is_alive():
                result += 1
            else:
                item.join()
                self.qthread.remove(item)
        return result

# A few output formatting functions
class l10n:
    def __init__(self,lang = "en_US"):
        self.lang = lang
        print("This class is not ready to be instantiated now. Please don't instantiate and directly use the functions")
    warnSuccess = lambda x,c: '警告成功。該用戶現在共有 '+x+' 個警告。'+(('\n'+c) if (c and c != "None") else '')
    delWarnSuccess = lambda t,a,r,c: '該條訊息曾於 '+t+' 被 '+a+' 以理由「 '+r+' 」警告過。警告現已取消。該用戶現有 '+c+' 個警告。如該用戶已因警告遭致處分，請管理員亦一同處置。'
    warnedFail = lambda t,a,r: '抱歉，該條訊息已於 '+t+' 被 '+a+' 以理由「 '+r+' 」警告過。'
    epochToISO = lambda x: datetime.datetime.fromtimestamp(x).isoformat()
    notifyWarn = lambda i,t,u,uid,a,c,m,r,g: ("" if g is None else (g+"\n"))+"ID: "+i+"\nTime: "+t+"\nUser "+u+" ("+uid+") warned by "+a+' with reason:\n'+r+'\nCurrent Warn #'+c+'\nMessage:\n'+(m if m else '&lt;Multimedia Message&gt;')
    notifyDelwarn = lambda i,t,u,uid,a,c,m,r,g: ("" if g is None else (g+"\n"))+"ID: "+i+'\nTime: '+t+"\n"+a+" cancelled a warning for user "+u+" ("+uid+") with reason:\n"+r+'\nCurrent Warn #:'+c+'\nMessage:\n' + (m if m else '&lt;Multimedia Message&gt;')
    notifyG11 = lambda t,u,uid,a,m,g: ("" if g is None else (g+"\n"))+"Time: "+t+"\nUser "+u+" ("+uid+") killed by "+a+' with reason: #G11\nMessage:\n'+getMsgText(m)
    notifyPunish = lambda p,t,u,uid,g: ("" if g is None else (g+"\n"))+"User "+u+" ("+uid+") has been "+p+" till "+t+"."
    notifyPunishFail = lambda p,t,u,uid,g: ("" if g is None else (g+"\n"))+"User "+u+" ("+uid+") need to be "+p+" till "+t+", but the operation failed."

def initiateDB(fName,outdev):
    try:
        conf = sqldb.sqliteDB(fName,'config')
    except sqldb.sqliteDBError:
        raise APIError('DB','Corrupted configuration table')
    if conf.getItem('dbver','value') != '1.5':
        raise APIError('DB','Database schema version is incompatible')
    try:
        group = sqldb.sqliteDB(conf.db,'group')
    except sqldb.sqliteDBError:
        raise APIError('DB','Corrupted group table')
    try:
        warn = sqldb.sqliteDB(conf.db,'warn')
    except sqldb.sqliteDBError:
        raise APIError('DB','Corrupted warn table')
    try:
        admin = sqldb.sqliteDB(conf.db,'admin')
    except sqldb.sqliteDBError:
        raise APIError('DB','Corrupted admin table')
    try:
        auth = sqldb.sqliteDB(conf.db,'auth')
    except sqldb.sqliteDBError:
        raise APIError('DB','Corrupted auth table')
    outdev.writeln('DB File '+fName+' loaded.')
    return (conf,group,warn,admin,auth)

def addGroup(gid,db,outdev):
    if not db[1].hasItem(str(gid)):
        db[1].addItem([str(gid)]+[str(i) for i in db[1].data.execute('select * from "group" where header="default"').fetchone()[1:]])
        outdev.writeln('I\'ve been added to a new group '+str(gid)) #+': '+message['message']['chat']['title']+'.')
    else:
        outdev.writeln('I\'ve been added back to group '+str(gid)) #+': '+message['message']['chat']['title']+'.')

def randomID():
    return hex(int.from_bytes(os.urandom(8),'big'))[2:]

def countWarn(db,gid,uid):
    if db[1].getItem(str(gid),'fade') == '0':
        return db[2].data.execute('select count(header) from warn where user=? and "group"=?',(str(uid),str(gid))).fetchone()[0]
    elif db[1].getItem(str(gid),'fade')[0] == '1':
        beforeTime = time.time() - int(db[1].getItem(str(gid),'fade').split('|')[1])
        counter = 0
        warnRec = db[2].data.execute('select time from warn where user=? and "group"=? and header != \'header\'',(str(uid),str(gid))).fetchall()
        # print(warnRec,beforeTime)
        for item in warnRec:
            counter += 1 if int(item[0]) > beforeTime else 0
        return counter

def getName(uid,gid,api,lookup={}):
    if uid in lookup:
        return '@'+lookup[uid]
    try:
        result = api.query('getChatMember',{'chat_id':int(gid),'user_id':int(uid)},retry=1)
    except APIError:
        return 'a former member of this group'
    return getNameRep(result['user'])

def getNameRep(userObj):
    name = ''
    if 'username' in userObj:
        name = userObj['username']
    elif 'last_name' in userObj:
        name = userObj['first_name']+' '+userObj['last_name']
    else:
        name = userObj['first_name']
    if 'id' in userObj:
        return '<a href="tg://user?id='+str(userObj['id'])+'>'+name+'</a>'
    else:
        return '@'+name

def getMsgText(msgObj):
    return msgObj['text'] if 'text' in msgObj else '&lt;Multimedia Message&gt;'

def getAdminList(adminList):
    result = {}
    for item in adminList:
        if item['status'] == 'creator' or (item['status'] == 'administrator' and 'can_restrict_members' in item):
            result[item['user']['id']] = getNameRep(item['user'])
    return result

def canPunish(api,gid):
    tmp = api.query('getChatMember',{'chat_id':gid,'user_id':api.info['id']})
    return tmp['status'] == 'creator' or ('can_restrict_members' in tmp and tmp['can_restrict_members'])

def processWarn(db,api,uo,gid,ts,reply):
    cannotPunish = not canPunish(api,gid)
    uid = str(uo['id'])
    uname = getNameRep(uo)
    api.logOut.writeln('Processing actual punishment...')
    warnNum = countWarn(db,gid,uid)
    if warnNum == 0:
        api.logOut.writeln("It does not qualify any warning.")
        return
    if warnNum > 5:
        warnNum = 5
    api.logOut.writeln(str(gid)+' '+str(db[1].hasItem(str(gid)))+' warning '+str(warnNum))
    punish = db[1].getItem(str(gid),'warning'+str(warnNum)).split('|')
    api.logOut.writeln(punish)
    # 0 - Nothing
    # 1 - Mute
    # 2 - Kick
    if punish[0] == '1':
        if len(punish) == 1 or punish[1] == '0':
            # Forever
            ## Cannot punish
            if cannotPunish:
                api.sendMessage(gid,'該用戶應當被永久禁言，然而機器人流下了沒有權利的淚水。',{'reply_to_message_id':reply})
            ## Can punish
            else:
                api.logOut.writeln(str(api.query('restrictChatMember',{'chat_id':gid,'user_id':uid,'until_date':int(time.time()+10),'can_send_messages':False})))
                api.sendMessage(gid,'該用戶已被永久禁言。',{'reply_to_message_id':reply})
                tmp = db[1].getItem(str(gid),'notify').split('|')
                if tmp[0] != 'None':
                    api.sendMessage(tmp[0],l10n.notifyPunish('silenced','forever',uname,uid,None if len(tmp) == 1 else tmp[1]))
        elif int(ts)+int(punish[1]) - time.time() < 60:
            api.sendMessage(gid,'該用戶應當被禁言至 '+l10n.epochToISO(int(ts)+int(punish[1]))+' 然而由於處理時間已過，故此不作處分。',{'reply_to_message_id':reply})
        else:
            ## Cannot punish
            if cannotPunish:
                api.sendMessage(gid,'該用戶應當被禁言至 '+l10n.epochToISO(int(ts)+int(punish[1]))+' ，然而機器人流下了沒有權利的淚水。',{'reply_to_message_id':reply})
            ## Can punish
            else:
                api.logOut.writeln(str(api.query('restrictChatMember',{'chat_id':gid,'user_id':uid,'until_date':int(ts)+int(punish[1]),'can_send_messages':False})))
                api.sendMessage(gid,'該用戶已被禁言至 '+l10n.epochToISO(int(ts)+int(punish[1]))+' 。',{'reply_to_message_id':reply})
                tmp = db[1].getItem(str(gid),'notify').split('|')
                if len(tmp) == 1:
                    tmp.append(None)
                if tmp[0] != 'None':
                    api.sendMessage(tmp[0],l10n.notifyPunish('silenced',l10n.epochToISO(int(ts)+int(punish[1])),uname,uid,tmp[1]))
    if punish[0] == '2' or punish[0] == '3':
        if len(punish) == 1 or punish[1] == '0' or punish[0] == '3':
            ## Cannot punish
            if cannotPunish:
                api.sendMessage(gid,'該用戶應當被永久封禁，然而機器人流下了沒有權利的淚水。',{'reply_to_message_id':reply})
            ## Can punish
            else:
                api.logOut.writeln(str(api.query('kickChatMember',{'chat_id':gid,'user_id':uid,'until_date':int(time.time()+10)})))
                api.sendMessage(gid,'該用戶已被永久封禁。',{'reply_to_message_id':reply})
                tmp = db[1].getItem(str(gid),'notify').split('|')
                if tmp[0] != 'None':
                    api.sendMessage(tmp[0],l10n.notifyPunish('kicked','forever',uname,uid,None if len(tmp) == 1 else tmp[1]))
        elif int(ts)+int(punish[1]) - time.time() < 60:
            api.sendMessage(gid,'該用戶應當被封禁至 '+l10n.epochToISO(int(ts)+int(punish[1]))+' 然而由於處理時間已過，故此不作處分。',{'reply_to_message_id':reply})
        else:
            ## Cannot punish
            if cannotPunish:
                api.sendMessage(gid,'該用戶應當被封禁至 '+l10n.epochToISO(int(ts)+int(punish[1]))+' 然而機器人流下了沒有權利的淚水。',{'reply_to_message_id':reply})
            # Can punish
            else:
                api.logOut.writeln(str(api.query('kickChatMember',{'chat_id':gid,'user_id':uid,'until_date':int(ts)+int(punish[1])})))
                api.sendMessage(gid,'該用戶已被封禁至 '+l10n.epochToISO(int(ts)+int(punish[1]))+' 。',{'reply_to_message_id':reply})
                tmp =  db[1].getItem(str(gid),'notify').split('|')
                if tmp[0] != 'None':
                    api.sendMessage(tmp[0],l10n.notifyPunish('kicked',l10n.epochToISO(int(ts)+int(punish[1])),uname,uid,None if len(tmp) == 1 else tmp[1]))

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
        result += '警告期限：警告永不過期\n'
    elif data[0] == '1':
        result += '警告期限：'+str(datetime.timedelta(seconds=int(data[1])))+'\n'
    elif data[0] == '2':
        result += '警告期限：每月 1 日解除 '+data[1]+' 個警告。\n'
    data = db[1].getItem(str(gid),'notify')
    result += '警告日誌：'+data
    return result

def processCheck(msg,api,db):
    if msg['message']['chat']['type'] == 'private':
    # Check the warnings for the user itself across the globe
        api.sendMessage(message['message']['chat']['id'],'Checking your warnings... Not Implemented D:',{'reply_to_message_id':message['message']['message_id']})
    elif msg['message']['chat']['type'] == 'supergroup':
    # Check the warnings for the user itself within the group
        data = db[2].data
        api.sendMessage(message['message']['chat']['id'],'Checking your warnings... Not Implemented.',{'reply_to_message_id':message['message']['message_id']})

def processItem(message,db,api):
    #print(message)
    api.logOut.writeln(str(message['update_id'])+' being processed...')
    if 'message' not in message:
        return
    # KillDice
    if 'dice' in message['message'] and 'killDice' in api.info and message['message']['chat']['id'] in api.info['killDice']:
        api.delayQuery(api.info['killDice'][message['message']['chat']['id']],'deleteMessage',{'chat_id':message['message']['chat']['id'],'message_id':message['message']['message_id']})
    if 'sticker' in message['message'] and 'set_name' in message['message']['sticker']:
        try:
            tmp = db[1].getItem(str(message['message']['chat']['id']),'bansticker').split('|')
        except sqldb.sqliteDBError:
            pass
        else:
            if message['message']['sticker']['set_name'] in tmp:
                try:
                    api.query('deleteMessage',{'chat_id':message['message']['chat']['id'],'message_id':message['message']['message_id']},retry=1)
                    api.sendMessage(message['message']['chat']['id'],getNameRep(message['message']['from'])+' 發送的一個 Sticker 由於被禁止於此群使用，已被刪除。')
                except APIError:
                    api.sendMessage(message['message']['chat']['id'],'注意：本 Sticker 禁止於此群使用。',{'reply_to_message_id':message['message']['message_id']})
    if 'text' in message['message'] and message['message']['text']:
        # Process bot command
        if message['message']['text'][0] == '/':
            stripText = message['message']['text'].split(' ',1)[0]
            if '@'+api.info['username'] in stripText:
                stripText=stripText[:-len(api.info['username'])-1]
            stripText = stripText.lower()
            if stripText == '/ping':
                api.sendMessage(message['message']['chat']['id'],'Hell o\'world! It took '+str(time.time()-message['message']['date'])+' seconds!',{'reply_to_message_id':message['message']['message_id']})
            if stripText == '/anyone':
                api.sendMessage(message['message']['chat']['id'],'沒有人，你悲劇了。',{'reply_to_message_id':message['message']['reply_to_message']['message_id'] if 'reply_to_message' in message['message'] else message['message']['message_id']})
                if 'reply_to_message' in message['message']:
                    try:
                        api.query('deleteMessage',{'chat_id':message['message']['chat']['id'],'message_id':message['message']['message_id']})
                    except APIError:
                        pass
            ## EASTER EGGS
            elif stripText == '/stupid_bluedeck':
                api.sendMessage(message['message']['chat']['id'],'藍桌，真的是笨桌！',{'reply_to_message_id':message['message']['message_id']})
            elif stripText == '/wpwpw':
                api.sendMessage(message['message']['chat']['id'],'白磷白磷白',{'reply_to_message_id':message['message']['message_id']})
            elif stripText == '/gay':
                gay = 0
                for i in range(5):
                    tmp = os.urandom(1)[0]
                    for j in range(5):
                        gay += tmp & 1 
                        tmp >>= 1
                gay = gay * 4 + (os.urandom(1)[0] & 3)
                api.sendMessage(message['message']['chat']['id'],getNameRep(message['message']['from'])+' is '+str(gay)+'% gay!',{'reply_to_message_id':message['message']['message_id']})
            elif stripText == '/taf':
                tafQuery = message['message']['text'].split(' ',1)
                if len(tafQuery) == 2 and len(tafQuery[1]) == 4:
                    try:
                        tafData = ur.urlopen('http://localhost/cgi-bin/taf.cgi?airport='+tafQuery[1]).read().decode('UTF-8').strip()
                    except ue.HTTPError:
                        tafData = 'Airport TAF lookup failed. Maybe wrong airport code?'
                else:
                    tafData = 'Usage: <pre>/taf &lt;ICAO code&gt;</pre>'
                api.sendMessage(message['message']['chat']['id'],tafData,{'reply_to_message_id':message['message']['message_id']})
            elif stripText == '/metar':
                tafQuery = message['message']['text'].split(' ',1)
                if len(tafQuery) == 2 and len(tafQuery[1]) == 4:
                    try:
                        tafData = ur.urlopen('http://localhost/cgi-bin/taf.cgi?type=metar&airport='+tafQuery[1]).read().decode('UTF-8').strip()
                    except ue.HTTPError:
                        tafData = 'Airport METAR lookup failed. Maybe wrong airport code?'
                else:
                    tafData = 'Usage: <pre>/metar &lt;ICAO code&gt;</pre>'
                api.sendMessage(message['message']['chat']['id'],tafData,{'reply_to_message_id':message['message']['message_id']})
            elif stripText in ('/iataicao','/icaoiata'):
                tafQuery = message['message']['text'].split(' ',1)
                if len(tafQuery) == 2 and len(tafQuery[1]) in (3,4):
                    try:
                        tafData = ur.urlopen('http://localhost/cgi-bin/airportinfo.cgi?info='+('ICAO' if len(tafQuery[1]) == 3 else 'IATA')+'&airport='+tafQuery[1]).read().decode('UTF-8').strip()
                    except ue.HTTPError:
                        tafData = 'Airport info lookup failed.'
                else:
                    tafData = 'Usage: <pre>/icaoiata &lt;ICAO code&gt;|&lt;IATA code&gt;</pre>'
                api.sendMessage(message['message']['chat']['id'],tafData,{'reply_to_message_id':message['message']['message_id']})
            elif stripText == '/airportname':
                tafQuery = message['message']['text'].split(' ',1)
                if len(tafQuery) == 2 and len(tafQuery[1]) in (3,4):
                    try:
                        tafData = ur.urlopen('http://localhost/cgi-bin/airportinfo.cgi?info=Info&airport='+tafQuery[1]).read().decode('UTF-8').strip()
                    except ue.HTTPError:
                        tafData = 'Airport info lookup failed.'
                else:
                    tafData = 'Usage: <pre>/airportname &lt;ICAO code&gt;|&lt;IATA code&gt;</pre>'
                api.sendMessage(message['message']['chat']['id'],tafData,{'reply_to_message_id':message['message']['message_id']})
            elif stripText == '/killsticker':
                if 'reply_to_message' not in message['message'] or 'sticker' not in message['message']['reply_to_message']:
                    api.sendMessage(message['message']['chat']['id'],"用法：使用 /killsticker 回覆 Sticker 以禁用該 Sticker 所屬的 Sticker set。",{"reply_to_message_id":message['message']['message_id']})
                elif 'set_name' not in message['message']['reply_to_message']['sticker'] or '|' in message['message']['reply_to_message']['sticker']['set_name']:
                    api.sendMessage(message['message']['chat']['id'],"抱歉，機器人無法禁用該 Sticker 所屬的 Sticker set。",{"reply_to_message_id":message['message']['message_id']})
                else:
                    queryBy = api.query("getChatMember",{"chat_id":message['message']['chat']['id'],"user_id":message['message']['from']['id']})
                    if queryBy['status'] not in ('creator','administrator'):
                        api.sendMessage(message['message']['chat']['id'],"抱歉，僅有濫權管理員方可使用 /killsticker 於本群組禁止使用該 Sticker set。",{"reply_to_message_id":message['message']['message_id']})
                    else:
                        tmp = db[1].getItem(str(message['message']['chat']['id']),'bansticker')
                        if message['message']['reply_to_message']['sticker']['set_name'] not in tmp.split('|'):
                            tmp = db[1].chgItem(str(message['message']['chat']['id']),'bansticker',tmp+('|' if tmp else '')+message['message']['reply_to_message']['sticker']['set_name'])
                        api.sendMessage(message['message']['chat']['id'],"該 Sticker 所屬的 Sticker set "+message['message']['reply_to_message']['sticker']['set_name']+' 已被禁用。',{"reply_to_message_id":message['message']['message_id']})
            elif stripText == '/killdice':
                queryBy = api.query("getChatMember",{"chat_id":message['message']['chat']['id'],"user_id":message['message']['from']['id']})
                if queryBy['status'] not in ('creator','administrator'):
                    api.sendMessage(message['message']['chat']['id'],"抱歉，僅有濫權管理員方可使用 /killdice 刪除未來的 Dice/Dart。",{"reply_to_message_id":message['message']['message_id']})
                else:
                    diceQuery = message['message']['text'].split(' ',1)
                    if len(diceQuery) != 2:
                        api.sendMessage(message['message']['chat']['id'],"Usage: /killdice delay|off",{'reply_to_message_id':message['message']['message_id']})
                    elif diceQuery[1] == "off":
                        if 'killDice' not in api.info or message['message']['chat']['id'] not in api.info['killDice']:
                            api.sendMessage(message['message']['chat']['id'],"抱歉，此處並未啟用 /killdice。",{'reply_to_message_id':message['message']['message_id']})
                        else:
                            api.info['killDice'].pop(message['message']['chat']['id'])
                            api.sendMessage(message['message']['chat']['id'],"此處已停用 /killdice。",{'reply_to_message_id':message['message']['message_id']})
                    else:
                        try:
                            tmp = int(diceQuery[1])
                        except ValueError:
                            api.sendMessage(message['message']['chat']['id'],"Usage: /killdice delay|off",{'reply_to_message_id':message['message']['message_id']})
                        else:
                            if 'killDice' not in api.info:
                                api.info['killDice'] = {}
                            api.info['killDice'][message['message']['chat']['id']] = tmp
                            api.sendMessage(message['message']['chat']['id'],"機器人將試圖於發出 "+diceQuery[1]+" 秒後刪除 Dice/Dart。",{'reply_to_message_id':message['message']['message_id']})
            elif stripText == '/poem':
                api.sendMessage(message['message']['chat']['id'],ur.urlopen('http://localhost/cgi-bin/poem.cgi').read().decode('UTF-8').strip(),{'reply_to_message_id':message['message']['message_id']})
            ##
            elif stripText == '/groupid':
                api.sendMessage(message['message']['chat']['id'],'Group ID: '+str(message['message']['chat']['id']),{'reply_to_message_id':message['message']['message_id']})
            elif stripText == "/userid":
                api.sendMessage(message['message']['chat']['id'],'User ID: '+str(message['message']['reply_to_message']['forward_from']['id'] if ('reply_to_message' in message['message'] and 'forward_from' in message['message']['reply_to_message']) else message['message']['reply_to_message']['from']['id'] if 'reply_to_message' in message['message'] else message['message']['from']['id']),{'reply_to_message_id':message['message']['message_id']})
            elif stripText == '/lastid':
                api.sendMessage(message['message']['chat']['id'],'Last Message ID: '+str(message['update_id']),{'reply_to_message_id':message['message']['message_id']})
            elif stripText == '/uptime':
                api.sendMessage(message['message']['chat']['id'],'Uptime:\n<pre>'+subprocess.check_output('uptime').decode().strip()+'</pre>\nThread: '+str(api.clearDelayQuery()),{'parse_mode':'HTML','reply_to_message_id':message['message']['message_id']})
            elif stripText == '/freedb':
                for item in db:
                    item.updateDB()
                api.sendMessage(message['message']['chat']['id'],'Database unlocked.',{'reply_to_message_id':message['message']['message_id']})
            elif stripText == '/webpassword':
                target = None
                if message['message']['chat']['type'] in ('group','supergroup'):
                    target = message['message']['chat']['id']
                elif message['message']['chat']['type'] == 'private':
                    tmp = message['message']['text'].split(' ',1)
                    if len(tmp) == 1:
                        api.sendMessage(message['message']['chat']['id'],"Usage: /webpassword GroupID",{'reply_to_message_id':message['message']['message_id']})
                    else:
                        target = tmp[1].strip()
                if target != None:
                    try:
                        tmp = api.query('getChat',{'chat_id':target})
                        target = tmp['id']
                        targetName = tmp['username'] if 'username' in tmp else tmp['title'] if 'title' in tmp else str(target)
                        tmp = api.query('getChatMember',{'chat_id':target,'user_id':message['message']['from']['id']},retry=0)
                    except APIError:
                        api.sendMessage(message['message']['chat']['id'],'Failed to check group permission.',{'reply_to_message_id':message['message']['message_id']})
                    else:
                        if tmp['status'] not in ('administrator','creator'):
                            api.sendMessage(message['message']['chat']['id'],'You are not admin of the group you are requesting API key for.',{'reply_to_message_id':message['message']['message_id']})
                        else:
                            try:
                                tmp = api.query('sendMessage',{'chat_id':message['message']['from']['id'],'text':'Generating web API key...'},retry=0)['message_id']
                            except APIError:
                                api.sendMessage(message['message']['chat']['id'],'You need to PM me first.',{'reply_to_message_id':message['message']['message_id']})
                            else:
                                if message['message']['chat']['type'] in ('group','supergroup'):
                                    api.sendMessage(message['message']['chat']['id'],'Please check your PM.',{'reply_to_message_id':message['message']['message_id']})
                                key = base64.b64encode(os.urandom(15),b'_-').decode('ASCII')
                                db[4].addItem([str(message['message']['from']['id']),key,str(int(time.time())),str(target),""])
                                api.sendMessage(message['message']['from']['id'],'Your web API key to group '+str(targetName)+' is:\n<pre>'+str(message['message']['from']['id'])+':'+key+'</pre>\n\nThis key would be valid till the earliest of '+db[0].getItem('keyexp','value')+' s after the last use, or a new key is generated for you.',{'parse_mode':'HTML'})
                                try:
                                    api.query('deleteMessage',{'chat_id':message['message']['from']['id'],'message_id':tmp})
                                except APIError:
                                    pass
            elif stripText == '/online':
                if 'username' not in message['message']['from']:
                    tmp = api.sendMessage(message['message']['chat']['id'],getNameRep(message['message']['from'])+': 抱歉，您需要擁有一個 Telegram 用戶名稱方可加入線上管理員列表。')
                elif db[3].hasItem(str(message['message']['from']['id'])):
                    tmp = api.sendMessage(message['message']['chat']['id'],getNameRep(message['message']['from'])+': 您已在線上管理員列表中。請使用 /offline 將您從該列表移除。')
                else:
                    tmp = message['message']['text'].split(' ',1)
                    if len(tmp) == 2 and tmp[1].strip().lower() == 'no pm':
                        db[3].addItem([str(message['message']['from']['id']),str(int(time.time())),'nopm'])
                    else:
                        db[3].addItem([str(message['message']['from']['id']),str(int(time.time())),str(int(time.time()))])
                    tmp = api.sendMessage(message['message']['chat']['id'],getNameRep(message['message']['from'])+': 您已成功加入線上管理員列表。請使用 /offline 將您從該列表移除。')
                if message['message']['chat']['type'] != 'private':
                    api.delayQuery(30,'deleteMessage',{'chat_id':message['message']['chat']['id'],'message_id':tmp})
                try:
                    api.query('deleteMessage',{'chat_id':message['message']['chat']['id'],'message_id':message['message']['message_id']})
                except APIError:
                    print('Message https://t.me/'+str(message['message']['chat']['id'])+'/'+str(message['message']['message_id'])+' failed to be removed.')
            elif stripText == '/offline':
                if db[3].hasItem(str(message['message']['from']['id'])):
                    db[3].remItem(str(message['message']['from']['id']))
                    tmp = api.sendMessage(message['message']['chat']['id'],getNameRep(message['message']['from'])+': 您已成功自線上管理員列表中移除。')
                else:
                    tmp = api.sendMessage(message['message']['chat']['id'],getNameRep(message['message']['from'])+': 您不在線上管理員列表中。請使用 /online 將您加入該列表。')
                if message['message']['chat']['type'] != 'private':
                    api.delayQuery(30,'deleteMessage',{'chat_id':message['message']['chat']['id'],'message_id':tmp})
                try:
                    api.query('deleteMessage',{'chat_id':message['message']['chat']['id'],'message_id':message['message']['message_id']})
                except APIError:
                    print('Message https://t.me/'+str(message['message']['chat']['id'])+'/'+str(message['message']['message_id'])+' failed to be removed.')
            elif stripText == "/admin":
                if message['message']['chat']['type'] not in ('supergroup','group'):
                    api.sendMessage(message['message']['chat']['id'],'抱歉，您僅可在群組或超級群組中呼叫管理員。',{'reply_to_message_id':message['message']['message_id']})
                elif 'reply_to_message' not in message['message']:
                    api.sendMessage(message['message']['chat']['id'],'使用 /admin 呼叫管理員時，請回覆需要管理員注意的消息。濫用該指令可能導致您被封禁，請慎重使用。',{'reply_to_message_id':message['message']['message_id']})
                else:
                    adminList = api.query('getChatAdministrators',{'chat_id':message['message']['chat']['id']})
                    result = []
                    for item in adminList:
                        if ('username' in item['user']) and db[3].hasItem(str(item['user']['id'])):
                            if db[3].getItem(str(item['user']['id']),'last') == 'nopm':
                                result.append(item['user']['username'])
                            else:
                                result.append('@'+item['user']['username'])
                    if result:
                        api.sendMessage(message['message']['chat']['id'],', '.join(result)+'，有人找管理啦。',{'reply_to_message_id':message['message']['message_id']})
                    else:
                        api.sendMessage(message['message']['chat']['id'],'抱歉，本群暫無在線上的管理員可供呼叫。',{'reply_to_message_id':message['message']['message_id']})
            elif stripText == "/warn":
                api.sendMessage(message['message']['chat']['id'],'本機器人可以用於警告用戶，請使用 #warn 附帶理由以作出警告。',{'reply_to_message_id':message['message']['message_id']})
            elif stripText == '/warnrule':
                if message['message']['chat']['type']!='supergroup':
                    api.sendMessage(message['message']['chat']['id'],'抱歉，警告功能僅在超級群組有效。',{'reply_to_message_id':message['message']['message_id']})
                else:
                    api.sendMessage(message['message']['chat']['id'],processRule(message['message']['chat']['id'],db),{'reply_to_message_id':message['message']['message_id']})
            elif stripText == '/warncheck':
                processCheck(message,api,db)
        # Process hashtag
        # Hashtag shall only be accepted in supergroup issued by admin
        elif message['message']['text'][0] == '#':
            if len(message['message']['text'])>4 and message['message']['text'][1:5].lower() == 'warn':
                if message['message']['chat']['type']!='supergroup':
                    api.sendMessage(message['message']['chat']['id'],'抱歉，警告功能僅在超級群組有效。',{'reply_to_message_id':message['message']['message_id']})
                else:
                    adminList = getAdminList(api.query('getChatAdministrators',{'chat_id':message['message']['chat']['id']}))
                    if message['message']['from']['id'] not in adminList:
                        api.sendMessage(message['message']['chat']['id'],'抱歉，僅有濫權管理員方可使用 #WARN 警告其他用戶。',{'reply_to_message_id':message['message']['message_id']})
                    elif 'reply_to_message' not in message['message']:
                        api.sendMessage(message['message']['chat']['id'],'用法錯誤：請回覆需要被警告的訊息。',{'reply_to_message_id':message['message']['message_id']})
                    elif db[2].data.execute('SELECT count(header) from warn where "group"=? and "text"=?',(str(message['message']['chat']['id']),str(message['message']['reply_to_message']['message_id']))).fetchone()[0]:
                        warnInfo = db[2].data.execute('SELECT time,admin,reason from warn where "group"=? and "text"=?',(str(message['message']['chat']['id']),str(message['message']['reply_to_message']['message_id']))).fetchone()
                        api.sendMessage(message['message']['chat']['id'],l10n.warnedFail(l10n.epochToISO(int(warnInfo[0])),getName(warnInfo[1],message['message']['chat']['id'],api,adminList),warnInfo[2]),{'reply_to_message_id':message['message']['message_id']})
                    else:
                        warnInfo = [int(time.time()),message['message']['chat']['id'],message['message']['reply_to_message']['from']['id'],message['message']['reply_to_message']['message_id'],message['message']['from']['id'],message['message']['text'][5:].strip()]
                        if not warnInfo[-1]:
                            api.sendMessage(message['message']['chat']['id'],'用法錯誤：請提供警告理由，使對方明白何處做錯。',{'reply_to_message_id':message['message']['message_id']})
                        elif warnInfo[2] in adminList:
                            api.sendMessage(message['message']['chat']['id'],'竟敢試圖警告管理員，你的請求被濫權掉了。',{'reply_to_message_id':message['message']['message_id']})
                        elif warnInfo[2] == api.info['id'] or message['message']['reply_to_message']['from']['is_bot']:
                            api.sendMessage(message['message']['chat']['id'],'竟敢試圖警告機器人，你的請求被濫權掉了。',{'reply_to_message_id':message['message']['message_id']})
                        else:
                            wid = [randomID()]
                            while db[2].hasItem(wid[0]):
                                wid = [randomID()]
                            db[2].addItem(wid+warnInfo)
                            rep = api.sendMessage(message['message']['chat']['id'],l10n.warnSuccess(str(countWarn(db,warnInfo[1],warnInfo[2])),db[1].getItem(str(message['message']['chat']['id']),'msg')),{'reply_to_message_id':message['message']['message_id']})
                            #  i,t,u,uid,a,c,m,r,g
                            tmp = db[1].getItem(str(message['message']['chat']['id']),'notify').split('|')
                            if tmp[0] != 'None':
                                api.sendMessage(tmp[0],l10n.notifyWarn(wid[0],l10n.epochToISO(warnInfo[0]),getNameRep(message['message']['reply_to_message']['from']),str(warnInfo[2]),getNameRep(message['message']['from']),str(countWarn(db,warnInfo[1],warnInfo[2])),message['message']['reply_to_message']['text'] if 'text' in message['message']['reply_to_message'] else None,warnInfo[-1],None if len(tmp) == 1 else tmp[1]))
                            # api.logOut.writeln('Warned '+getNameRep(message['message']['reply_to_message']['from'])+' in group '+message['message']['chat']['id'])
                            processWarn(db,api,message['message']['reply_to_message']['from'],warnInfo[1],message['message']['reply_to_message']['date'],rep)
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
                        db[2].remItem(warnInfo[-1])
                        # api.logOut.writeln('Removed warning for '+getNameRep(message['message']['reply_to_message']['from'])+' in group '+message['message']['chat']['id'])
                        api.sendMessage(message['message']['chat']['id'],l10n.delWarnSuccess(l10n.epochToISO(int(warnInfo[0])),getName(warnInfo[1],message['message']['chat']['id'],api,adminList),warnInfo[2],str(countWarn(db,message['message']['chat']['id'],message['message']['reply_to_message']['from']['id']))),{'reply_to_message_id':message['message']['message_id']})
                        #  i,t,u,uid,a,c,m,r
                        tmp = db[1].getItem(str(message['message']['chat']['id']),'notify').split('|')
                        if tmp[0] != 'None':
                            api.sendMessage(tmp[0],l10n.notifyDelwarn(warnInfo[-1],l10n.epochToISO(int(time.time())),getNameRep(message['message']['reply_to_message']['from']),str(message['message']['reply_to_message']['from']['id']),getNameRep(message['message']['from']),str(countWarn(db,message['message']['chat']['id'],message['message']['reply_to_message']['from']['id'])),message['message']['reply_to_message']['text'] if 'text' in message['message']['reply_to_message'] else None,message['message']['text'][8:].strip(),None if len(tmp) == 1 else tmp[1]))
            elif len(message['message']['text'])>3 and message['message']['text'][1:4].lower() == 'g11':
                if message['message']['chat']['type']!='supergroup':
                    api.sendMessage(message['message']['chat']['id'],'抱歉，警告功能僅在超級群組有效。',{'reply_to_message_id':message['message']['message_id']})
                elif db[1].getItem(str(message['message']['chat']['id']),'notify') == 'None':
                    api.sendMessage(message['message']['chat']['id'],'抱歉，該功能僅在已配置群組日誌的群可用。您可以直接使用濫權三連（刪除消息，封禁用戶，舉報用戶）處理 #G11。',{'reply_to_message_id':message['message']['message_id']})
                else:
                    adminList = getAdminList(api.query('getChatAdministrators',{'chat_id':message['message']['chat']['id']}))
                    if message['message']['from']['id'] not in adminList:
                        api.sendMessage(message['message']['chat']['id'],'抱歉，僅有濫權管理員方可使用 #G11 快速踢出其他用戶。',{'reply_to_message_id':message['message']['message_id']})
                    elif 'reply_to_message' not in message['message']:
                        api.sendMessage(message['message']['chat']['id'],'用法錯誤：請回覆需要被處理的訊息。',{'reply_to_message_id':message['message']['message_id']})
                    elif message['message']['reply_to_message']['from']['id'] in adminList:
                        api.sendMessage(message['message']['chat']['id'],'竟敢試圖說管理員有 #G11 ，你的請求被濫權掉了。',{'reply_to_message_id':message['message']['message_id']})
                    elif message['message']['reply_to_message']['from']['id'] == api.info['id'] or message['message']['reply_to_message']['from']['is_bot']:
                        api.sendMessage(message['message']['chat']['id'],'竟敢試圖 #G11 機器人，你的請求被濫權掉了。',{'reply_to_message_id':message['message']['message_id']})
                    elif not canPunish(api,message['message']['chat']['id']):
                        api.sendMessage(message['message']['chat']['id'],'雖然很想處理掉這個 #G11 ，然而本機器人流下了沒有權利的淚水。您可以直接使用濫權三連（刪除消息，封禁用戶，舉報用戶）處理 #G11。',{'reply_to_message_id':message['message']['message_id']})
                    else:
                        ## Process G11
                        api.query('kickChatMember',{'chat_id':message['message']['chat']['id'],'user_id':message['message']['reply_to_message']['from']['id']})
#                        api.sendMessage(db[1].getItem(str(message['message']['chat']['id'],'notify')),l10n.notifyG11(str(int(time.time())),getNameRep(message['message']['reply_to_message']['from']),str(message['message']['reply_to_message']['from']['id']),getNameRep(message['message']['from']),message['message']['reply_to_message']))
                        tmp = db[1].getItem(str(message['message']['chat']['id']),'notify').split('|')
                        api.sendMessage(tmp[0],("" if len(tmp) == 1 else tmp[1]+'\n')+getNameRep(message['message']['from'])+" has killed a #G11 from "+getNameRep(message['message']['reply_to_message']['from'])+"("+ str(message['message']['reply_to_message']['from']['id'])+") with content of\n"+getMsgText(message['message']['reply_to_message']))
                        try:
                            api.query('deleteMessage',{'chat_id':message['message']['chat']['id'],'message_id':message['message']['reply_to_message']['message_id']})
                        except APIError:
                            api.sendMessage(message['message']['chat']['id'],'機器人似乎在試圖刪除該消息時遇到了一些困難。',{'reply_to_message_id':message['message']['message_id']})
                        else:
                            api.sendMessage(message['message']['chat']['id'],'機器人成功處理掉了一個 #G11 ！',{'reply_to_message_id':message['message']['message_id']})
            elif len(message['message']['text'])>11 and message['message']['text'][1:12].lower() == 'setwarnrule':
                if message['message']['chat']['type']!='supergroup':
                    api.sendMessage(message['message']['chat']['id'],'抱歉，警告功能僅在超級群組有效。',{'reply_to_message_id':message['message']['message_id']})
                else:
                    reqUser = api.query('getChatMember',{'chat_id':message['message']['chat']['id'],'user_id':message['message']['from']['id']})
                    if (reqUser['status'] != 'creator') and not (('can_promote_members' in reqUser) and reqUser['can_promote_members']):
                        api.sendMessage(message['message']['chat']['id'],'抱歉，僅有濫權管理員方可使用 #SETWARNRULE 修改警告懲罰規則。',{'reply_to_message_id':message['message']['message_id']})
                    else:
                        newRule = message['message']['text'].split('\n')[1:]
                        if not newRule:
                            api.sendMessage(message['message']['chat']['id'],"規則說明：每行一條，使用下列格式聲明規則\n\n規則類型：\n0: 口頭警告\n1|x: 禁言 x 秒\n2|x: 封禁 x 秒\n3: 永封\n\n警告規則不超過 5 條",{"reply_to_message_id":message['message']['message_id']})
                        else:
                            dbRule = []
                            for i in range(len(newRule)):
                                tmp = newRule[i].split('|')
                                if (not tmp[0]) or (tmp[0] not in '0123') or ((tmp[0] in '03') and len(tmp) != 1) or ((tmp[0] in '12') and len(tmp) not in (1,2)):
                                    api.sendMessage(message['message']['chat']['id'],"規則格式錯誤：請參見 #SETWARNRULE 規則說明。",{"reply_to_message_id":message['message']['message_id']})
                                    dbRule = None
                                    break
                                elif tmp[0] in '12' and len(tmp) == 2:
                                    try:
                                        tmp[0] += '|'+str(int(tmp[1]))
                                    except ValueError:
                                        api.sendMessage(message['message']['chat']['id'],"規則格式錯誤：請參見 #SETWARNRULE 規則說明。",{"reply_to_message_id":message['message']['message_id']})
                                        dbRule = None
                                        break
                                dbRule.append(tmp[0])
                            if dbRule:
                                tmp = [str(message['message']['chat']['id'])]+dbRule
                                tmp += [dbRule[-1]] * (6-len(tmp))
                                tmp += [db[1].getItem(str(message['message']['chat']['id']),'fade')]
                                tmp += [db[1].getItem(str(message['message']['chat']['id']),'notify')]
                                tmp += [db[1].getItem(str(message['message']['chat']['id']),'msg')]
                                db[1].addItem(tmp)
                                api.sendMessage(message['message']['chat']['id'],"警告懲罰規則已修改成功。",{'reply_to_message_id':message['message']['message_id']})
            elif len(message['message']['text'])>11 and message['message']['text'][1:12].lower() == 'setwarnfade':
                if message['message']['chat']['type']!='supergroup':
                    api.sendMessage(message['message']['chat']['id'],'抱歉，警告功能僅在超級群組有效。',{'reply_to_message_id':message['message']['message_id']})
                else:
                    reqUser = api.query('getChatMember',{'chat_id':message['message']['chat']['id'],'user_id':message['message']['from']['id']})
                    if (reqUser['status'] != 'creator') and not (('can_promote_members' in reqUser) and reqUser['can_promote_members']):
                        api.sendMessage(message['message']['chat']['id'],'抱歉，僅有濫權管理員方可使用 #SETWARNFADE 修改警告懲罰規則。',{'reply_to_message_id':message['message']['message_id']})
                    else:
                        newRule = message['message']['text'].split(' ')[1:]
                        invalidRule = False
                        if not newRule:
                            api.sendMessage(message['message']['chat']['id'],"用法說明：\n#SETWARNFADE 規則\n\n規則類型：\n0: 警告永不過期\n1|x: 警告 x 秒後過期",{'reply_to_message_id':message['message']['message_id']})
                            invalidRule = True
                        else:
                            dbRule = newRule[0].split('|')
                            if (dbRule[0] == '1' and len(dbRule) != 2) or (dbRule[0] == '0' and len(dbRule) != 1):
                                api.sendMessage(message['message']['chat']['id'],"規則格式錯誤：請參見 #SETWARNFADE 規則說明。",{"reply_to_message_id":message['message']['message_id']})
                                invalidRule = True
                            else:
                                if dbRule[0] == '1':
                                    try:
                                        dbRule[0] += '|'+str(int(dbRule[1]))
                                    except ValueError:
                                        api.sendMessage(message['message']['chat']['id'],"規則格式錯誤：請參見 #SETWARNFADE 規則說明。",{"reply_to_message_id":message['message']['message_id']})
                                        invalidRule = True
                            if not invalidRule:
                                db[1].data.execute('UPDATE "group" SET "fade"=? WHERE header=?',(dbRule[0],str(message['message']['chat']['id'])))
                                db[1].updateDB()
                                api.sendMessage(message['message']['chat']['id'],"警告過期規則已修改成功。",{'reply_to_message_id':message['message']['message_id']})
    elif 'new_chat_members' in message['message']:
        for newMember in message['message']['new_chat_members']:
            if newMember['id'] == api.info["id"]:
                addGroup(message['message']['chat']['id'],db,api.logOut)
                groupBlacklist = db[0].getItem('blacklist','value').split('|')
                if str(message['message']['chat']['id']) in groupBlacklist:
                    try:
                        api.sendMessage(message['message']['chat']['id'],"This group has been blacklisted!")
                    except APIError:
                        api.logOut.writeln("Group blacklisted message failed to be sent")
                    api.query("leaveChat",{"chat_id":message['message']['chat']['id']})
    db[0].addItem(['lasttime',message['message']['date']])

def updateWorker(dbn,outdev,api,stdin,happyEnd):
    db = initiateDB(dbn,outdev)
    while happyEnd.empty():
        while not stdin.empty():
            try:
                tmp = stdin.get()
                processItem(tmp,db,api)
                time.sleep(0.5)
            except Exception as e:
                print("Worker Error:",e,tmp,sep="\t")

def run(db,api,outdev):
    data = api.query('getUpdates')
    resPos = int(db[0].getItem('lastid','value'))
    msgQueue = queue.Queue()
    killSig = queue.Queue()
    msgThr = threading.Thread(target=updateWorker,args=(db[0].filename,outdev,api,msgQueue,killSig))
    msgThr.start()
    botGroup = {'default':(msgQueue,killSig,msgThr)}
    for item in range(len(data)):
        if data[item]['update_id'] == resPos:
            data = data[item+1:]
            api.logOut.writeln('Skipping '+str(item+1)+' processed messages.')
            break
    for item in data:
        msgQueue.put(item)
        db[0].addItem(['lastid',item['update_id']])
    api.logOut.writeln('All pending messages processed.')
    ## Start default thread for non-messages
    while True:
        try:
            time.sleep(2) #Max frequency 30 messages/group
            data = api.query('getUpdates',{'offset':int(db[0].getItem('lastid','value'))+1,'timeout':20})
            for item in data:
                db[0].addItem(['lastid',item['update_id']])
                queueTarget = 'default' if 'message' not in item else item['message']['chat']['id']
                if queueTarget not in botGroup:
                    msgQueue = queue.Queue()
                    killSig = queue.Queue()
                    msgThr = threading.Thread(target=updateWorker,args=(db[0].filename,outdev,api,msgQueue,killSig))
                    msgThr.start()
                    botGroup[queueTarget] = (msgQueue,killSig,msgThr)
            ## Global commands
                if 'message' in item and 'text' in item['message'] and item['message']['text'].lower() in ('/groupthread','/groupthread'+api.info['username'].lower()):
                    api.sendMessage(item['message']['chat']['id'],'<pre>'+'\n'.join([str(i)+'('+str(botGroup[i][2].native_id)+')\t'+str(botGroup[i][0].qsize()) for i in botGroup])+'</pre>',{'parse_mode':'HTML','reply_to_message_id':item['message']['message_id']})
            ## Global commands end
                else:
                    botGroup[queueTarget][0].put(item)
            api.clearDelayQuery()
            ## Garbage Collection
            gc = []
            for item in botGroup:
                if item != 'default':
                    if botGroup[item][0].empty():
                        botGroup[item][1].put(True)
                        botGroup[item][2].join()
                        gc.append(item)
            for item in gc:
                botGroup.pop(item)
        except KeyboardInterrupt:
            print('Gracefully processing all remaining messages...')
            for item in botGroup:
                botGroup[item][1].put(True)
                botGroup[item][2].join()
                print('Group '+str(item)+' completed.')
            print('Bye!')
            return

def main(args):
    outdev = stdOut(args[2]) if len(args)==3 else stdOut()
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
    run(db,api,outdev)

if __name__ == '__main__':
    main(sys.argv[1:])
