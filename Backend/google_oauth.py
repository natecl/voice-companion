"""Google grant revocation with a fixed endpoint and no automatic retries."""
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, HTTPRedirectHandler, build_opener
from admission import Rejected


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise Rejected('identity_provider_unavailable')


class GoogleOAuth:
    def __init__(self):
        self.opener = build_opener(NoRedirect())

    def revoke(self, token):
        if not isinstance(token, str) or not 1 <= len(token) <= 8192 or any(c.isspace() for c in token):
            raise Rejected('invalid_account_request')
        request = Request('https://oauth2.googleapis.com/revoke', data=urlencode({'token': token}).encode(),
                          headers={'Content-Type': 'application/x-www-form-urlencoded'}, method='POST')
        try:
            with self.opener.open(request, timeout=5) as response:
                if response.status != 200:
                    raise Rejected('identity_provider_unavailable')
        except HTTPError as error:
            try:
                body = json.loads(error.read(32768))
                expired = error.code == 400 and isinstance(body, dict) and body.get('error') == 'invalid_token'
            except (ValueError, OSError):
                expired = False
            finally:
                error.close()
            raise Rejected('google_authorization_revoked' if expired else 'identity_provider_unavailable') from None
        except (URLError, TimeoutError, OSError):
            raise Rejected('identity_provider_unavailable') from None
