import sqlite3
conn = sqlite3.connect('open-webui-main2/open-webui/backend/data/webui.db')
c = conn.cursor()
c.execute("UPDATE auth SET email = ?", ('admin@localhost',))
c.execute("UPDATE user SET email = ?", ('admin@localhost',))
conn.commit()
conn.close()