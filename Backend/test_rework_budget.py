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
