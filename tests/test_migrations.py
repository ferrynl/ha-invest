import sys
import sqlite3
import tempfile
import unittest
from pathlib import Path
from contextlib import closing
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'portfolio' / 'app'))
from migrations import migrate, MIGRATIONS, SCHEMA_VERSION
from storage import Store

class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'portfolio.sqlite3'

    def create_old(self, version):
        with closing(sqlite3.connect(self.path)) as db:
            for number in range(1, version + 1):
                for statement in MIGRATIONS[number]:
                    db.execute(statement)
            db.execute(f'PRAGMA user_version={version}')
            db.execute("INSERT INTO purchases VALUES(1,'ASML.AS','AMSTERDAM','ASML','1','999','EUR','2026-10-12','2026-10-12T00:00:00Z')")
            if version >= 3:
                db.execute("INSERT INTO dividends VALUES(1,'ASML.AS','AMSTERDAM','EUR','5.25','2026-10-15','netto','2026-10-15T00:00:00Z')")
            db.commit()

    def test_all_previously_released_versions_upgrade_without_losing_data(self):
        for version in (1,2,3):
            with self.subTest(version=version), tempfile.TemporaryDirectory() as directory:
                self.path=Path(directory)/'portfolio.sqlite3'
                self.create_old(version)
                migrate(self.path)
                with closing(sqlite3.connect(self.path)) as db:
                    self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],SCHEMA_VERSION)
                    self.assertEqual(db.execute('SELECT price FROM purchases').fetchone()[0],'999')
                    self.assertEqual(db.execute('SELECT value FROM app_settings').fetchone()[0],'1M')
                    if version==3:self.assertEqual(db.execute('SELECT amount FROM dividends').fetchone()[0],'5.25')
                backups=list((self.path.parent/'backups'/'migrations').glob('*.sqlite3'))
                self.assertEqual(len(backups),1)
                with closing(sqlite3.connect(backups[0])) as db:
                    self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],version)
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM purchases').fetchone()[0],1)

    def test_failed_migration_rolls_back_schema_and_version(self):
        self.create_old(1)
        broken={**MIGRATIONS,4:MIGRATIONS[4]+('INVALID SQL',)}
        with patch.dict('migrations.MIGRATIONS',broken,clear=True),self.assertRaises(sqlite3.Error):
            migrate(self.path)
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],1)
            self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='dividends'").fetchone())
            self.assertEqual(db.execute('SELECT COUNT(*) FROM purchases').fetchone()[0],1)

    def test_newer_database_is_refused_without_downgrading(self):
        self.create_old(3)
        with closing(sqlite3.connect(self.path)) as db:
            db.execute('PRAGMA user_version=99')
        with self.assertRaises(RuntimeError):migrate(self.path)
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],99)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM dividends').fetchone()[0],1)

    def test_current_schema_is_not_run_again_and_settings_survive_restart(self):
        store=Store(self.temp.name)
        store.save_settings({'default_range':'1Y'})
        restarted=Store(self.temp.name)
        self.assertEqual(restarted.settings()['default_range'],'1Y')
        self.assertFalse((self.path.parent/'backups'/'migrations').exists())
        with self.assertRaises(ValueError):store.save_settings({'default_range':'bad'})
