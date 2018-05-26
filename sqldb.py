#! /usr/bin/python3
import sqlite3

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
            self.db = sqlite3.connect(dbFile)
        else:
            self.db = dbFile
        self.table = dbTable
        try:
            self.data = self.db.cursor()
            self.header = self.data.execute('select * from "'+dbTable+'" where header = "header"').fetchone()
        except sqlite3.OperationalError:
            raise sqliteDBError('no such table - '+dbTable)

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
        return self.data.execute('select * from "'+self.table+'" where header=?',(item,)).fetchone() is not None

    def getItem(self,item,key):
        data = self.data.execute('select "'+key+'" from "'+self.table+'" where header=?',(item,)).fetchone()
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
        self.db.commit()

    def remItem(self,item):
        if not self.hasItem(item):
            raise sqliteDBError('item not found - '+item)
        result = [item]
        for key in self.header[1:]:
            result.append(self.getItem(item,key))
        self.data.execute('delete from "'+self.table+'" where header = ?',(item,))
        self.db.commit()
        return result

    def updateDB(self):
        self.db.commit()

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

# This process is used to protect the CGI access from the outside,
# as well as Command-line direct access.
def main():
    print('Content-Type:text/html charset:utf-8\nLocation:http://bbs.psucssa.org/cgi-bin/webAccess/\n\n')

if __name__ == '__main__':
    main()
