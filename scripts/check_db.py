"""Simple DB check using MemoryManager to print identities, recent memories, and vocab count."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from memory_manager import MemoryManager


def main():
    mm = MemoryManager()
    try:
        print('Identity keys sample:')
        cur = mm._conn.cursor()
        cur.execute("SELECT key, value FROM identity LIMIT 10")
        for r in cur.fetchall():
            print('-', r['key'])

        print('\nRecent memories:')
        mems = mm.get_memories(limit=5)
        for m in mems:
            print('-', m['type'], m['content'][:80])

        print('\nVocab count:')
        cur.execute('SELECT COUNT(*) as c FROM vocab')
        print('-', cur.fetchone()['c'])
    finally:
        mm.close()


if __name__ == '__main__':
    main()
