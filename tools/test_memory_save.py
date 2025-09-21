import sys
sys.path.append(r'D:\SeedAI')
from gateway import seedai_storage

print('Initializing DB')
seedai_storage.init_db()

conv = 'testconv-1234'
model_text = '''Hello user.
CORE_MEMORY_UPDATE
{"topic": "test-topic", "owner": "user123", "value": "remember this fact"}
END_CORE_MEMORY_UPDATE
Goodbye.'''

print('Calling process_model_output...')
sanitized, parsed = seedai_storage.process_model_output(conv, model_text)
print('Parsed:', parsed)
print('Sanitized:', sanitized)

print('Query memory by topic...')
from gateway.seedai_storage import query_memory_by_topic, load_conversation
mems = query_memory_by_topic('test-topic')
print('Memories:', mems)

print('Load conversation...')
conv_obj = load_conversation(conv)
print('Conversation:', conv_obj)

print('Exporting memory json to seedai/memory/memory_export.json')
seedai_storage.export_memory_json()
print('Done')
