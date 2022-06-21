#! /usr/bin/python3
import json
import socket
import sqlite3
import sys
import time

class sqliteDBError(Exception):
    def __init__(self,e):
        self.message = e
    def __repr__(self):
        return 'SQLite DB Exception: '+self.message

# This is the file that would replace the old-fashioned PSV DB with the new SQLite database.
# A few security issues exist and might cause serious data destruction.
# The following input is not filtered: dbTable, item, key. Please filter accordingly.
class sqliteDB():
    "This is the file that would replace the old-fashioned PSV DB with the new SQLite database."
    def __init__(self,dbFile,dbTable='main'):
        if type(dbFile) is str:
            self.filename = dbFile
            self.db = sqlite3.connect(dbFile)
        elif type(dbFile) is sqliteDB:
            self.db = dbFile.db
            self.filename = dbFile.filename
        else:
            self.db = dbFile
            self.filename = "Unknown"
        self.table = dbTable
        try:
            self.data = self.db.cursor()
            self.header = self.data.execute('select * from "'+dbTable+'" where header = "header"').fetchone()
            self.data.close()
            self.data = self.db.cursor()
        except sqlite3.OperationalError:
            raise sqliteDBError('no such table - '+dbTable)

    def keys(self):
        tmp = self.data.execute('select header from "'+self.table+'"').fetchall()
        result = []
        for datum in tmp:
            if datum[0] != 'header':
                result.append(datum[0])
        return result

    def __iter__(self):
        return self.keys().__iter__()

    def __getitem__(self,key):
        if not self.hasItem(key):
            raise KeyError(key)
        tmp = {}
        data = self.data.execute('select * from "'+self.table+'" where header=?',(key,)).fetchone()
        for item in self.header[1:]:
            data = data[1:]
            tmp[item] = data[0]
        self.data.close()
        self.data = self.db.cursor()
        return tmp

    def __str__(self):
        tmpData = self.data.execute('select * from "'+self.table+'"').fetchall()
        result = ''
        for item in tmpData:
            first = True
            for subitem in item:
                if not first:
                    result += '|'
                else:
                    first = False
                result += str(subitem)
            result += '\n'
        return result

    def __repr__(self):
        return self.__str__()

    def hasItem(self,item):
        result = self.data.execute('select * from "'+self.table+'" where header=?',(item,)).fetchone() is not None
        self.data.close()
        self.data = self.db.cursor()
        return result

    def getItem(self,item,key):
        data = self.data.execute('select "'+key+'" from "'+self.table+'" where header=?',(item,)).fetchone()
        self.data.close()
        self.data = self.db.cursor()
        if data is not None:
            return data[0]
        else:
            raise sqliteDBError('item not found - '+item)

    # This would add a new item to the database if the "header" was not used.
    # If the "header" was already used, this would update the "header" with new data.
    def addItem(self,item):
        # If we do not have the item - Add it.
        if not self.hasItem(item[0]):
            self.data.execute('insert into "'+self.table+'" (header) values ("'+item[0]+'")')
        tmp = item[1:]
        for key in range(len(tmp)):
            self.data.execute('update "'+self.table+'" set "'+self.header[key+1]+'" = "'+str(tmp[key])+'" where header = "'+item[0]+'"')
        self.data.close()
        self.db.commit()
        self.data = self.db.cursor()

    def remItem(self,item):
        if not self.hasItem(item):
            raise sqliteDBError('item not found - '+item)
        result = [item]
        for key in self.header[1:]:
            result.append(self.getItem(item,key))
        self.data.execute('delete from "'+self.table+'" where header = ?',(item,))
        self.data.close()
        self.db.commit()
        self.data = self.db.cursor()
        return result

    def chgItem(self,item,key,val):
        if not self.hasItem(item):
            raise sqliteDBError('item not found - '+ item)
        elif key not in self.header[1:]:
            raise sqliteDBError('key not found - '+ key)
        result = self.getItem(item,key)
        self.data.execute('UPDATE "'+self.table+'" SET "'+key+'" = ? WHERE header = ?',(val,item))
        self.updateDB()
        return result

    def updateDB(self):
        self.data.close()
        self.db.commit()
        self.data = self.db.cursor()

# Input: fileName - The file name of the new SQLite file
#        columnList - The list of every columns except "header" column
#        tableName - The name of the table in the SQLite file, default "main"
# Output: The corresponding SQLite file that contains the header row only.
def createSQLiteDB(fileName,columnList,tableName = 'main'):
    db = sqlite3.Connection(fileName)
    data = db.cursor()
    data.execute('create table '+tableName+' (header, '+str(columnList)[1:-1].replace("'",'').replace('"','')+')')
    data.execute('insert into '+tableName+' values ("header", '+str(columnList)[1:-1]+')')
    db.commit()

# Input: fileName - The file name of the PSV file need to be imported
# Output: The corresponding SQLite file with .psv replaced by .sql.
# Notice: The "header" row is required.
def importPSVDB(fileName,tableName = 'main'):
    import psvdb
    db = psvdb.psvDB(fileName)
    columnList = db.data['header']
    createSQLiteDB(fileName[:-3]+'sql',columnList,tableName)
    newDB = sqliteDB(fileName[:-3]+'sql')
    for key in db.data.keys():
        if key != 'header':
            newDB.addItem([key]+db.data[key])

def main(args):
    sock = socket.socket(socket.AF_INET6,socket.SOCK_DGRAM)
    sock.bind(("::1",10086))
    print("Starting service on [::1]:10086")
    db = {}
    while True:
        data, addr = sock.recvfrom(4096)
        printaddr = (addr[0][7:],addr[1]) if addr[0][:7] == '::ffff:' else addr
        print('['+str(int(time.time()))+']\tReceived a UDP packet from',printaddr[0]+':'+str(printaddr[1]))
        parse = json.loads(data.decode("UTF-8"))
        print(parse)
        try:
            if parse["target"] not in db:
                if not db:
                    db[parse["target"]] = sqliteDB(args[0],parse["target"])
                else:
                    db[parse["target"]] = sqliteDB(db[list(db.keys())[0]],parse["target"])
            if parse["action"] == "execute":
                if "param" not in parse:
                    parse["param"] = []
                result = db[parse["target"]].data.execute(parse["query"],parse["param"]).fetchall()
            elif parse["action"] == "commit":
                db[parse["target"]].commit()
                result = None
            elif parse["action"] == "builtin.getitem":
                result = db[parse["target"]][parse["query"]]
            elif parse["action"] == "hasitem":
                result = db[parse["target"]].hasItem(parse["query"])
            result = {"ok":True,"data":result}
        except Exception as e:
            result = {"ok": False, "type": type(e).__module__+"."+type(e).__name__, "info": str(e)}
        try:
            sock.sendto(len(json.dumps(result)).to_bytes(8,"big"),addr)
            sock.sendto(json.dumps(result).encode("UTF-8"),addr)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print('['+str(int(time.time()))+']\tSocket send to '+addr[0]+':'+str(addr[1])+' failed with Exception: '+str(e))

if __name__ == '__main__':
    main(sys.argv[1:])
