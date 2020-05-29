#! /usr/bin/env python3

import sys
import sqldb

def update0(db):
    if db[0].getItem('dbver','value') != '1.0':
        raise TypeError("Wrong Database Version")
    db[1].data.execute("alter table 'group' add 'notify'")
    db[1].data.execute("update 'group' set notify = 'notify' where header='header'")
    db[1].data.execute("alter table 'group' add 'msg'")
    db[1].data.execute("update 'group' set msg = 'msg' where header='header'")
    db[1].updateDB()
    db[0].addItem(['dbver','1.1'])
    print("DB version updated to 1.1")

def update1(db):
    if db[0].getItem('dbver','value') != '1.1':
        raise TypeError("Wrong Database Version")
    db[0].addItem(['blacklist',''])
    db[0].addItem(['dbver','1.2'])
    print('DB version updated to 1.2')

def update2(db):
    if db[0].getItem('dbver','value') != '1.2':
        raise TypeError("Wrong Database Version")
    db[0].data.execute("create table admin (header text, time text, last text)")
    db[0].data.execute("insert into admin values ('header','time','last')")
    db[0].updateDB()
    db[0].addItem(['dbver','1.3'])
    print('DB version updated to 1.3')

def update3(db):
    if db[0].getItem('dbver','value') != '1.3':
        raise TypeError("Wrong Database Version")
    db[0].data.execute("create table auth (header text, pword text, atime text, gid text, key text)")
    db[0].data.execute("insert into auth values('header','pword','atime','gid','key')")
    db[0].updateDB()
    db[0].addItem(['keyexp','1800'])
    db[0].addItem(['dbver','1.4'])
    print('DB version updated to 1.4')

def update4(db):
    if db[0].getItem('dbver','value') != '1.4':
        raise TypeError("Wrong Database Version")
    db[1].data.execute("alter table 'group' add 'bansticker'")
    db[1].data.execute("update 'group' set bansticker = ''")
    db[1].data.execute("update 'group' set bansticker = 'bansticker' where header='header'")
    db[0].addItem(['dbver','1.5'])
    print('DB version updated to 1.5')

def main(args):
    tmp = sqldb.sqliteDB(args[0],'config')
    db = [tmp,sqldb.sqliteDB(tmp,'group'),sqldb.sqliteDB(tmp,'warn')]
    if db[0].getItem('dbver','value') == '1.0':
        update0(db)
    if db[0].getItem('dbver','value') == '1.1':
        update1(db)
    if db[0].getItem('dbver','value') == '1.2':
        update2(db)
        db.append(sqldb.sqliteDB(tmp,'admin'))
    if db[0].getItem('dbver','value') == '1.3':
        update3(db)
        db.append(sqldb.sqliteDB(tmp,'auth'))
    if db[0].getItem('dbver','value') == '1.4':
        update4(db)
    print("Your database is up-to-date.")

if __name__ == '__main__':
    main(sys.argv[1:])
