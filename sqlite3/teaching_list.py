#!/usr/bin/env python3
#
#    Simple report of classes taught by each teacher
#
import sqlite3


def main(cursor):
    cursor.execute("select * from teacher order by name")
    for teacher in cursor.fetchall():
        tId = teacher[0]
        print(teacher[1])
        cmd = """select * from course where teacherId = "{0}" order by name"""
        cursor.execute(cmd.format(tId))
        for course in cursor.fetchall():
            print("  {0}  {1}".format(course[0], course[1]))


if __name__ == '__main__':
    conn = sqlite3.connect('school.db')
    cur = conn.cursor()
    main(cur)
