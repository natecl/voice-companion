import tempfile
from pathlib import Path
import unittest
from admission import Admission,Rejected
from profile_budget import provision,provision_rework_allowance,provision_consolidation_allowance,ProfileBudget

class ReworkBudgetTests(unittest.TestCase):
    def test_allowance_is_idempotent_bounded_and_not_automatic_for_old_callers(self):
        with tempfile.TemporaryDirectory() as folder:
            global_path,memory_path=(Path(folder)/n for n in ('usage.sqlite','memory.sqlite'))
            admission=Admission(global_path,total_microusd=5_000_000,limits={'ask':(2_500_000,3000,20)})
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
