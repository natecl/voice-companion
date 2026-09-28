import unittest
from proactive_policy import ProactivePolicy
from test_memory import source


def live(revision=1, text='We are discussing sleep.'):
    return dict(source('capture', revision, text), completed=False)


class ProactivePolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = ProactivePolicy()
        self.policy.start('owner', 'capture')

    def test_delivers_once_and_cooldown_keeps_latest_for_later(self):
        p = self.policy
        first = p.observe(live(), 0)
        self.assertTrue(p.finish(first, 1, 'sleep'))
        self.assertIsNone(p.observe(live(), 61))
        self.assertIsNone(p.observe(live(2), 21))
        next_lease = p.observe(live(2), 62)
        self.assertIsNotNone(next_lease)
        self.assertFalse(p.finish(next_lease, 63, 'sleep'))

    def test_revision_invalidates_old_result_even_during_cooldown(self):
        p = self.policy
        first = p.observe(live(), 0)
        self.assertIsNone(p.observe(live(2, 'Correction: not sleep.'), 2))
        self.assertFalse(p.finish(first, 3, 'sleep'))
        self.assertIsNotNone(p.observe(live(2, 'Correction: not sleep.'), 21))

    def test_quiet_stop_owner_switch_and_background_reject_late_results(self):
        for action in [lambda p:p.quiet(),lambda p:p.stop(),lambda p:p.start('other','capture'),lambda p:p.background()]:
            p = ProactivePolicy();p.start('owner','capture')
            lease = p.observe(live(), 0)
            action(p)
            self.assertFalse(p.finish(lease, 1, 'sleep'))

    def test_return_requires_new_text_and_does_not_unquiet(self):
        p = self.policy;p.observe(live(),0);p.background();p.resume()
        self.assertIsNone(p.observe(live(),100))
        self.assertIsNotNone(p.observe(live(2),101))
        p.quiet();p.background();p.resume()
        self.assertIsNone(p.observe(live(3),200))

    def test_failure_and_timeout_do_not_retry_same_cutoff(self):
        p = self.policy;lease = p.observe(live(),0)
        self.assertFalse(p.finish(lease,16,'sleep'))
        self.assertIsNone(p.observe(live(),40))
        next_lease = p.observe(live(2),41)
        self.assertFalse(p.finish(next_lease,42))
        self.assertIsNone(p.observe(live(2),80))

    def test_attempt_cap_and_pending_no_duplicate(self):
        p = self.policy;p.max_attempts = 1
        lease = p.observe(live(),0)
        self.assertIsNone(p.observe(live(),1))
        p.finish(lease,2)
        self.assertIsNone(p.observe(live(2),30))
