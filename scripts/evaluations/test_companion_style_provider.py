import importlib.util,io,sqlite3,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('style_provider',Path(__file__).with_name('companion-style-provider.py'))
provider=importlib.util.module_from_spec(spec);spec.loader.exec_module(provider)

class BudgetTests(unittest.TestCase):
    def test_grant_cache_failed_reservation_and_ten_call_cap(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(provider,'ROOT',Path(folder)):
            root=Path(folder)
            with sqlite3.connect(root/'usage.sqlite') as db:
                db.executescript('CREATE TABLE budget(id INTEGER,cap INTEGER); INSERT INTO budget VALUES(1,5000000); CREATE TABLE request(reserved INTEGER);')
            for name,cap in [('matched-recall-20260927-030',300000),('unified-recall-20260927-025',250000)]:
                with sqlite3.connect(root/(name+'.sqlite')) as db:
                    db.execute('CREATE TABLE allocation(id TEXT,cap INTEGER)');db.execute('INSERT INTO allocation VALUES(?,?)',(name,cap))
            provider.provision();provider.provision()
            def req(i):return dict(model='gpt-6-luna',input=str(i),store=False,tools=[],service_tier='default',reasoning={'effort':'none'},max_output_tokens=1000,truncation='disabled',stream=False)
            with patch.dict(provider.os.environ,{'OPENAI_API_KEY':'fixture'}),patch.object(provider.urllib.request,'urlopen',side_effect=lambda *a,**k:io.StringIO('{"usage":{}}')) as network:
                saved=provider.run(req(0));self.assertEqual(provider.run(req(0)),saved)
                for i in range(1,9):provider.run(req(i))
                self.assertEqual(network.call_count,9)
            with patch.dict(provider.os.environ,{'OPENAI_API_KEY':'fixture'}),patch.object(provider.urllib.request,'urlopen',side_effect=RuntimeError('fixture failure')) as network:
                with self.assertRaises(RuntimeError):provider.run(req(9))
                with self.assertRaises(AssertionError):provider.run(req(9))
                with self.assertRaises(AssertionError):provider.run(req(10))
                self.assertEqual(network.call_count,1)
            with sqlite3.connect(root/(provider.ID+'.sqlite')) as db:
                self.assertEqual(db.execute('SELECT sum(reserved) FROM attempts').fetchone()[0],200000)
            with sqlite3.connect(root/'usage.sqlite') as db:
                self.assertEqual(db.execute('SELECT count(*) FROM request').fetchone()[0],0)
                self.assertEqual(db.execute('SELECT cap FROM budget').fetchone()[0],5000000)
