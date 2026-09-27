import importlib.util
import io
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('notes_first_provider',Path(__file__).with_name('notes-first-provider.py'))
provider=importlib.util.module_from_spec(spec);spec.loader.exec_module(provider)

class BudgetTests(unittest.TestCase):
    def test_idempotent_grant_cache_model_cap_and_no_paid_retry(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(provider,'ROOT',Path(folder)):
            with closing(sqlite3.connect(Path(folder)/'usage.sqlite')) as db, db:
                db.executescript('''CREATE TABLE budget(id INTEGER,cap INTEGER); INSERT INTO budget VALUES(1,5000000);
                CREATE TABLE request(id TEXT PRIMARY KEY,credential TEXT,category TEXT,created REAL,reserved INTEGER,state TEXT);
                CREATE TABLE policy(category TEXT,cap INTEGER); INSERT INTO policy VALUES('stt',70000),('jev',80000);
                CREATE TABLE credential(id TEXT); INSERT INTO credential VALUES('fixture');
                CREATE TABLE allocation_request(id TEXT PRIMARY KEY);''')
            provider.provision();provider.provision()
            with closing(sqlite3.connect(Path(folder)/'usage.sqlite')) as db, db:
                self.assertEqual(db.execute('SELECT sum(reserved) FROM request').fetchone()[0],150000)
            def req(i):return dict(model='jev-1.13.0',state={'case':i},questions={'p0':{}})
            with patch.dict(provider.os.environ,{'TYPESAFE_API_KEY':'fixture-unused'}), patch.object(provider.urllib.request,'urlopen',side_effect=lambda *a,**k:io.StringIO('{"usage":{}}')) as network:
                first=provider.run(req(0));self.assertEqual(provider.run(req(0)),first)
                self.assertEqual(network.call_count,1)
                for i in range(1,6):provider.run(req(i))
                with self.assertRaisesRegex(AssertionError,'QA model call limit'):provider.run(req(6))
                self.assertEqual(network.call_count,6)
            # A failed call keeps its reservation; repeating it cannot hit the provider.
            luna=dict(model='gpt-6-luna',store=False,tools=[],service_tier='default',reasoning={'effort':'none'},max_output_tokens=1000)
            with patch.dict(provider.os.environ,{'OPENAI_API_KEY':'fixture-unused'}), patch.object(provider.urllib.request,'urlopen',side_effect=RuntimeError('fixture network failure')) as network:
                with self.assertRaises(RuntimeError):provider.run(luna)
                with self.assertRaisesRegex(AssertionError,'No automatic paid retry'):provider.run(luna)
                self.assertEqual(network.call_count,1)
