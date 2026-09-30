"""Encrypted provider refresh grants; encryption key stays outside the database."""
from cryptography.fernet import Fernet, InvalidToken
from admission import Rejected


class ProviderGrants:
    def __init__(self, admission, encryption_key):
        self.admission, self.db = admission, admission.db
        self.cipher = Fernet(encryption_key)
        self.db.execute('CREATE TABLE IF NOT EXISTS apple_grant '
                        '(owner TEXT NOT NULL, client TEXT NOT NULL, ciphertext BLOB NOT NULL, '
                        'PRIMARY KEY(owner,client))')

    def save_apple(self, owner, client, refresh_token):
        encrypted = self.cipher.encrypt(refresh_token.encode())
        self.db.execute('INSERT INTO apple_grant VALUES(?,?,?) ON CONFLICT(owner,client) '
                        'DO UPDATE SET ciphertext=excluded.ciphertext', (owner, client, encrypted))

    def apple_for(self, owner):
        result = []
        for client, encrypted in self.db.execute('SELECT client,ciphertext FROM apple_grant WHERE owner=?', (owner,)):
            try:
                result.append((client, self.cipher.decrypt(encrypted).decode()))
            except (InvalidToken, UnicodeError):
                raise Rejected('identity_provider_unavailable') from None
        return result

    def revoke_local_owner(self, owner):
        self.db.execute('UPDATE credential SET revoked=1 WHERE id IN '
                        '(SELECT credential FROM account_session WHERE owner=?)', (owner,))
