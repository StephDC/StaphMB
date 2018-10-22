#! /usr/bin/env python3

import sqldb
import sys

def main(args):
    db = sqldb.sqliteDB(args[0],'config')
    db.addItem(['lastid',str(int(db.getItem('lastid','value'))+1)])

if __name__ == '__main__':
    main(sys.argv[1:])
