import tempfile
from pathlib import Path
import unittest
from admission import Admission,Rejected
from memory_budget import database
from notes_budget import NotesBudget,PER_CALL
from hosted import notes_setting

class NotesBudgetTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        root=Path(self.folder.name)
        self.admission=Admission(root/'global.sqlite',total_microusd=100000,limits={'ask':(100000,50000,10)})
        self.addCleanup(self.admission.close)
        self.path=root/'notes.sqlite'
    def provision(self):
        credential,token=self.admission.enroll()
        reservation=self.admission.reserve(token,'ask')
        self.admission.db.execute('CREATE TABLE IF NOT EXISTS allocation_request(id TEXT PRIMARY KEY)')
        self.admission.db.execute('INSERT INTO allocation_request VALUES(?)',(reservation,))
        with database(self.path) as db:
            db.execute('CREATE TABLE notes_allocation(id TEXT PRIMARY KEY,cap INTEGER,max_calls INTEGER)')
            db.execute('INSERT INTO notes_allocation VALUES(?,?,?)',(reservation,50000,2))
            db.execute('CREATE TABLE notes_attempt(id TEXT PRIMARY KEY,reserved INTEGER,state TEXT,usage TEXT)')
    def test_two_reservations_survive_reopen_and_no_refunds(self):
        self.provision();budget=NotesBudget(self.path,self.admission)
        budget.reserve('a','gpt-6-luna');budget.finish('a')
        with self.assertRaisesRegex(Rejected,'paid_retry'):budget.reserve('a','gpt-6-luna')
        budget=NotesBudget(self.path,self.admission);budget.reserve('b','gpt-6-luna');budget.finish('b',{})
        with self.assertRaisesRegex(Rejected,'budget_limit'):budget.reserve('c','gpt-6-luna')
        with database(self.path) as db:self.assertEqual(db.execute('SELECT sum(reserved) FROM notes_attempt').fetchone()[0],2*PER_CALL)
    def test_requires_global_funding_and_explicit_flag(self):
        with self.assertRaises(ValueError):NotesBudget(self.path,self.admission)
        self.provision()
        self.admission.db.execute('DELETE FROM allocation_request')
        with self.assertRaises(ValueError):NotesBudget(self.path,self.admission)
        self.assertFalse(notes_setting({}))
        with self.assertRaises(ValueError):notes_setting({'VOICE_ENABLE_RECORDING_NOTES':'1'})
        self.assertTrue(notes_setting({'VOICE_ENABLE_RECORDING_NOTES':'1','VOICE_ENABLE_MEMORY':'1'}))
