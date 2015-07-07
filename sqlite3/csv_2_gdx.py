#!/usr/bin/env python3
#
#    Code example of using the GAMS GDX API to create a GDX file with 
#    a sqlite3 populated with a CSV file
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
    assert gdxDataWriteStrStart(gdxHandle, "Site", "Site data", 1, GMS_DT_SET , 0)

    values = doubleArray(GMS_VAL_MAX)


# sqlite3 part of the demo
    conn = sqlite3.connect('niko.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.executescript("""
           DROP TABLE IF EXISTS ProductDemands;
           CREATE TABLE ProductDemands (Site_Name text, Commodity text, TimeIdx integer, Demand real);
           """)

    # Populate table with CSV data
    with open('Product Demands.csv','rb') as fin: 
        # csv.DictReader uses first line in file for column headings by default
        dr = csv.DictReader(fin) # comma is default delimiter
        to_db = [(i['Site_Name'], i['Commodity'], i['TimeIdx'], i['Demand']) for i in dr]

    cursor.executemany("INSERT INTO ProductDemands (Site_Name, Commodity, TimeIdx, Demand) VALUES (?, ?, ?, ?);", to_db)
 
    conn.commit()    

    # cursor.execute("select Site_Name, Commodity, count(Commodity) from ProductDemands group by Site_Name, Commodity")
    # for groupings in cursor.fetchall():
    #     print groupings

    values[GMS_VAL_LEVEL] = 0
    temp = []

    # Write a query to a GDX set
    cursor.execute("select distinct Site_Name from ProductDemands")
    for row in cursor:
        temp = []
        temp.append(row["Site_Name"].encode('ascii','ignore'))
        gdxDataWriteStr(gdxHandle, temp, values)
    assert gdxDataWriteDone(gdxHandle)

    # Write a query to a GDX parameter
    assert gdxDataWriteStrStart(gdxHandle, "ProductDemand", "Demand data", 3, GMS_DT_PAR , 0)
  
    cursor.execute("select * from ProductDemands")
    for row in cursor:
        temp = []
        values[GMS_VAL_LEVEL] = row["Demand"]
        gdxDataWriteStr(gdxHandle, [row["Site_Name"].encode('ascii','ignore'),row["Commodity"].encode('ascii','ignore'),str(row["TimeIdx"])], values)
    assert gdxDataWriteDone(gdxHandle)
        
    assert not gdxClose(gdxHandle)
    assert gdxFree(gdxHandle)
 
    conn.close()

    # cursor.execute("select * from teacher order by name")    
    # for teacher in cursor.fetchall():
    #     tId = teacher[0]
    #     print(teacher[1])
    #     cmd = """select * from course where teacherId = "{0}" order by name"""
    #     cursor.execute(cmd.format(tId))
    #     for course in cursor.fetchall():
    #         print("  {0}  {1}".format(course[0], course[1]))


if __name__ == "__main__":
    sys.exit(main())




# Module gamsglobals
#     Public Const maxdim As Integer = 19
#     Public Const str_len As Integer = 255

#     Public Const val_level As Integer = 0
#     Public Const val_marginal As Integer = 1
#     Public Const val_lower As Integer = 2
#     Public Const val_upper As Integer = 3
#     Public Const val_scale As Integer = 4
#     Public Const val_max As Integer = 4

#     Public Const sv_und As Integer = 0
#     Public Const sv_na As Integer = 1
#     Public Const sv_pin As Integer = 2
#     Public Const sv_min As Integer = 3
#     Public Const sv_leps As Integer = 4
#     Public Const sv_normal As Integer = 5
#     Public Const sv_acronym As Integer = 6
#     Public Const sv_max As Integer = 6

#     Public Const dt_set As Integer = 0
#     Public Const dt_par As Integer = 1
#     Public Const dt_var As Integer = 2
#     Public Const dt_equ As Integer = 3
#     Public Const dt_alias As Integer = 4
#     Public Const dt_max As Integer = 4

#     Public Const sv_valund As Double = 1.0E+300       ' undefined
#     Public Const sv_valna As Double = 2.0E+300        ' not available/applicable
#     Public Const sv_valpin As Double = 3.0E+300       ' plus infinity
#     Public Const sv_valmin As Double = 4.0E+300       ' minus infinity
#     Public Const sv_valeps As Double = 5.0E+300       ' epsilon
#     Public Const sv_valacronym As Double = 1.0E+301   ' potential/real acronym

