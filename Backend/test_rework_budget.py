import tempfile
from pathlib import Path
import unittest
from admission import Admission,Rejected
from profile_budget import provision,provision_rework_allowance,provision_consolidation_allowance,provision_multisource_allowance,ProfileBudget

class ReworkBudgetTests(unittest.TestCase):
    def test_allowance_is_idempotent_bounded_and_not_automatic_for_old_callers(self):
        with tempfile.TemporaryDirectory() as folder:
            global_path,memory_path=(Path(folder)/n for n in ('usage.sqlite','memory.sqlite'))
            admission=Admission(global_path,total_microusd=5_000_000,limits={'ask':(2_500_000,3000,20),'jev':(500_000,500,64)})
            self.addCleanup(admission.close);admission.enroll()
            provision(global_path,memory_path)
            provision_rework_allowance(global_path,memory_path);provision_rework_allowance(global_path,memory_path)
            budget=ProfileBudget(memory_path,include_rework_allowance=True)
            for i in range(200):budget.reserve(str(i),'jev-1.13.0')
            with self.assertRaisesRegex(Rejected,'profile_budget_limit'):budget.reserve('overflow','jev-1.13.0')
            with self.assertRaisesRegex(Rejected,'paid_retry'):budget.reserve('0','jev-1.13.0')
            self.assertEqual(ProfileBudget(memory_path).cap,1_000_000)
            self.assertEqual(admission.db.execute('SELECT count(*) FROM request').fetchone()[0],2)
            self.assertEqual(admission.db.execute('SELECT sum(reserved) FROM request').fetchone()[0],2_000_000)

            provision_consolidation_allowance(global_path,memory_path)
            provision_consolidation_allowance(global_path,memory_path)
            expanded=ProfileBudget(memory_path,include_rework_allowance=True,include_consolidation_allowance=True)
            for i in range(20):expanded.reserve('additional-'+str(i),'jev-1.13.0')
            with self.assertRaisesRegex(Rejected,'profile_budget_limit'):expanded.reserve('overflow2','jev-1.13.0')
            self.assertEqual(ProfileBudget(memory_path,include_rework_allowance=True).cap,2_000_000)
            self.assertEqual(admission.db.execute('SELECT sum(reserved) FROM request').fetchone()[0],2_200_000)

            provision_multisource_allowance(global_path,memory_path)
            provision_multisource_allowance(global_path,memory_path)
            latest=ProfileBudget(memory_path,include_rework_allowance=True,include_consolidation_allowance=True,include_multisource_allowance=True)
            for i in range(20):latest.reserve('multisource-'+str(i),'jev-1.13.0')
            with self.assertRaisesRegex(Rejected,'profile_budget_limit'):latest.reserve('overflow3','jev-1.13.0')
            self.assertEqual(expanded.cap,2_200_000)
            self.assertEqual(admission.db.execute('SELECT sum(reserved) FROM request').fetchone()[0],2_400_000)

            self.assertEqual(admission.db.execute("SELECT sum(reserved) FROM request WHERE category='ask'").fetchone()[0],2_300_000)
            self.assertEqual(admission.db.execute("SELECT sum(reserved) FROM request WHERE category='jev'").fetchone()[0],100_000)
            self.assertEqual(admission.db.execute("SELECT cap FROM policy WHERE category='ask'").fetchone()[0],2_500_000)

    def test_split_failure_reserves_nothing_and_does_not_expose_credit(self):
        with tempfile.TemporaryDirectory() as folder:
            global_path,memory_path=(Path(folder)/n for n in ('usage.sqlite','memory.sqlite'))
            admission=Admission(global_path,total_microusd=5_000_000,limits={'ask':(2_500_000,3000,20),'jev':(50_000,500,64)})
            self.addCleanup(admission.close);admission.enroll()
            provision(global_path,memory_path);provision_rework_allowance(global_path,memory_path)
            provision_consolidation_allowance(global_path,memory_path)
            before=admission.db.execute('SELECT count(*),sum(reserved) FROM request').fetchone()
            with self.assertRaisesRegex(Rejected,'budget_limit'):provision_multisource_allowance(global_path,memory_path)
            self.assertEqual(admission.db.execute('SELECT count(*),sum(reserved) FROM request').fetchone(),before)
            self.assertEqual(ProfileBudget(memory_path,include_rework_allowance=True,include_consolidation_allowance=True).cap,2_200_000)

class RolloutBudgetTests(unittest.TestCase):
    def fixture(self,folder):
        from service_policy import STT,ASK,RETIRED_JEV
        paths=Path(folder)/'usage.sqlite',Path(folder)/'budget.sqlite'
        admission=Admission(paths[0],total_microusd=5_000_000,limits={'stt':STT,'ask':ASK,'jev':RETIRED_JEV})
        admission.enroll();self.addCleanup(admission.close)
        provision(*paths);provision_rework_allowance(*paths);provision_consolidation_allowance(*paths);provision_multisource_allowance(*paths)
        return paths,admission

    def test_explicit_redistribution_is_idempotent_and_startup_preserves_it(self):
        import os
        from unittest.mock import patch
        from profile_budget import provision_rollout_allowance
        from service_policy import open_ledger,ROLLOUT_POLICIES
        from hosted import validate_rework_allocations
        with tempfile.TemporaryDirectory() as folder:
            paths,admission=self.fixture(folder)
            before=admission.db.execute('SELECT * FROM request ORDER BY id').fetchall()
            provision_rollout_allowance(*paths);provision_rollout_allowance(*paths)
            self.assertEqual(admission.db.execute('SELECT cap FROM budget').fetchone(),(5_000_000,))
            self.assertEqual(admission.db.execute('SELECT sum(reserved) FROM request').fetchone(),(2_900_000,))
            self.assertEqual(dict((r[0],tuple(r[1:])) for r in admission.db.execute('SELECT * FROM policy')),ROLLOUT_POLICIES)
            for row in before:self.assertEqual(admission.db.execute('SELECT * FROM request WHERE id=?',(row[0],)).fetchone(),row)
            validate_rework_allocations(admission,rollout=True)
            old=ProfileBudget(paths[1],include_rework_allowance=True,include_consolidation_allowance=True,include_multisource_allowance=True)
            self.assertEqual(old.cap,2_400_000)
            new=ProfileBudget(paths[1],include_rework_allowance=True,include_consolidation_allowance=True,include_multisource_allowance=True,include_rollout_allowance=True)
            for i in range(290):new.reserve(str(i),'gpt-6-luna')
            with self.assertRaisesRegex(Rejected,'profile_budget_limit'):new.reserve('over','gpt-6-luna')
            with self.assertRaisesRegex(Rejected,'paid_retry'):new.reserve('0','gpt-6-luna')
            with patch.dict(os.environ,{'VOICE_DATA_DIR':folder,'VOICE_ENABLE_ASK':'1'}):
                reopened=open_ledger(migrate=True)
                self.assertEqual(reopened.usage(),admission.usage());reopened.close()

    def test_conflicting_reservation_rolls_back_policy_and_exposes_no_allowance(self):
        from profile_budget import provision_rollout_allowance,ROLLOUT_APPROVAL_ID
        with tempfile.TemporaryDirectory() as folder:
            paths,admission=self.fixture(folder)
            credential=admission.db.execute('SELECT id FROM credential').fetchone()[0]
            admission.db.execute('INSERT INTO request VALUES(?,?,?,?,?,?)',(ROLLOUT_APPROVAL_ID+':jev',credential,'jev',0,1,'completed'))
            before=admission.db.execute('SELECT * FROM policy').fetchall()
            with self.assertRaisesRegex(ValueError,'Allowance conflicts'):provision_rollout_allowance(*paths)
            self.assertEqual(admission.db.execute('SELECT * FROM policy').fetchall(),before)
            import sqlite3
            with sqlite3.connect(paths[1]) as db:self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='profile_rollout_allowance'").fetchone())

    def test_recording_usage_cannot_be_erased_to_make_room(self):
        from profile_budget import provision_rollout_allowance
        with tempfile.TemporaryDirectory() as folder:
            paths,admission=self.fixture(folder)
            credential=admission.db.execute('SELECT id FROM credential').fetchone()[0]
            admission.db.execute('INSERT INTO request VALUES(?,?,?,?,?,?)',('previous',credential,'stt',0,1_500_001,'completed'))
            before=admission.db.execute('SELECT * FROM policy').fetchall()
            with self.assertRaisesRegex(ValueError,'Existing usage'):provision_rollout_allowance(*paths)
            self.assertEqual(admission.db.execute('SELECT * FROM policy').fetchall(),before)

    def test_preference_allowance_remains_opt_in_and_survives_restart(self):
        import os
        from unittest.mock import patch
        from profile_budget import provision_rollout_allowance,provision_preference_allowance
        from service_policy import open_ledger,PREFERENCE_POLICIES
        with tempfile.TemporaryDirectory() as folder:
            paths,admission=self.fixture(folder);provision_rollout_allowance(*paths)
            before=admission.db.execute('SELECT * FROM request ORDER BY id').fetchall()
            provision_preference_allowance(*paths);provision_preference_allowance(*paths)
            self.assertEqual(admission.db.execute('SELECT sum(reserved) FROM request').fetchone(),(3_200_000,))
            self.assertEqual(admission.db.execute('SELECT cap FROM budget').fetchone(),(5_000_000,))
            for row in before:self.assertEqual(admission.db.execute('SELECT * FROM request WHERE id=?',(row[0],)).fetchone(),row)
            options=dict(include_rework_allowance=True,include_consolidation_allowance=True,include_multisource_allowance=True,include_rollout_allowance=True)
            self.assertEqual(ProfileBudget(paths[1],**options).cap,2_900_000)
            new=ProfileBudget(paths[1],include_preference_allowance=True,**options)
            for i in range(320):new.reserve(str(i),'jev-1.13.0')
            with self.assertRaisesRegex(Rejected,'profile_budget_limit'):new.reserve('over','jev-1.13.0')
            with patch.dict(os.environ,{'VOICE_DATA_DIR':folder,'VOICE_ENABLE_ASK':'1'}):
                reopened=open_ledger(migrate=True)
                self.assertEqual(dict((r[0],tuple(r[1:])) for r in reopened.db.execute('SELECT * FROM policy')),PREFERENCE_POLICIES)
                self.assertEqual(reopened.usage(),admission.usage());reopened.close()
