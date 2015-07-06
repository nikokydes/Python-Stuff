#!/usr/bin/env python3
#
#    Simple report of classes taught by each teacher
#
import sqlite3


def main(conn,cursor):

    cursor.execute('''CREATE TABLE ProductDemands
                      (Site_Name text, Commodity text, TimeIdx text, Demand real)''')

    cursor.execute("INSERT INTO ProductDemands VALUES ('AK','ASPHout','-1',0.15)")

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
