import io
import unittest
from unittest.mock import Mock
from urllib.error import HTTPError, URLError
from google_oauth import GoogleOAuth, NoRedirect
from admission import Rejected


class GoogleOAuthTests(unittest.TestCase):
    def setUp(self):
        self.oauth = GoogleOAuth()
        self.oauth.opener = Mock()

    def test_fixed_post_encoded_body_and_deadline(self):
        self.oauth.opener.open.return_value.__enter__ = Mock(return_value=Mock(status=200))
        self.oauth.opener.open.return_value.__exit__ = Mock(return_value=False)
        self.oauth.revoke('fixture+/=&token=other')
        args, kwargs = self.oauth.opener.open.call_args
        request = args[0]
        self.assertEqual(request.full_url, 'https://oauth2.googleapis.com/revoke')
        self.assertEqual(request.method, 'POST')
        self.assertEqual(request.data, b'token=fixture%2B%2F%3D%26token%3Dother')
        self.assertEqual(kwargs, {'timeout': 5})

    def test_invalid_token_requires_proof_but_other_errors_remain_retryable(self):
        for code, body, expected in [(400, b'{"error":"invalid_token"}', 'google_authorization_revoked'),
                                     (400, b'{"error":"other"}', 'identity_provider_unavailable'),
                                     (500, b'private-provider-diagnostics', 'identity_provider_unavailable')]:
            self.oauth.opener.open.side_effect = HTTPError('https://oauth2.googleapis.com/revoke', code, 'fixture', {}, io.BytesIO(body))
            with self.assertRaisesRegex(Rejected, '^'+expected+'$'): self.oauth.revoke('fictional-token')
        self.assertEqual(self.oauth.opener.open.call_count, 3)

    def test_no_redirects_or_invalid_requests_or_automatic_retries(self):
        for token in (None, '', 'bad token', 'x'*8193):
            with self.assertRaisesRegex(Rejected, '^invalid_account_request$'): self.oauth.revoke(token)
        self.oauth.opener.open.assert_not_called()
        self.oauth.opener.open.side_effect = URLError('private')
        with self.assertRaisesRegex(Rejected, '^identity_provider_unavailable$'): self.oauth.revoke('fictional-token')
        self.assertEqual(self.oauth.opener.open.call_count, 1)
        with self.assertRaises(Rejected): NoRedirect().redirect_request(None, None, 302, None, {}, 'https://elsewhere.test')


if __name__ == '__main__': unittest.main()
