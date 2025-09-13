import os
import json
import sqlite3

# Paths
memory_dir = "./memory"
sqlite_path = os.path.join(memory_dir, "memory.db")

json_files = {
    "memory": "memory.json",
    "vocab": "vocab.json",
    "emotions": "emotions.json",
    "beliefs": "beliefs.json"
}

# Make sure directory exists
os.makedirs(memory_dir, exist_ok=True)

# Start fresh SQLite DB
conn = sqlite3.connect(sqlite_path)
cursor = conn.cursor()

# Create tables
cursor.execute("CREATE TABLE IF NOT EXISTS memory (key TEXT PRIMARY KEY, value TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS vocab (word TEXT PRIMARY KEY)")
cursor.execute("CREATE TABLE IF NOT EXISTS emotions (emotion TEXT PRIMARY KEY, intensity TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS beliefs (id INTEGER PRIMARY KEY AUTOINCREMENT, belief TEXT)")
conn.commit()

# Load and insert data
for table, filename in json_files.items():
    json_path = os.path.join(memory_dir, filename)
    if not os.path.exists(json_path):
        print(f"Skipping {filename} (not found)")
        continue

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if table == "memory":
        for key, val in data.items():
            cursor.execute("INSERT OR REPLACE INTO memory (key, value) VALUES (?, ?)", (key, json.dumps(val)))

    elif table == "vocab":
        if isinstance(data, list):
            for word in data:
                cursor.execute("INSERT OR IGNORE INTO vocab (word) VALUES (?)", (word,))
        elif isinstance(data, dict) and "known_words" in data:
            for word in data["known_words"]:
                cursor.execute("INSERT OR IGNORE INTO vocab (word) VALUES (?)", (word,))

    elif table == "emotions":
        for emotion, intensity in data.items():
            cursor.execute("INSERT OR REPLACE INTO emotions (emotion, intensity) VALUES (?, ?)", (emotion, json.dumps(intensity)))

    elif table == "beliefs":
        beliefs = data.get("beliefs", data)  # support both formats
        if isinstance(beliefs, list):
            for belief in beliefs:
                cursor.execute("INSERT INTO beliefs (belief) VALUES (?)", (belief,))

conn.commit()
conn.close()

print("✅ Conversion complete! Created:", sqlite_path)
