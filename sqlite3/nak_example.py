#!/usr/bin/env python3
#
#    Simple report of classes taught by each teacher
#
import sqlite3
import csv


def main(conn,cursor):

    cursor.executescript("""
           DROP TABLE IF EXISTS ProductDemands;
           CREATE TABLE ProductDemands (Site_Name text, Commodity text, TimeIdx text, Demand real);
           """)

    # cursor.execute("INSERT INTO ProductDemands VALUES ('AK','ASPHout','-1',0.15)")

    with open('Product Demands.csv','rb') as fin: 
        # csv.DictReader uses first line in file for column headings by default
        dr = csv.DictReader(fin) # comma is default delimiter
        to_db = [(i['Site_Name'], i['Commodity'], i['TimeIdx'], i['Demand']) for i in dr]

    cursor.executemany("INSERT INTO ProductDemands (Site_Name, Commodity, TimeIdx, Demand) VALUES (?, ?, ?, ?);", to_db)
 
    conn.commit()    

    cursor.execute("select * from ProductDemands")
    for demands in cursor.fetchall():
        print demands 

    conn.close()
 
    # cursor.execute("select * from teacher order by name")    
    # for teacher in cursor.fetchall():
    #     tId = teacher[0]
    #     print(teacher[1])
    #     cmd = """select * from course where teacherId = "{0}" order by name"""
    #     cursor.execute(cmd.format(tId))
    #     for course in cursor.fetchall():
    #         print("  {0}  {1}".format(course[0], course[1]))


if __name__ == '__main__':
    conn = sqlite3.connect('niko.db')
    cur = conn.cursor()
    main(conn,cur)
