import multiprocessing
import tempfile
import time
import unittest
from pathlib import Path

from backend.interprocess_lock import interprocess_file_lock


class InterprocessLockTests(unittest.TestCase):
    def test_lock_serializes_separate_processes(self):
        with tempfile.TemporaryDirectory() as scratch:
            lock = str(Path(scratch)/'catalog.lock')
            ctx = multiprocessing.get_context('spawn')
            state = ctx.Array('i', [0, 0])
            processes = [ctx.Process(target=_locked_probe, args=(lock, state)) for _ in range(2)]
            for process in processes: process.start()
            for process in processes:
                process.join(10)
                self.assertEqual(process.exitcode, 0)
            self.assertEqual(state[0], 0)
            self.assertEqual(state[1], 1)


def _locked_probe(path, active):
    with interprocess_file_lock(path):
        with active.get_lock():
            active[0] += 1
            active[1] = max(active[1], active[0])
        time.sleep(.15)
        with active.get_lock(): active[0] -= 1


if __name__ == '__main__':
    unittest.main()
