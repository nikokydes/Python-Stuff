#!/usr/bin/env python3
#
#    Simple report of classes taught by each teacher
#
import sqlite3
import csv
from gdxcc import *
import sys
import os

def main(argv=None):
    if argv is None:
        argv = sys.argv

# GAMS GDX API part of the demo
    GAMSpath = 'c:/gams/win64/24.1'

    gdxHandle = new_gdxHandle_tp()
    rc =  gdxCreateD(gdxHandle, GAMSpath, GMS_SSSIZE)
    assert rc[0],rc[1]

    print "Using GDX DLL version: " + gdxGetDLLVersion(gdxHandle)[1]
        
    assert gdxOpenWrite(gdxHandle, "nikotest.gdx", "csv_2_gdx")[0]
    assert gdxDataWriteStrStart(gdxHandle, "TimeIdx", "Time data", 1, GMS_DT_SET , 0)

    values = doubleArray(GMS_VAL_MAX)

    values[GMS_VAL_LEVEL] = 0
    gdxDataWriteStr(gdxHandle, ["0"], values)
    gdxDataWriteStr(gdxHandle, ["1"], values)

    assert gdxDataWriteDone(gdxHandle)
        
    assert not gdxClose(gdxHandle)
    assert gdxFree(gdxHandle)

# sqlite3 part of the demo
    conn = sqlite3.connect('niko.db')
    cursor = conn.cursor()
    cursor.executescript("""
           DROP TABLE IF EXISTS ProductDemands;
           CREATE TABLE ProductDemands (Site_Name text, Commodity text, TimeIdx integer, Demand real);
           """)

    # cursor.execute("INSERT INTO ProductDemands VALUES ('AK','ASPHout','-1',0.15)")

    with open('Product Demands.csv','rb') as fin: 
        # csv.DictReader uses first line in file for column headings by default
        dr = csv.DictReader(fin) # comma is default delimiter
        to_db = [(i['Site_Name'], i['Commodity'], i['TimeIdx'], i['Demand']) for i in dr]

    cursor.executemany("INSERT INTO ProductDemands (Site_Name, Commodity, TimeIdx, Demand) VALUES (?, ?, ?, ?);", to_db)
 
    conn.commit()    

    # cursor.execute("select * from ProductDemands")
    # for demands in cursor.fetchall():
    #     print demands

    # cursor.execute("select Site_Name, Commodity, count(Commodity) from ProductDemands group by Site_Name, Commodity")
    # for groupings in cursor.fetchall():
    #     print groupings

    cursor.execute("select distinct Site_Name from ProductDemands")
    for setelements in cursor.fetchall():
        print setelements

    conn.close()
 
    # cursor.execute("select * from teacher order by name")    
    # for teacher in cursor.fetchall():
    #     tId = teacher[0]
    #     print(teacher[1])
    #     cmd = """select * from course where teacherId = "{0}" order by name"""
    #     cursor.execute(cmd.format(tId))
    #     for course in cursor.fetchall():
    #         print("  {0}  {1}".format(course[0], course[1]))


# if __name__ == '__main__':
#     conn = sqlite3.connect('niko.db')
#     cur = conn.cursor()
#     main(conn,cur)

if __name__ == "__main__":
    sys.exit(main())