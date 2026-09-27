"""Fail-closed notes subledger. Operator provisioning is separate from startup."""
import json
from pathlib import Path
from admission import Rejected
from memory_budget import database

PER_CALL = 25_000

class NotesBudget:
    def __init__(self,path,admission):
        self.path=Path(path)
        if not self.path.exists():raise ValueError('Provision notes allowance before enablement')
        with database(self.path) as db:
            rows=db.execute('SELECT id,cap,max_calls FROM notes_allocation').fetchall()
            if len(rows)!=1:raise ValueError('One explicit notes allocation required')
            self.approval,self.cap,self.max_calls=rows[0]
            if self.cap<=0 or self.max_calls<=0 or self.cap>self.max_calls*PER_CALL:
                raise ValueError('Invalid notes allocation')
            allocated=admission.db.execute('SELECT reserved FROM request WHERE id=?',(self.approval,)).fetchone()
            marker=admission.db.execute('SELECT 1 FROM allocation_request WHERE id=?',(self.approval,)).fetchone()
            if allocated is None or allocated[0]!=self.cap or not marker:
                raise ValueError('Notes allowance must already be reserved globally')

    def reserve(self,attempt,model):
        if model!='gpt-6-luna':raise Rejected('unapproved_notes_model')
        with database(self.path,isolation_level=None,timeout=2) as db:
            db.execute('BEGIN IMMEDIATE')
            count,total=db.execute('SELECT count(*),coalesce(sum(reserved),0) FROM notes_attempt').fetchone()
            if count>=self.max_calls or total+PER_CALL>self.cap:raise Rejected('notes_budget_limit')
            if db.execute('SELECT 1 FROM notes_attempt WHERE id=?',(attempt,)).fetchone():raise Rejected('notes_paid_retry')
            db.execute('INSERT INTO notes_attempt VALUES(?,?,?,NULL)',(attempt,PER_CALL,'reserved'))
            db.commit()

    def finish(self,attempt,usage=None):
        # Never refund a dispatched/uncertain call. Usage is evidence, not credit.
        with database(self.path) as db:
            db.execute('UPDATE notes_attempt SET state=?,usage=? WHERE id=?',
                ('completed' if usage is not None else 'uncertain',json.dumps(usage),attempt))
