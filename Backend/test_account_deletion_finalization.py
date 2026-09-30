"""Google identity reservation remains until server-observed grant revocation."""
import asyncio
import threading
import unittest
from unittest.mock import AsyncMock
from admission import Rejected
from account_deletion import AccountDeletion
from account_sessions import AccountSessions
from memory_store import MemoryStore
import test_account_deletion as fixtures
import test_account_deletion_recovery as recovery_fixtures


class FinalizationTests(unittest.IsolatedAsyncioTestCase):
    setUp = fixtures.AccountDeletionTests.setUp
    enroll = fixtures.AccountDeletionTests.enroll
    proof = recovery_fixtures.DeletionRecoveryTests.proof

    async def test_erased_identity_stays_reserved_across_restart_and_provider_failure(self):
        account = self.enroll()
        other = self.enroll('other')
        result = await self.deletion.delete(account['refresh_token'])
        self.assertEqual(result['status'], 'awaiting_google_revocation')
        with self.assertRaisesRegex(Rejected, 'account_deletion_pending'): self.enroll()
        self.sessions = AccountSessions(self.admission, MemoryStore(self.memory.path))
        self.deletion = AccountDeletion(self.sessions, self.grants, self.apple, self.google)
        self.deletion.quiesce = AsyncMock()
        self.google.revoke.side_effect = Rejected('google_authorization_revoked')
        with self.assertRaises(Rejected):
            await self.deletion.finish_google(account['refresh_token'], 'expired-grant')
        with self.assertRaisesRegex(Rejected, 'account_deletion_pending'): self.enroll()
        with self.assertRaises(Rejected):
            await self.deletion.finish_google(other['refresh_token'], 'other-grant')
        self.admission.authorized(other['token'])
        # Fresh provider proof resolves the retained hash even after identity rows
        # and all account content have been erased. It cannot change the owner.
        recovered = self.deletion.recover(*self.proof(), expected_owner=account['owner'])
        self.assertEqual(recovered['owner'], account['owner'])
        self.google.revoke.side_effect = None
        self.assertEqual(await self.deletion.finish_google(recovered['deletion_token'], 'fresh-grant', recovery=True), {'status':'deleted'})
        count = self.google.revoke.call_count
        self.assertEqual(await self.deletion.finish_google(account['refresh_token'], 'lost-response-retry'), {'status':'deleted'})
        self.assertEqual(self.google.revoke.call_count, count)
        fresh = self.enroll()
        self.assertNotEqual(fresh['owner'], account['owner'])
        await self.deletion.finish_google(recovered['deletion_token'], 'stale', recovery=True)
        self.admission.authorized(fresh['token'])
        self.assertEqual(self.google.revoke.call_count, count)

    async def test_cannot_finalize_before_erasure_or_finalize_apple(self):
        for provider in ('google', 'apple'):
            account = self.enroll(provider=provider)
            self.deletion.begin(account['refresh_token'])
            with self.assertRaisesRegex(Rejected, 'invalid_account_request'):
                await self.deletion.finish_google(account['refresh_token'], 'fictional-grant')
        self.google.revoke.assert_not_called()

    async def test_cancellation_waits_for_bounded_provider_result_before_releasing_identity(self):
        account = self.enroll()
        await self.deletion.delete(account['refresh_token'])
        arrived, release = threading.Event(), threading.Event()
        def revoke(_):
            arrived.set()
            if not release.wait(3): raise TimeoutError()
        self.google.revoke.side_effect = revoke
        task = asyncio.create_task(self.deletion.finish_google(account['refresh_token'], 'fictional-grant'))
        self.assertTrue(await asyncio.to_thread(arrived.wait, 2))
        task.cancel()
        await asyncio.sleep(0)
        self.assertFalse(task.done())
        with self.assertRaisesRegex(Rejected, 'account_deletion_pending'): self.enroll()
        release.set()
        with self.assertRaises(asyncio.CancelledError): await task
        self.assertNotEqual(self.enroll()['owner'], account['owner'])
        await self.deletion.finish_google(account['refresh_token'], 'retry')
        self.google.revoke.assert_called_once()


if __name__ == '__main__': unittest.main()
