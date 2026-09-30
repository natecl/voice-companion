"""Durable enrollment replay protection and rotating app sessions.

Uses Admission's connection on its owning thread. Identity verification runs
before exchange(); no unverified provider subject crosses this boundary.
"""
import hashlib
import secrets
import uuid

from admission import Rejected
from account_tokens import VerifiedIdentity, GOOGLE, APPLE

ACCESS_SECONDS = 3600
REFRESH_SECONDS = 30 * 86400
CHALLENGE_SECONDS = 300


class AccountSessions:
    def __init__(self, admission, memory):
        self.admission, self.memory = admission, memory
        self.db = admission.db
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS account_challenge (
                digest TEXT PRIMARY KEY, provider TEXT NOT NULL, expires REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS account_exchange (
                digest TEXT PRIMARY KEY, expires REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS account_session (
                credential TEXT PRIMARY KEY REFERENCES credential(id),
                family TEXT NOT NULL, owner TEXT NOT NULL,
                refresh_digest TEXT UNIQUE NOT NULL, refresh_expires REAL NOT NULL,
                consumed INTEGER NOT NULL DEFAULT 0);
            CREATE INDEX IF NOT EXISTS account_session_family ON account_session(family);
        ''')

    def challenge(self, provider):
        if provider not in ('google', 'apple'):
            raise Rejected('invalid_account_request')
        token = secrets.token_urlsafe(32)
        now = self.admission.clock()
        with self.admission.transaction():
            self.db.execute('DELETE FROM account_challenge WHERE expires<=?', (now,))
            self.db.execute('DELETE FROM account_exchange WHERE expires<=?', (now,))
            if self.db.execute('SELECT count(*) FROM account_challenge').fetchone()[0] >= 1000:
                raise Rejected('account_busy')
            self.db.execute('INSERT INTO account_challenge VALUES(?,?,?)',
                            (self.admission.digest(token), provider, now + CHALLENGE_SECONDS))
        return dict(challenge=token, nonce=self.admission.digest(token), expires=now+CHALLENGE_SECONDS)

    def nonce(self, challenge, provider):
        digest = self.admission.digest(challenge)
        row = self.db.execute('SELECT provider,expires FROM account_challenge WHERE digest=?', (digest,)).fetchone()
        if row is None or row[0] != provider or row[1] <= self.admission.clock():
            raise Rejected('invalid_account_challenge')
        return digest

    def exchange(self, challenge, provider, identity, identity_token):
        if not isinstance(identity, VerifiedIdentity) or identity.issuer != {'google': GOOGLE, 'apple': APPLE}.get(provider):
            raise Rejected('invalid_identity_token')
        if not isinstance(identity_token, str) or not 1 <= len(identity_token) <= 16384:
            raise Rejected('invalid_identity_token')
        fingerprint = hashlib.sha256(identity_token.encode()).hexdigest()
        with self.admission.transaction():
            digest = self.nonce(challenge, provider)
            if identity.expires <= self.admission.clock():
                raise Rejected('invalid_identity_token')
            if self.db.execute('SELECT 1 FROM account_exchange WHERE digest=?', (fingerprint,)).fetchone():
                raise Rejected('identity_token_replayed')
            self.db.execute('DELETE FROM account_challenge WHERE digest=?', (digest,))
            self.db.execute('INSERT INTO account_exchange VALUES(?,?)', (fingerprint, identity.expires))
            credential, token = self.admission.enroll(lifetime_seconds=ACCESS_SECONDS)
            # A memory failure rolls back issuance. A crash after this independent
            # DB commit can leave an unreachable credential mapping, never access.
            owner = self.memory.owner_for_identity(credential, issuer=identity.issuer, subject=identity.subject)
            return self._session(credential, token, owner, str(uuid.uuid4()),
                                 self.admission.clock() + REFRESH_SECONDS)

    def _session(self, credential, token, owner, family, refresh_expires):
        refresh = secrets.token_urlsafe(48)
        self.db.execute('INSERT INTO account_session VALUES(?,?,?,?,?,0)',
                        (credential, family, owner, self.admission.digest(refresh), refresh_expires))
        return dict(token=token, refresh_token=refresh, owner=owner,
                    expires=self.admission.clock()+ACCESS_SECONDS, refresh_expires=refresh_expires)

    def _revoke_family(self, family):
        self.db.execute('UPDATE credential SET revoked=1 WHERE id IN '
                        '(SELECT credential FROM account_session WHERE family=?)', (family,))

    def refresh_owner(self, token):
        row = self.db.execute('SELECT s.owner,s.refresh_expires,s.consumed,c.revoked '
                              'FROM account_session s JOIN credential c ON c.id=s.credential '
                              'WHERE s.refresh_digest=?', (self.admission.digest(token),)).fetchone()
        if row is None or row[1] <= self.admission.clock():
            raise Rejected('unauthorized')
        if row[2]:
            # Preserve the committed replay-revocation behavior before any API call.
            self.refresh(token)
        if row[3]:
            raise Rejected("unauthorized")
        return row[0]

    def refresh(self, token):
        digest = self.admission.digest(token)
        replayed = False
        with self.admission.transaction():
            row = self.db.execute('SELECT s.credential,s.family,s.owner,s.refresh_expires,s.consumed,c.revoked '
                                  'FROM account_session s JOIN credential c ON c.id=s.credential '
                                  'WHERE s.refresh_digest=?', (digest,)).fetchone()
            if row is None or row[3] <= self.admission.clock():
                raise Rejected('unauthorized')
            credential, family, owner, expiry, consumed, revoked = row
            if consumed:
                # Commit family revocation before reporting a replay failure.
                self._revoke_family(family)
                replayed = True
            elif revoked:
                raise Rejected('unauthorized')
            else:
                self.db.execute('UPDATE account_session SET consumed=1 WHERE credential=?', (credential,))
                self.admission.revoke(credential)
                fresh, access = self.admission.enroll(lifetime_seconds=ACCESS_SECONDS)
                self.memory.owner_for(fresh, existing_owner=owner)
                result = self._session(fresh, access, owner, family, expiry)
        if replayed:
            raise Rejected('refresh_replayed')
        return result

    def sign_out(self, refresh_token):
        digest = self.admission.digest(refresh_token)
        with self.admission.transaction():
            row = self.db.execute('SELECT family FROM account_session WHERE refresh_digest=?', (digest,)).fetchone()
            if row:
                self._revoke_family(row[0])
        # Idempotent and no account-existence disclosure.
