import sqlite3
import os

if os.path.exists('issue_tracker.db'):
    conn = sqlite3.connect('issue_tracker.db')
    c = conn.cursor()
    c.execute("SELECT * FROM Issues")
    print("Issues:", c.fetchall())
    c.execute("SELECT * FROM Project_Members")
    print("Members:", c.fetchall())
    conn.close()
