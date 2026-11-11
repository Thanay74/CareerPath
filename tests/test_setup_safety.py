import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

from backend.database_config import DatabaseTargetError, resolve_database_target, validate_setup_target
from backend import setup


class SetupTargetSafetyTests(unittest.TestCase):
    def test_missing_malformed_unsupported_and_production_targets_rejected(self):
        cases = [
            ("", None),
            ("mysql://user:pass@host", None),
            ("postgres://user:pass@host/db", None),
            ("mysql://user:pass@[broken/db", None),
            ("mysql://user:pass@host:bad/db", None),
            ("mysql://user:pass@host/careerpath", None),
        ]
        for url, path in cases:
            with self.subTest(url=url), self.assertRaises(DatabaseTargetError):
                target = resolve_database_target(url, path, allow_default=False)
                validate_setup_target(target, target.identity, allow_non_test=True)

    def test_confirmation_and_non_test_allow_flag_are_required(self):
        target = resolve_database_target("mysql://student:secret@db.example/careerpath_test")
        with self.assertRaises(DatabaseTargetError):
            validate_setup_target(target, None)
        with self.assertRaises(DatabaseTargetError):
            validate_setup_target(target, "mysql://db.example/careerpath_test")
        self.assertIs(validate_setup_target(target, target.identity), target)
        other = resolve_database_target("mysql://student:secret@db.example/careersandbox")
        with self.assertRaises(DatabaseTargetError):
            validate_setup_target(other, other.identity)
        self.assertIs(validate_setup_target(other, other.identity, allow_non_test=True), other)
        self.assertNotIn("secret", target.identity)

    def test_unsafe_setup_arguments_return_before_any_connection(self):
        with tempfile.TemporaryDirectory() as scratch:
            for url, sqlite_path in [
                ("", None),
                ("postgres://user:secret@host/db", None),
                ("mysql://user:secret@host/careerpath", None),
                ("mysql://user:secret@host/db", None),
            ]:
                with self.subTest(url=url, sqlite_path=sqlite_path):
                    with patch.object(setup.application, 'DATABASE_URL', url), \
                         patch.dict(os.environ, {'CAREERPATH_DB': sqlite_path or ''}), \
                         patch.object(setup.application, 'init_db', side_effect=AssertionError('connection/setup called')) as init_db:
                        output = io.StringIO()
                        with redirect_stderr(output):
                            result = setup.main(['--schema'])
                        self.assertEqual(result, 2)
                        init_db.assert_not_called()

    def test_explicit_test_sqlite_target_requires_credential_free_confirmation(self):
        with tempfile.TemporaryDirectory() as scratch:
            target = resolve_database_target('', str(Path(scratch)/'career_test.sqlite3'))
            self.assertIs(validate_setup_target(target, target.identity), target)
            self.assertFalse(Path(target.sqlite_path).exists())


if __name__ == '__main__':
    unittest.main()
