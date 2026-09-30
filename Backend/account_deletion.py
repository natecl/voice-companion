"""Durable, explicitly retried account deletion; no background provider retries."""
import asyncio
import hashlib
import json
import secrets

from admission import Rejected
from account_erasure import erase_content

SCHEMA = '''
CREATE TABLE IF NOT EXISTS account_deletion(
 owner TEXT PRIMARY KEY, request_digest TEXT UNIQUE NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('pending','complete')));
CREATE TABLE IF NOT EXISTS deletion_recovery(
 owner TEXT PRIMARY KEY REFERENCES account_deletion(owner), digest TEXT UNIQUE NOT NULL);
CREATE TABLE IF NOT EXISTS deleting_identity(
 digest TEXT PRIMARY KEY, owner TEXT NOT NULL REFERENCES account_deletion(owner));
'''


def identity_digest(issuer, subject):
    return hashlib.sha256(json.dumps([issuer, subject], separators=(',', ':')).encode()).hexdigest()


class AccountDeletion:
    def __init__(self, sessions, grants, apple):
        self.sessions, self.grants, self.apple = sessions, grants, apple
        self.db = sessions.db
        self.quiesce = None  # Relay attaches its owner-scoped socket/task shutdown.

    def pending_owner(self, identity):
        row = self.db.execute("SELECT d.owner FROM deleting_identity i JOIN account_deletion d ON d.owner=i.owner "
                              "WHERE i.digest=? AND d.state='pending'",
                              (identity_digest(identity.issuer, identity.subject),)).fetchone()
        if row is None:
            raise Rejected('no_account_deletion_pending')
        return row[0]

    def recover(self, challenge, provider, identity, identity_token, grant=None):
        """Fresh verified proof can recover only an already accepted deletion.

        One recovery receipt per owner bounds storage. New recovery invalidates
        the previous recovery receipt; the original accepted request still works.
        No access/refresh session is issued and no content is returned.
        """
        if self.quiesce is None:
            raise Rejected('account_deletion_unavailable')
        token = secrets.token_urlsafe(48)
        with self.sessions.admission.transaction():
            owner = self.pending_owner(identity)
            self.sessions.consume_identity(challenge, provider, identity, identity_token)
            if provider == 'apple':
                if grant is None:
                    raise Rejected('invalid_account_request')
                self.grants.save_apple(owner, identity.audience, grant['refresh_token'])
            self.db.execute('INSERT INTO deletion_recovery VALUES(?,?) ON CONFLICT(owner) '
                            'DO UPDATE SET digest=excluded.digest',
                            (owner, self.sessions.admission.digest(token)))
        return dict(status='pending', owner=owner, deletion_token=token)

    def recovery_receipt(self, token):
        digest = self.sessions.admission.digest(token)
        row = self.db.execute('SELECT d.owner,d.state FROM deletion_recovery r '
                              'JOIN account_deletion d ON d.owner=r.owner WHERE r.digest=?', (digest,)).fetchone()
        if row is None:
            raise Rejected('unauthorized')
        return row

    def begin(self, refresh_token):
        digest = self.sessions.admission.digest(refresh_token)
        old = self.db.execute('SELECT owner,state FROM account_deletion WHERE request_digest=?', (digest,)).fetchone()
        if old:
            return old
        owner = self.sessions.refresh_owner(refresh_token)
        with self.sessions.memory.connect() as db:
            identities = db.execute('SELECT issuer,subject FROM account_identity WHERE owner=?', (owner,)).fetchall()
        if not identities:
            raise Rejected('account_not_enrolled')
        with self.sessions.admission.transaction():
            if self.db.execute('SELECT 1 FROM account_deletion WHERE owner=?', (owner,)).fetchone():
                raise Rejected('account_deletion_pending')
            self.db.execute("INSERT INTO account_deletion VALUES(?,?,'pending')", (owner, digest))
            self.db.executemany('INSERT INTO deleting_identity VALUES(?,?)',
                                [(identity_digest(*row), owner) for row in identities])
            self.grants.revoke_local_owner(owner)
        return owner, 'pending'

    async def delete(self, token, *, recovery=False):
        if self.quiesce is None:
            raise Rejected('account_deletion_unavailable')
        owner, state = self.recovery_receipt(token) if recovery else self.begin(token)
        if state == 'complete':
            return {'status': 'deleted'}
        # Revocation is durable before any await. New content handshakes fail;
        # existing owner sockets/tasks must settle before storage is removed.
        await self.quiesce(owner)
        for client, refresh in self.grants.apple_for(owner):
            await asyncio.to_thread(self.apple.revoke, client, refresh)
            self.db.execute('DELETE FROM apple_grant WHERE owner=? AND client=?', (owner, client))
        await asyncio.to_thread(erase_content, self.sessions.memory, owner)
        with self.sessions.admission.transaction():
            self.db.execute("UPDATE account_deletion SET state='complete' WHERE owner=?", (owner,))
            self.db.execute('DELETE FROM deleting_identity WHERE owner=?', (owner,))
        return {'status': 'deleted'}
