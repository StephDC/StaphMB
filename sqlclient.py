#! /usr/bin/python3
import socket
import json

class socketInteraction():
    def __init__(self,addr,port,table="main"):
        self.table = table
        self.addr = addr
        self.port = port
        self.db = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        self.db.connect((addr,port))
    def query(self,data):
        if len(data) > 4000:
            raise sqliteDBError("Request too long")
        try:
            self.db.send(data)
        except Exception:
            self.db.connect((self.addr,self.port))
            try:
                self.db.send(data)
            except Exception:
                raise sqliteDBError("Connection failed")
        resplen = int.from_bytes(self.db.recv(10),"big")
        resp = json.loads(self.db.recv(resplen + 5).decode("UTF-8"),parse_float=lambda x:x, parse_int=lambda x:x)
        if not resp["ok"]:
            raise sqliteDBError(resp["type"]+": "+resp["info"])
        return resp["data"]
    def execute(self,query,param=[]):
        return sqlResponse(self.query(json.dumps({"action": "execute", "query": query, "param": param, "target": self.table}).encode("UTF-8")))

class sqlResponse(list):
    def fetchone(self):
        if len(self) == 0:
            raise StopIteration
        result = self[0]
        self.remove(result)
        return result
    def fetchall(self):
        return self

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
            self.db = socketInteraction(dbFile.rsplit(":",1)[0],int(dbFile.rsplit(":",1)[1]),dbTable)
        elif type(dbFile) is sqliteDB:
            self.filename = dbFile.filename
            self.db = socketInteraction(dbFile.db.addr,dbFile.db.port,dbTable)
        else:
            self.db = dbFile
            self.filename = "Unknown"
        self.table = dbTable
        self.data = self.db
        resp = self.db.query(json.dumps({"target":dbTable, "action": "execute", "query":"select * from '"+dbTable+'\' where header = "header"',"param":[]}).encode("UTF-8"))
        self.header = resp[0]

    def keys(self):
        tmp = self.db.query(json.dumps({"target":self.table, "action": "execute", "query":'select header from "'+self.table+'"', "param":[]}).encode("UTF-8"))
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
        return self.db.query(json.dumps({"target": self.table, "action": "builtin.getitem", "query": key}).encode("UTF-8"))

    def __str__(self):
        tmpData = self.keys()
        result = []
        for item in tmpData:
            result.append("|".join([item]+list(self[item].values())))
        return "\n".join(result)

    def __repr__(self):
        return self.__str__()

    def hasItem(self,item):
        return self.db.query(json.dumps({"target": self.table, "action": "hasitem", "query": item}).encode("UTF-8"))

    def getItem(self,item,key):
        if key not in self.header:
            raise sqliteDBError("key not found - "+key)
        try:
            data = self[item]
        except KeyError:
            raise sqliteDBError("item not found - "+item)
        return data[key]

    ######### TODO: Adapt to new style #########
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
    ################ END OF TODO ####################

    def chgItem(self,item,key,val):
        if key not in self.header[1:]:
            raise sqliteDBError('key not found - '+ key)
        if not self.hasItem(item):
            raise sqliteDBError('item not found - '+ item)
        result = self.getItem(item,key)
        self.db.query(json.dumps({"target":self.table,"action": "execute", "query":'UPDATE "'+self.table+'" SET "'+key+'" = ? WHERE header = ?', "param":[val,item]}).encode("UTF-8"))
        self.updateDB()
        return result

    def updateDB(self):
        self.db.query(json.dumps({"target": self.table, "action": "commit"}).encode("UTF-8"))

###TODO: Not Implemented for the new interface
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

###TODO: Not Implemented for the new interface
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

# This process is used to protect the CGI access from the outside,
# as well as Command-line direct access.
def main():
    print('Content-Type:text/html charset:utf-8\nLocation:http://bbs.psucssa.org/cgi-bin/webAccess/\n\n')

if __name__ == '__main__':
    main()
