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
            db.execute("INSERT INTO purchases(id,symbol,exchange,name,quantity,price,currency,purchased_on,created_at) VALUES(1,'ASML.AS','AMSTERDAM','ASML','1','999','EUR','2026-10-12','2026-10-12T00:00:00Z')")
            if version >= 2:
                db.execute("INSERT INTO daily_prices VALUES('ASML.AS','AMSTERDAM','EUR','2026-10-12','1000')")
            if version >= 3:
                db.execute("INSERT INTO dividends(id,symbol,exchange,currency,amount,paid_on,note,created_at) VALUES(1,'ASML.AS','AMSTERDAM','EUR','5.25','2026-10-15','netto','2026-10-15T00:00:00Z')")
            db.commit()

    def test_all_previously_released_versions_upgrade_without_losing_data(self):
        for version in (1,2,3,4,5,6,7,8,9,10,11,12,13,14):
            with self.subTest(version=version), tempfile.TemporaryDirectory() as directory:
                self.path=Path(directory)/'portfolio.sqlite3'
                self.create_old(version)
                migrate(self.path)
                with closing(sqlite3.connect(self.path)) as db:
                    self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],SCHEMA_VERSION)
                    self.assertEqual(db.execute('SELECT price FROM purchases').fetchone()[0],'999')
                    self.assertEqual(db.execute('SELECT value FROM app_settings').fetchone()[0],'1M')
                    if version>=2:self.assertEqual(db.execute('SELECT price FROM daily_prices').fetchone()[0],'1000')
                    if version>=3:self.assertEqual(db.execute('SELECT amount FROM dividends').fetchone()[0],'5.25')
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

    def test_logging_migration_from_six_rolls_back_without_losing_portfolio(self):
        self.create_old(6)
        broken={**MIGRATIONS,7:MIGRATIONS[7]+('INVALID SQL',)}
        with patch.dict('migrations.MIGRATIONS',broken,clear=True),self.assertRaises(sqlite3.Error):migrate(self.path)
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],6)
            self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='app_logs'").fetchone())
            self.assertEqual(db.execute('SELECT price FROM purchases').fetchone()[0],'999')
            self.assertEqual(db.execute('SELECT name FROM broker_accounts').fetchone()[0],'Handmatig')

    def test_fx_migration_failure_preserves_schema_seven_and_existing_data(self):
        self.create_old(7)
        broken={**MIGRATIONS,8:MIGRATIONS[8]+('INVALID SQL',)}
        with patch.dict('migrations.MIGRATIONS',broken,clear=True),self.assertRaises(sqlite3.Error):migrate(self.path)
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],7)
            self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='fx_rates'").fetchone())
            self.assertEqual(db.execute('SELECT price FROM purchases').fetchone()[0],'999')

    def test_mapping_migration_failure_rolls_back_to_eight(self):
        self.create_old(8)
        broken={**MIGRATIONS,9:MIGRATIONS[9]+('INVALID SQL',)}
        with patch.dict('migrations.MIGRATIONS',broken,clear=True),self.assertRaises(sqlite3.Error):migrate(self.path)
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],8)
            self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='instrument_mappings'").fetchone())
            self.assertEqual(db.execute('SELECT price FROM purchases').fetchone()[0],'999')

    def test_partial_import_migration_rolls_back_to_nine_on_failure(self):
        self.create_old(9)
        broken={**MIGRATIONS,10:MIGRATIONS[10]+('INVALID SQL',)}
        with patch.dict('migrations.MIGRATIONS',broken,clear=True),self.assertRaises(sqlite3.Error):migrate(self.path)
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],9)
            self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='import_issues'").fetchone())
            self.assertEqual(db.execute('SELECT price FROM purchases').fetchone()[0],'999')

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

    def test_categories_migration_preserves_ledger_and_rolls_back_on_failure(self):
        self.create_old(12)
        broken={**MIGRATIONS,13:MIGRATIONS[13]+('INVALID SQL',)}
        with patch.dict('migrations.MIGRATIONS',broken,clear=True),self.assertRaises(sqlite3.Error):migrate(self.path)
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],12)
            self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='instrument_categories'").fetchone())
            self.assertEqual(db.execute('SELECT COUNT(*) FROM dividends').fetchone()[0],1)
        migrate(self.path);migrate(self.path)
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],SCHEMA_VERSION)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM purchases').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM instrument_categories').fetchone()[0],0)

    def test_profile_migration_preserves_manual_categories_and_rolls_back(self):
        self.create_old(13)
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("INSERT INTO instrument_categories VALUES('ASML.AS','AMSTERDAM','EUR','Eigen sector','','Aandeel','Groei','2026-10-01T00:00:00+00:00')");db.commit()
        broken={**MIGRATIONS,14:MIGRATIONS[14]+('INVALID SQL',)}
        with patch.dict('migrations.MIGRATIONS',broken,clear=True),self.assertRaises(sqlite3.Error):migrate(self.path)
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],13)
            self.assertNotIn('manual_sector',{r[1] for r in db.execute('PRAGMA table_info(instrument_categories)')})
            self.assertEqual(db.execute('SELECT sector FROM instrument_categories').fetchone()[0],'Eigen sector')
        migrate(self.path);migrate(self.path)
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute('SELECT manual_sector,manual_country,manual_asset_type FROM instrument_categories').fetchone(),(1,0,1))
            self.assertEqual(db.execute('SELECT amount FROM dividends').fetchone()[0],'5.25')

    def test_final_price_migration_failure_rolls_back_and_restart_is_idempotent(self):
        self.create_old(14)
        broken={**MIGRATIONS,15:MIGRATIONS[15]+('INVALID SQL',)}
        with patch.dict('migrations.MIGRATIONS',broken,clear=True),self.assertRaises(sqlite3.Error):migrate(self.path)
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],14)
            self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='instrument_valuations'").fetchone())
            self.assertEqual(db.execute('SELECT amount FROM dividends').fetchone()[0],'5.25')
        migrate(self.path);migrate(self.path)
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM instrument_valuations').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT price FROM purchases').fetchone()[0],'999')
