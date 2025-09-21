import sys, traceback
sys.path.append(r'D:\SeedAI')
from gateway import seedai_storage
try:
    seedai_storage.init_db()
    print('calling migrate_from_json')
    r = seedai_storage.migrate_from_json(r'D:\\SeedAI\\memory')
    print('result', r)
except Exception:
    traceback.print_exc()
