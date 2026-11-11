import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT=Path(__file__).resolve().parents[1]


class StartupSafetyTests(unittest.TestCase):
    def test_import_does_not_connect_migrate_seed_or_bootstrap_admin(self):
        scratch=ROOT/'.test-tmp'; scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as directory:
            db_path=Path(directory)/'must-not-be-created.sqlite3'
            env=os.environ.copy()
            env.update({'DATABASE_URL':'','CAREERPATH_DB':str(db_path),'ADMIN_EMAIL':'bootstrap@example.test','ADMIN_PASSWORD':'long-enough-test-password'})
            script=(
                'import sqlite3,sys; '
                'sqlite3.connect=lambda *a,**k: (_ for _ in ()).throw(AssertionError("database access during import")); '
                'import backend.app; '
                'assert "backend.aptitude_bank" not in sys.modules'
            )
            result=subprocess.run([sys.executable,'-c',script],cwd=ROOT,env=env,text=True,capture_output=True)
            self.assertEqual(result.returncode,0,result.stdout+'\n'+result.stderr)
            self.assertFalse(db_path.exists())


if __name__=='__main__': unittest.main()
