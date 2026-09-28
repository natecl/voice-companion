"""Explicit, expiring two-capture phone experiment. Startup never grants funding."""
import json
import sqlite3
import time
from pathlib import Path
from admission import Rejected
from memory_budget import database

APPROVAL = 'proactive-phone-20260928-090'

class PhoneQA:
    def __init__(self, directory, *, clock=time.time):
        self.root=Path(directory);self.clock=clock
        self.config=json.loads((self.root/'proactive-phone-qa.json').read_text())
        if self.config['approval']!=APPROVAL:raise ValueError('Unknown phone QA approval')
        if not 0<self.config['expires']-self.config['starts']<=86400:raise ValueError('Invalid QA window')
        self.path=self.root/'proactive-phone-qa.sqlite'
        if not self.path.exists():raise ValueError('Provision phone QA first')
        self.usage=self.root/'proactive-20260928-025'/'usage.sqlite'
        if not self.usage.exists():raise ValueError('Existing feature ledger required')

    def active(self, owner):
        return owner==self.config['owner'] and self.config['starts']<=self.clock()<self.config['expires']

    def enroll(self,owner,capture):
        if not self.active(owner):raise Rejected('proactive_test_unavailable')
        with database(self.path,isolation_level=None) as db:
            db.execute('BEGIN IMMEDIATE')
            if not db.execute('SELECT 1 FROM capture WHERE id=?',(capture,)).fetchone():
                if db.execute('SELECT count(*) FROM capture').fetchone()[0]>=2:raise Rejected('proactive_test_complete')
                db.execute('INSERT INTO capture(id) VALUES(?)',(capture,))
            db.commit()

    def contains(self,owner,capture):
        # Keep test recordings out of personal learning even after expiry.
        if owner!=self.config['owner']:return False
        with database(self.path) as db:return bool(db.execute('SELECT 1 FROM capture WHERE id=?',(capture,)).fetchone())

    def sources(self,owner):
        if not self.active(owner):return set()
        with database(self.path) as db:return {r[0] for r in db.execute('SELECT id FROM capture')}

    def reserve(self,key,model):
        if not self.active(self.config['owner']) or model!='gpt-6-luna':raise Rejected('proactive_test_unavailable')
        with database(self.usage,isolation_level=None,timeout=2) as db:
            db.execute('BEGIN IMMEDIATE')
            count,total=db.execute('SELECT count(*),coalesce(sum(reserved),0) FROM attempts').fetchone()
            if count>=12 or total+20000>250000:raise Rejected('proactive_budget_limit')
            if db.execute('SELECT 1 FROM attempts WHERE id=?',(key,)).fetchone():raise Rejected('proactive_paid_retry')
            db.execute('INSERT INTO attempts VALUES(?,?,?, ?,NULL)',(key,'phone-runtime',20000,'reserved'))
            db.commit()

    def finish(self,key,usage=None):
        with database(self.usage) as db:
            db.execute('UPDATE attempts SET state=?,usage=? WHERE id=?',
                ('completed' if usage is not None else 'uncertain',json.dumps(usage),key))
