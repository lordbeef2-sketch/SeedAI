"""Basic tests for MemoryManager: store/get identity, add/get memory, add vocab, resolve unknown word."""
import sys
import os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from memory_manager import MemoryManager


def run_tests():
    mm = MemoryManager()
    try:
        print('--- Identity ---')
        mm.store_identity('test_key', 'test_value')
        assert mm.get_identity('test_key') == 'test_value'
        print('store/get identity OK')

        print('\n--- Memories ---')
        mid = mm.add_memory('test', 'this is a test memory', 'neutral', 1)
        assert isinstance(mid, int)
        mems = mm.get_memories('test', limit=10)
        assert any(m['id'] == mid for m in mems)
        print('add/get memories OK')

        print('\n--- Vocab / Unknown ---')
        mm.add_unknown_word('foobar', 'testing unknown')
        mm.resolve_unknown_word('foobar', 'a test word', 'example uses')
        v = mm.get_vocab('foobar')
        assert v and v['word'] == 'foobar'
        print('unknown->vocab resolve OK')

        print('\nAll basic tests passed')
    finally:
        mm.close()


if __name__ == '__main__':
    run_tests()
