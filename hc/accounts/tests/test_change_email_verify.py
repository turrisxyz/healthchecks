from unittest.mock import patch

from django.contrib.auth.hashers import make_password
from django.core.signing import TimestampSigner
from hc.test import BaseTestCase


class ChangeEmailVerifyTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.profile.token = make_password("secret-token", "login")
        self.profile.save()

        self.checks_url = "/projects/%s/checks/" % self.project.code

    def _url(self, expired=False):
        payload = {
            "u": self.alice.username,
            "t": "secret-token",
            "e": "alice+new@example.org",
        }

        if expired:
            with patch("django.core.signing.TimestampSigner.timestamp") as mock_ts:
                mock_ts.return_value = "1kHR5c"
                signed = TimestampSigner().sign_object(payload)
        else:
            signed = TimestampSigner().sign_object(payload)

        return f"/accounts/change_email/{signed}/"

    def test_it_works(self):
        r = self.client.post(self._url())
        self.assertRedirects(r, self.checks_url)

        # Alice's email should have been updated, and password cleared
        self.alice.refresh_from_db()
        self.assertEqual(self.alice.email, "alice+new@example.org")
        self.assertFalse(self.alice.has_usable_password())

        # After login, token should be blank
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.token, "")

    def test_it_handles_get(self):
        r = self.client.get(self._url())
        self.assertContains(r, "You are about to log into")

        # Alice's email should have *not* been changed yet
        self.alice.refresh_from_db()
        self.assertEqual(self.alice.email, "alice@example.org")

    def test_it_handles_get_with_cookie(self):
        self.client.cookies["auto-login"] = "1"
        r = self.client.get(self._url())
        self.assertRedirects(r, self.checks_url)

    def test_it_handles_expired_link(self):
        r = self.client.post(self._url(expired=True))
        self.assertContains(r, "The link you just used is incorrect.")

    def test_it_handles_bad_payload(self):
        r = self.client.post("/accounts/change_email/bad-payload/")
        self.assertContains(r, "The link you just used is incorrect.")
