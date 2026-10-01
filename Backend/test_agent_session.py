import dataclasses
import math
import unittest
import agent_session as a

OWNER, OTHER = 'owner-a', 'owner-b'
CAPTURE = 'capture-1'
TTL = 15.0
IDLE = dict(pending_direct_turn=False, anchor_complete=True)
RESTART = 'restart'
EXPECTED_SURVIVAL = {(a.REPLY, a.QUIET)}


def main(owner=OWNER, epoch_floor=0):
    return a.reconnected(a.restore_session(owner, epoch_floor, quiet_capture=a.OFF, quiet_main=a.OFF))


def capturing(owner=OWNER, capture=CAPTURE):
    return a.user_started_capture(main(owner), owner, capture, verified=True)


def paused():
    return a.user_paused(capturing(), OWNER, CAPTURE)


def restart(session):
    return a.reconnected(a.restore_session(session.owner, session.epoch, quiet_capture=session.quiet_capture,
                                           quiet_main=session.quiet_main, capture=session.capture))


def emit(session, lease, now=1.0, **context):
    return a.may_emit(session, lease, now, **{**IDLE, **context})


def cue(session, now=0.0, revision=1):
    return a.issue_cue(session, now, TTL, revision, pending_direct_turn=False)


def followup(session, now=0.0):
    return a.issue_followup(session, now, TTL, **IDLE)


TRANSITIONS = {
    a.QUIET: a.quiet,
    a.CAPTURE_START: lambda s: a.user_started_capture(s, s.owner, 'capture-2', verified=True),
    a.PAUSE: lambda s: a.user_paused(s, s.owner, CAPTURE),
    a.RESUME: lambda s: a.user_resumed(s, s.owner, CAPTURE, 99),
    a.STOP: lambda s: a.user_stopped(s, s.owner, CAPTURE),
    a.BACKGROUND: a.backgrounded,
    a.REVOKE: a.revoked,
    RESTART: restart,
}
LIVE_CAPTURE = {'none': None, 'bound': CAPTURE, 'unknown': 'capture-x'}


def issue(session, kind, binding):
    if kind == a.REPLY: return a.issue_reply(session, 0.0, 20.0, live_capture=LIVE_CAPTURE[binding])
    return cue(session) if kind == a.CUE else followup(session)


class ImmutabilityTests(unittest.TestCase):
    def test_state_and_leases_cannot_be_mutated(self):
        session = capturing()
        lease = a.issue_reply(session, 0.0, 20.0, live_capture=CAPTURE)
        for value, field in ((session, 'epoch'), (session.capture, 'state'), (lease, 'epoch'), (lease, 'owner')):
            with self.subTest(field=field), self.assertRaises(dataclasses.FrozenInstanceError):
                setattr(value, field, 'changed')

    def test_transitions_return_new_state_and_leave_the_original_intact(self):
        before = capturing()
        snapshot = dataclasses.asdict(before)
        for change in (a.quiet, TRANSITIONS[a.PAUSE], TRANSITIONS[a.STOP], a.backgrounded, a.revoked, a.chat_changed):
            with self.subTest(change=change):
                self.assertIsNot(change(before), before)
                self.assertEqual(dataclasses.asdict(before), snapshot)


class SurvivalMatrixTests(unittest.TestCase):
    def test_every_constructible_kind_transition_binding_matches_the_survival_table(self):
        covered = set()
        for name, start in (('main', main()), ('capture', capturing()), ('paused', paused())):
            for kind, binding in ((a.REPLY, 'none'), (a.REPLY, 'bound'), (a.CUE, 'bound'), (a.FOLLOWUP, 'none')):
                try: lease = issue(start, kind, binding)
                except a.Denied: continue
                self.assertEqual(emit(start, lease), a.OK)
                for transition, apply in TRANSITIONS.items():
                    try: after = apply(start)
                    except a.Denied: continue
                    with self.subTest(state=name, kind=kind, binding=binding, transition=transition):
                        reason = emit(after, lease, 2.0)
                        if (kind, transition) in EXPECTED_SURVIVAL: self.assertEqual(reason, a.OK)
                        else: self.assertIn(reason, ('epoch_changed', 'revoked'))
                    covered.add((kind, binding, transition))
        everything = set(TRANSITIONS)
        capture_bound = everything - {a.CAPTURE_START, a.RESUME}   # no active capture to bind before these
        expected = ({(a.REPLY, 'none', t) for t in everything - {a.RESUME}}   # nothing is issued while paused
                    | {(a.REPLY, 'bound', t) for t in capture_bound}
                    | {(a.CUE, 'bound', t) for t in capture_bound}
                    | {(a.FOLLOWUP, 'none', t) for t in (a.QUIET, a.CAPTURE_START, a.BACKGROUND, a.REVOKE, RESTART)})
        self.assertEqual(covered, expected)

    def test_unknown_and_foreign_bindings_never_emit_before_or_after_any_transition(self):
        session = capturing()
        valid = a.issue_reply(session, 0.0, 20.0, live_capture=CAPTURE)
        for binding in (a.UNKNOWN, 'capture-x'):
            forged = dataclasses.replace(valid, binding=binding)
            self.assertNotEqual(emit(session, forged), a.OK)
            for transition, apply in TRANSITIONS.items():
                try: after = apply(session)
                except a.Denied: continue
                with self.subTest(binding=binding, transition=transition):
                    self.assertNotEqual(emit(after, forged, 2.0), a.OK)

    def test_resume_and_stop_from_paused_or_unknown_invalidate_any_lease_of_that_epoch(self):
        template = a.issue_reply(capturing(), 0.0, 20.0, live_capture=CAPTURE)
        unknown = a.reconnected(a.restore_session(OWNER, 4, quiet_capture=a.OFF, capture=a.Capture(CAPTURE, 'corrupt')))
        for start in (paused(), unknown):
            for kind, binding in ((a.REPLY, None), (a.REPLY, CAPTURE), (a.REPLY, a.UNKNOWN), (a.CUE, CAPTURE), (a.FOLLOWUP, None)):
                forged = dataclasses.replace(template, kind=kind, binding=binding, epoch=start.epoch, mode=start.mode, revision=1)
                for transition in (a.RESUME, a.STOP):
                    with self.subTest(state=start.capture.state, kind=kind, binding=binding, transition=transition):
                        self.assertEqual(emit(TRANSITIONS[transition](start), forged), 'epoch_changed')

    def test_reply_survives_quiet_alone(self):
        session = capturing()
        lease = a.issue_reply(session, 0.0, 20.0, live_capture=CAPTURE)
        quieted = a.quiet(a.quiet(session))
        self.assertEqual(emit(quieted, lease), a.OK)
        self.assertEqual(emit(a.chat_changed(quieted), lease), a.OK)
        self.assertEqual(emit(a.backgrounded(quieted), lease), 'epoch_changed')
        self.assertEqual(emit(TRANSITIONS[a.STOP](quieted), lease), 'epoch_changed')


class ConsentAndBindingTests(unittest.TestCase):
    def test_capture_start_requires_owner_and_verified_user_start(self):
        session = main()
        for owner, verified, reason in ((OTHER, True, 'owner_mismatch'), (OWNER, False, 'capture_unverified'),
                                        (OWNER, None, 'capture_unverified'), (OWNER, 'yes', 'capture_unverified')):
            with self.subTest(owner=owner, verified=verified), self.assertRaises(a.Denied) as denied:
                a.user_started_capture(session, owner, CAPTURE, verified)
            self.assertEqual(denied.exception.reason, reason)

    def test_second_capture_cannot_replace_a_live_paused_or_unknown_binding(self):
        unknown = a.restore_session(OWNER, 3, capture=a.Capture(CAPTURE, 'corrupt'))
        for session in (capturing(), paused(), unknown):
            with self.subTest(state=session.capture.state), self.assertRaises(a.Denied) as denied:
                a.user_started_capture(session, OWNER, 'capture-2', True)
            self.assertEqual(denied.exception.reason, 'capture_already_bound')

    def test_capture_controls_reject_foreign_capture_and_other_owner(self):
        session = capturing()
        controls = (lambda o, c: a.user_paused(session, o, c), lambda o, c: a.user_stopped(session, o, c),
                    lambda o, c: a.user_resumed(paused(), o, c, 1))
        for control in controls:
            for owner, capture, reason in ((OWNER, 'capture-x', 'capture_foreign'), (OTHER, CAPTURE, 'owner_mismatch')):
                with self.subTest(owner=owner, capture=capture), self.assertRaises(a.Denied) as denied:
                    control(owner, capture)
                self.assertEqual(denied.exception.reason, reason)

    def test_reply_naming_unverified_or_stopped_capture_is_denied(self):
        cases = ((capturing(), 'capture-x', 'capture_unknown'), (main(), CAPTURE, 'capture_unknown'),
                 (TRANSITIONS[a.STOP](capturing()), CAPTURE, 'capture_stopped'))
        for session, live, reason in cases:
            with self.subTest(live=live, reason=reason), self.assertRaises(a.Denied) as denied:
                a.issue_reply(session, 0.0, 20.0, live_capture=live)
            self.assertEqual(denied.exception.reason, reason)

    def test_leases_are_bound_to_their_owner(self):
        mine, theirs = capturing(OWNER), capturing(OTHER)
        self.assertEqual(mine.epoch, theirs.epoch)
        for lease in (a.issue_reply(mine, 0.0, 20.0), a.issue_reply(mine, 0.0, 20.0, CAPTURE), cue(mine)):
            with self.subTest(kind=lease.kind):
                self.assertEqual(emit(theirs, lease), 'owner_mismatch')
                self.assertEqual(emit(mine, lease), a.OK)

    def test_restart_without_a_durable_capture_creates_no_consent(self):
        session = a.reconnected(a.restore_session(OWNER, 5, quiet_capture=a.OFF, quiet_main=a.OFF))
        self.assertIsNone(session.capture)
        with self.assertRaises(a.Denied) as denied: cue(session)
        self.assertEqual(denied.exception.reason, 'no_capture')


def every_issue(session):
    return (lambda: cue(session), lambda: followup(session), lambda: a.issue_reply(session, 0.0, 10.0),
            lambda: a.issue_reply(session, 0.0, 10.0, CAPTURE))


class FailClosedStateTests(unittest.TestCase):
    def test_paused_or_unknown_capture_denies_all_output_including_unbound_replies(self):
        restored = lambda state: a.restore_session(
            OWNER, 2, quiet_capture=a.OFF, quiet_main=a.OFF, capture=a.Capture(CAPTURE, state))
        cases = (('paused', paused(), 'capture_paused'),
                 ('paused-background', a.backgrounded(paused()), 'capture_paused'),
                 ('restored-paused', a.reconnected(restored(a.PAUSED)), 'capture_paused'),
                 ('restored-unknown', a.reconnected(restored('corrupt')), 'capture_unknown'),
                 ('restored-unknown-background', restored('corrupt'), 'capture_unknown'))
        for name, session, reason in cases:
            for attempt in every_issue(session):
                with self.subTest(state=name), self.assertRaises(a.Denied) as denied:
                    attempt()
                self.assertEqual(denied.exception.reason, reason)

    def test_ordinary_main_chat_without_a_live_capture_allows_unbound_replies(self):
        never_captured = main()
        after_stop = TRANSITIONS[a.STOP](capturing())
        for session in (never_captured, after_stop):
            with self.subTest(capture=session.capture):
                self.assertEqual(session.mode, a.MAIN_CHAT)
                self.assertEqual(emit(session, a.issue_reply(session, 0.0, 10.0), 1.0), a.OK)

    def test_explicit_resume_or_stop_restores_reply_eligibility(self):
        unknown = a.reconnected(a.restore_session(OWNER, 2, quiet_capture=a.OFF, capture=a.Capture(CAPTURE, 'corrupt')))
        for start in (paused(), unknown):
            resumed = a.user_resumed(start, OWNER, CAPTURE, 3)
            stopped = a.user_stopped(start, OWNER, CAPTURE)
            with self.subTest(state=start.capture.state):
                self.assertEqual(emit(resumed, a.issue_reply(resumed, 0.0, 10.0, CAPTURE)), a.OK)
                self.assertEqual(emit(resumed, a.issue_reply(resumed, 0.0, 10.0)), a.OK)
                self.assertEqual(emit(stopped, a.issue_reply(stopped, 0.0, 10.0)), a.OK)

    def test_invalid_or_inconsistent_session_state_denies_every_kind(self):
        base = capturing()
        lease = a.issue_reply(base, 0.0, 10.0)
        bound = a.issue_reply(base, 0.0, 10.0, CAPTURE)
        cases = ((dataclasses.replace(base, mode='bogus'), 'mode_invalid'),
                 (dataclasses.replace(base, capture=None), 'mode_invalid'),
                 (dataclasses.replace(base, mode=a.MAIN_CHAT), 'mode_invalid'),
                 (dataclasses.replace(base, capture=a.Capture(CAPTURE, 'bogus')), 'capture_unknown'))
        for session, reason in cases:
            for value in (lease, bound, cue(base)):
                with self.subTest(mode=session.mode, capture=session.capture, kind=value.kind):
                    self.assertEqual(emit(session, value), reason)

    def test_non_boolean_foreground_and_busy_flags_fail_closed(self):
        chat, live = main(), capturing()
        self.assertEqual(emit(dataclasses.replace(chat, foreground='no'), followup(chat)), 'background')
        for busy in (0, '', 'no'):
            self.assertEqual(emit(live, cue(live), pending_direct_turn=busy), 'chat_busy')

    def test_unknown_or_unreadable_quiet_suppresses_unsolicited_output_only(self):
        for value in (a.UNKNOWN, None, 'maybe'):
            with self.subTest(value=value):
                chat = a.reconnected(a.restore_session(OWNER, 1, quiet_main=value))
                live = a.reconnected(a.restore_session(OWNER, 1, quiet_capture=value, capture=a.Capture(CAPTURE)))
                for attempt in (lambda: followup(chat), lambda: cue(live)):
                    with self.assertRaises(a.Denied) as denied: attempt()
                    self.assertEqual(denied.exception.reason, 'quiet')
                self.assertEqual(emit(live, a.issue_reply(live, 0.0, 20.0, CAPTURE)), a.OK)

    def test_unknown_chat_state_denies_unsolicited_work(self):
        session = capturing()
        lease = cue(session)
        self.assertEqual(a.may_emit(session, lease, 1.0), 'chat_state_unknown')
        chat = main()
        self.assertEqual(a.may_emit(chat, followup(chat), 1.0, pending_direct_turn=False), 'chat_changed')


class NoAutomaticResumeTests(unittest.TestCase):
    def test_only_a_user_resume_reactivates_a_paused_capture(self):
        start = paused()
        for name, change in (('background', a.backgrounded), ('reconnect', a.reconnected), ('quiet', a.quiet),
                             ('chat', a.chat_changed), ('restart', restart),
                             ('background-reconnect-restart', lambda s: restart(a.reconnected(a.backgrounded(s))))):
            with self.subTest(change=name):
                after = change(start)
                self.assertEqual(after.capture.state, a.PAUSED)
                with self.assertRaises(a.Denied) as denied: cue(a.reconnected(after), revision=200)
                self.assertEqual(denied.exception.reason, 'capture_paused')
        resumed = a.user_resumed(start, OWNER, CAPTURE, 5)
        self.assertEqual(emit(resumed, cue(resumed, revision=6)), a.OK)

    def test_reconnect_preserves_quiet_and_capture_state(self):
        session = a.backgrounded(a.quiet(capturing()))
        back = a.reconnected(session)
        self.assertEqual((back.capture, back.quiet_capture, back.epoch), (session.capture, a.ON, session.epoch))


class RaceAndLateResultTests(unittest.TestCase):
    def test_quiet_before_provider_result_drops_the_cue_and_stays_suppressive(self):
        session = capturing()
        lease = cue(session)
        quieted = a.quiet(session)
        for now in (0.5, 5.0, TTL):
            self.assertEqual(emit(quieted, lease, now), 'epoch_changed')
        with self.assertRaises(a.Denied) as denied: cue(quieted, 20.0, 2)
        self.assertEqual(denied.exception.reason, 'quiet')

    def test_stop_between_stream_check_and_commit_check_blocks_the_commit(self):
        session = capturing()
        lease = a.issue_reply(session, 0.0, 20.0, CAPTURE)
        self.assertEqual(emit(session, lease, 1.0), a.OK)
        self.assertEqual(emit(TRANSITIONS[a.STOP](session), lease, 1.1), 'epoch_changed')

    def test_stop_invalidates_a_reply_that_started_before_the_capture(self):
        session = main()
        lease = a.issue_reply(session, 0.0, 20.0)
        live = a.user_started_capture(session, OWNER, CAPTURE, True)
        self.assertEqual(emit(live, lease), 'epoch_changed')
        self.assertEqual(emit(TRANSITIONS[a.STOP](live), lease), 'epoch_changed')

    def test_quiet_in_capture_suppresses_the_later_main_chat_followup(self):
        stopped = TRANSITIONS[a.STOP](a.quiet(capturing()))
        with self.assertRaises(a.Denied) as denied: followup(stopped)
        self.assertEqual(denied.exception.reason, 'quiet')

    def test_provider_ignoring_cancellation_cannot_deliver_late_or_into_a_new_capture(self):
        session = capturing()
        leases = (cue(session), a.issue_reply(session, 0.0, 20.0, CAPTURE))
        stopped = TRANSITIONS[a.STOP](session)
        later = (stopped, a.reconnected(stopped), restart(stopped),
                 a.user_started_capture(stopped, OWNER, 'capture-2', True))
        for lease in leases:
            for state in later:
                with self.subTest(kind=lease.kind, epoch=state.epoch):
                    self.assertNotEqual(emit(state, lease, 3.0), a.OK)


class EpochTests(unittest.TestCase):
    def test_every_transition_advances_the_epoch_by_one_and_others_do_not(self):
        session = capturing()
        for transition in (a.QUIET, a.PAUSE, a.RESUME, a.STOP, a.CAPTURE_START, a.BACKGROUND, a.REVOKE):
            after = TRANSITIONS[transition](session)
            self.assertEqual(after.epoch, session.epoch + 1, transition)
            session = after if transition != a.REVOKE else session
        self.assertEqual(a.chat_changed(session).epoch, session.epoch)
        self.assertEqual(a.reconnected(session).epoch, session.epoch)

    def test_restart_starts_above_the_floor_and_rejects_earlier_and_future_leases(self):
        session = capturing()
        lease = a.issue_reply(session, 0.0, 20.0)
        restored = restart(session)
        self.assertEqual(restored.epoch, session.epoch + 1)
        self.assertEqual(emit(restored, lease), 'epoch_changed')
        self.assertEqual(emit(a.restore_session(OWNER, 0), dataclasses.replace(lease, epoch=50)), 'epoch_invalid')
        for floor in (-1, True, 1.5, None):
            with self.subTest(floor=floor), self.assertRaises(ValueError):
                a.restore_session(OWNER, floor)

    def test_revoked_session_accepts_no_further_transitions_or_emissions(self):
        session = capturing()
        lease = a.issue_reply(session, 0.0, 20.0)
        gone = a.revoked(session)
        self.assertEqual(emit(gone, lease), 'revoked')
        for change in (a.quiet, a.reconnected, a.backgrounded, TRANSITIONS[a.STOP]):
            with self.assertRaises(a.Denied): change(gone)


class DeadlineTests(unittest.TestCase):
    def test_deadline_is_inclusive_and_clock_must_be_valid(self):
        session = capturing()
        lease = cue(session, now=10.0)
        self.assertEqual(emit(session, lease, 10.0 + TTL), a.OK)
        self.assertEqual(emit(session, lease, math.nextafter(10.0 + TTL, math.inf)), 'deadline_exceeded')
        for now in (9.999, math.nan, math.inf):
            self.assertEqual(emit(session, lease, now), 'clock_invalid')

    def test_issue_requires_a_finite_deadline_later_than_now(self):
        for now, ttl in ((math.nan, 1.0), (0.0, 0.0), (0.0, -1.0), (0.0, math.inf),
                         (1e308, 1e308), (1e17, 1.0), (10 ** 400, 1.0), (0.0, 10 ** 400)):
            with self.subTest(now=now, ttl=ttl), self.assertRaises(ValueError):
                a.issue_reply(main(), now, ttl)

    def test_forged_or_overflowing_lease_times_are_denied(self):
        session = main()
        lease = a.issue_reply(session, 0.0, 10.0)
        for changes in (dict(deadline=math.nan), dict(deadline=math.inf), dict(issued_at=-math.inf, deadline=math.inf),
                        dict(issued_at=math.nan)):
            with self.subTest(**{k: str(v) for k, v in changes.items()}):
                self.assertEqual(emit(session, dataclasses.replace(lease, **changes), 1e9), 'clock_invalid')
        self.assertEqual(emit(session, lease, 10 ** 400), 'clock_invalid')

    def test_forged_cue_without_a_revision_after_resume_is_stale(self):
        resumed = a.user_resumed(paused(), OWNER, CAPTURE, 5)
        self.assertEqual(emit(resumed, dataclasses.replace(cue(resumed, revision=6), revision=None)), 'stale_cutoff')


class EligibilityTests(unittest.TestCase):
    def test_followup_needs_the_current_complete_chat_anchor(self):
        session = main()
        lease = followup(session)
        self.assertEqual(emit(session, lease), a.OK)
        self.assertEqual(emit(a.chat_changed(session), lease), 'chat_changed')
        for anchor in (False, None):
            self.assertEqual(emit(session, lease, anchor_complete=anchor), 'chat_changed')

    def test_pending_direct_turn_and_background_block_unsolicited_but_not_replies(self):
        chat, live = main(), capturing()
        for session, lease in ((chat, followup(chat)), (live, cue(live))):
            self.assertEqual(emit(session, lease, pending_direct_turn=True), 'chat_busy')
        reply = a.issue_reply(live, 0.0, 20.0, CAPTURE)
        self.assertEqual(emit(live, reply, pending_direct_turn=True), a.OK)
        not_back = a.restore_session(OWNER, 1, quiet_capture=a.OFF, capture=a.Capture(CAPTURE))
        with self.assertRaises(a.Denied) as denied: cue(not_back)
        self.assertEqual(denied.exception.reason, 'background')

    def test_cues_and_followups_never_cross_modes_even_at_the_current_epoch(self):
        chat, live = main(), capturing()
        with self.assertRaises(a.Denied): cue(chat)
        with self.assertRaises(a.Denied): followup(live)
        forged = (
            (live, dataclasses.replace(cue(live), kind=a.FOLLOWUP, revision=live.chat_revision), 'mode_changed'),
            (live, dataclasses.replace(cue(live), kind=a.FOLLOWUP, mode=a.MAIN_CHAT, binding=None), 'mode_changed'),
            (chat, dataclasses.replace(followup(chat), kind=a.CUE, revision=1), 'no_capture'),
        )
        for session, lease, reason in forged:
            with self.subTest(kind=lease.kind, mode=lease.mode):
                self.assertEqual(lease.epoch, session.epoch)
                self.assertEqual(emit(session, lease), reason)

    def test_cue_after_resume_needs_text_newer_than_the_resume_cutoff(self):
        resumed = a.user_resumed(paused(), OWNER, CAPTURE, 5)
        for revision in (4, 5):
            with self.subTest(revision=revision), self.assertRaises(a.Denied) as denied:
                cue(resumed, revision=revision)
            self.assertEqual(denied.exception.reason, 'stale_cutoff')
        self.assertEqual(emit(resumed, cue(resumed, revision=6)), a.OK)

    def test_unknown_lease_kind_is_denied(self):
        session = main()
        lease = dataclasses.replace(a.issue_reply(session, 0.0, 20.0), kind='tool')
        self.assertEqual(emit(session, lease), 'kind_invalid')


if __name__ == '__main__':
    unittest.main()
