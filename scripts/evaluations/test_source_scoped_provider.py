import importlib.util
import io
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('source_scoped_provider',Path(__file__).with_name('source-scoped-provider.py'))
provider=importlib.util.module_from_spec(spec);spec.loader.exec_module(provider)

class BudgetTests(unittest.TestCase):
    def test_reallocation_is_idempotent_bounded_and_prevents_paid_retries(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(provider,'ROOT',Path(directory)):
            parent=Path(directory)/(provider.PARENT+'.sqlite')
            with sqlite3.connect(parent) as db:
                db.execute('CREATE TABLE allocation(id TEXT,cap INTEGER,combined_cap INTEGER)')
                db.execute('INSERT INTO allocation VALUES(?,?,?)',(provider.PARENT,250000,5550000))
                db.execute('CREATE TABLE attempts(id TEXT PRIMARY KEY,model TEXT,reserved INTEGER,state TEXT,usage TEXT)')
                db.execute('INSERT INTO attempts VALUES(?,?,?,?,NULL)',('old','old',135000,'completed'))
            provider.provision();provider.provision()
            with sqlite3.connect(parent) as db:
                self.assertEqual(db.execute('SELECT sum(reserved) FROM attempts').fetchone()[0],185000)
            def request(i):return dict(model='jev-1.13.0',state={'case':i},questions={'p0':{}})
            with patch.dict(provider.os.environ,{'TYPESAFE_API_KEY':'fixture'}),patch.object(provider.urllib.request,'urlopen',return_value=io.StringIO('{"usage":{}}')) as network:
                value=provider.run(request(0));self.assertEqual(provider.run(request(0)),value)
                self.assertEqual(network.call_count,1)
            with patch.dict(provider.os.environ,{'TYPESAFE_API_KEY':'fixture'}),patch.object(provider.urllib.request,'urlopen',side_effect=RuntimeError('failed')) as network:
                with self.assertRaises(RuntimeError):provider.run(request(1))
                with self.assertRaises(AssertionError):provider.run(request(1))
                with self.assertRaisesRegex(AssertionError,'QA model call limit'):provider.run(request(2))
                self.assertEqual(network.call_count,1)
