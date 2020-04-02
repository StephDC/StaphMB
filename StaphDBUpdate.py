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

def main(args):
    tmp = sqldb.sqliteDB(args[0],'config')
    db = (tmp,sqldb.sqliteDB(tmp,'group'),sqldb.sqliteDB(tmp,'warn'))
    if db[0].getItem('dbver','value') == '1.0':
        update0(db)
    if db[0].getItem('dbver','value') == '1.1':
        update1(db)
    print("Your database is up-to-date.")

if __name__ == '__main__':
    main(sys.argv[1:])
