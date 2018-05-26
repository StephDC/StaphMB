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

class tgapi:
    __doc__ = 'tgapi - Telegram Chat Bot HTTPS API Wrapper'

    def __init__(self,apikey,maxRetry=5):
        self.target = 'https://api.telegram.org/bot'+apikey+'/'
        self.retry = maxRetry
        self.info = self.query('getMe')
        if self.info is None:
            raise APIError('API', 'Initialization Self-test Failed')
        print("Bot "+self.info["username"]+" connected to the Telegram API.")

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
            print("Query failed. Try again in 5 sec.")
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
            return True
        else:
            return False

def initiateDB(fName):
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
    print('DB File '+fName+' loaded.')
    return (conf,group,warn)

def addGroup(gid,db):
    pass

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
    return '@'+result['user']['username']

def processItem(message,db,api):
    print(message['update_id'],'being processed...')
    if 'message' not in message:
        return
    if 'text' in message['message']:
        # Process bot command
        if message['message']['text'][0] == '/':
            stripText = message['message']['text']
            if '@'+api.info['username'] in stripText:
                stripText=stripText[:-len(api.info['username'])-1]
            if stripText == '/ping':
                api.sendMessage(message['message']['chat']['id'],'Hell o\'world!',{'reply_to_message_id':message['message']['message_id']})
        # Process hashtag
        elif message['message']['text'][0] == '#':
            if len(message['message']['text'])>4 and message['message']['text'][1:5].lower() == 'warn':
                if message['message']['chat']['type']!='supergroup':
                    api.sendMessage(message['message']['chat']['id'],'抱歉，警告功能僅在超級群組有效。',{'reply_to_message_id':message['message']['message_id']})
                else:
                    adminList = {i['user']['id']:i['user']['username'] for i in api.query('getChatAdministrators',{'chat_id':message['message']['chat']['id']})}
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
                            api.sendMessage(message['message']['chat']['id'],'警告成功。該用戶現在共有 '+str(countWarn(db,warnInfo[1],warnInfo[2]))+' 個警告。',{'reply_to_message_id':message['message']['message_id']})
                            print('Warned '+message['message']['reply_to_message']['from']['username']+' in group '+message['message']['chat']['title'])
    elif 'new_chat_participant' in message['message']:
        if message['message']['new_chat_participant']['id'] == api.info["id"]:
            addGroup(message['message']['chat']['id'],db)
            print('I\'ve been added to the group '+str(message['message']['chat']['id'])+': '+message['message']['chat']['title']+'.')
    db[0].addItem(['lastid',message['update_id']])
    db[0].addItem(['lasttime',message['message']['date']])

def run(db,api):
    data = api.query('getUpdates')
    resPos = int(db[0].getItem('lastid','value'))
    for item in range(len(data)):
        if data[item]['update_id'] == resPos:
            data = data[item+1:]
            print('Skipping '+str(item+1)+' processed messages.')
            break
    for item in data:
        processItem(item,db,api)
    print('All pending messages processed.')
    while True:
        time.sleep(2) #Max frequency 30 messages/group
        data = api.query('getUpdates',{'offset':int(db[0].getItem('lastid','value'))+1,'timeout':20})
        for item in data:
            processItem(item,db,api)

def main(args):
    if len(args)!=2:
        print('FATAL ERROR: Incorrect number of parameters given.')
        print(__doc__)
        sys.exit(1)
    try:
        api = tgapi(args[1])
    except APIError:
        print('FATAL ERROR: API Initialization Self-test Failed.')
        sys.exit(2)
    try:
        db = initiateDB(args[0])
    except APIError:
        print('FATAL ERROR: Corrupted database or wrong parameter given.')
        sys.exit(3)
    print('The configurations have been loaded successfully.')
    run(db,api)

if __name__ == '__main__':
    main(sys.argv[1:])
