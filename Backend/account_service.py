"""One bounded native account operation per socket; credentials never enter URLs."""
import asyncio
import json
import time

from admission import Rejected


class AccountService:
    def __init__(self, sessions, verifier, *, clock=time.monotonic):
        self.sessions, self.verifier = sessions, verifier
        self.clock = clock
        self.window = clock()
        self.attempts = 0
        self.slots = asyncio.Semaphore(2)

    def admit(self, request):
        # This is a native endpoint, not a cookie-authenticated browser API.
        if request.headers.get_all('Origin'):
            return False
        now = self.clock()
        if now - self.window >= 60:
            self.window, self.attempts = now, 0
        if self.attempts >= 60:
            return False
        self.attempts += 1
        return True

    async def handle(self, socket):
        try:
            async with asyncio.timeout(12):
                async with self.slots:
                    raw = await socket.recv()
                    if not isinstance(raw, str) or len(raw.encode()) > 20000:
                        raise Rejected('invalid_account_request')
                    try:
                        data = json.loads(raw)
                    except ValueError:
                        raise Rejected('invalid_account_request') from None
                    if not isinstance(data, dict) or type(data.get('version')) is not int or data['version'] != 1:
                        raise Rejected('invalid_account_request')
                    op = data.get('operation')
                    fields = set(data) - {'version', 'operation'}
                    if op == 'challenge' and fields == {'provider'}:
                        result = self.sessions.challenge(data['provider'])
                    elif op == 'exchange' and fields == {'provider', 'challenge', 'identity_token'}:
                        provider = data['provider']
                        if not isinstance(provider, str) or provider not in ('google', 'apple'):
                            raise Rejected('invalid_account_request')
                        nonce = self.sessions.nonce(data['challenge'], provider)
                        identity = await asyncio.to_thread(self.verifier.verify, provider,
                                                          data['identity_token'], apple_nonce=nonce)
                        result = self.sessions.exchange(data['challenge'], provider, identity, data['identity_token'])
                    elif op == 'refresh' and fields == {'refresh_token'}:
                        result = self.sessions.refresh(data['refresh_token'])
                    elif op == 'sign_out' and fields == {'refresh_token'}:
                        self.sessions.sign_out(data['refresh_token'])
                        result = {}
                    else:
                        raise Rejected('invalid_account_request')
                    await socket.send(json.dumps(dict(type='account_result', version=1, operation=op, **result)))
        except Exception as error:
            reason = str(error) if isinstance(error, Rejected) else 'account_unavailable'
            try:
                await socket.send(json.dumps(dict(type='error', message=reason)))
            except Exception:
                pass  # A lost rotation response requires fresh provider sign-in.
        finally:
            await socket.close()


def configured_accounts(env, admission, memory):
    """Disabled by default; incomplete enabled configuration aborts startup."""
    enabled = env.get('VOICE_ENABLE_ACCOUNTS', '0')
    if enabled not in ('0', '1'):
        raise ValueError('Invalid accounts feature flag')
    if enabled == '0':
        return None
    if memory is None:
        raise ValueError('Accounts require memory storage')
    from account_tokens import AccountTokenVerifier
    from account_sessions import AccountSessions
    def values(name):
        return [v.strip() for v in env.get(name, '').split(',') if v.strip()]
    verifier = AccountTokenVerifier(google_audience=env.get('VOICE_GOOGLE_SERVER_CLIENT_ID', ''),
                                    google_presenters=values('VOICE_GOOGLE_NATIVE_CLIENT_IDS'),
                                    apple_audiences=values('VOICE_APPLE_CLIENT_IDS'))
    return AccountService(AccountSessions(admission, memory), verifier)
