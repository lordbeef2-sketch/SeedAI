import sqlite3, os
DB=r'D:\SeedAI\seedai\memory\seedai_store.sqlite3'
print('db exists', os.path.exists(DB))
conn=sqlite3.connect(DB)
c=conn.cursor()
c.execute("SELECT id,type,key,data_json,ts FROM memories ORDER BY id DESC LIMIT 5")
for r in c.fetchall():
    print(r[0], r[1], r[2], str(r[3])[:160])
conn.close()
