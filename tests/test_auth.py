import json
import unittest
from qnap_sdk import QnapClient, QnapError, SessionExpired


class AuthTests(unittest.TestCase):
    def client(self, responses):
        self.requests = []

        def transport(req):
            self.requests.append(req)
            return json.dumps(responses.pop(0)).encode()

        c = QnapClient(
            "https://nas.invalid",
            "fixture",
            {"firmware": "fixture", "operations": {}},
            "INITIAL",
            transport=transport,
        )
        c.close()
        return c

    def test_login_and_check(self):
        c = self.client([{"authPassed": "1", "authSid": "SECRET"}, {"authPassed": "1"}])
        c.login("manager", "hidden")
        self.assertTrue(c.check_session())
        self.assertNotIn("SECRET", repr(c))
        self.assertNotIn("hidden", self.requests[0].full_url)

    def test_failure_does_not_keep_session(self):
        c = self.client([{"authPassed": "0"}])
        with self.assertRaises(SessionExpired):
            c.login("manager", "wrong")
        self.assertEqual(c.sid, "")

    def test_two_step_requires_explicit_input(self):
        c = self.client([{"authPassed": "0", "need_2_step_verification": "1"}])
        with self.assertRaises(QnapError):
            c.login("manager", "hidden")
        self.assertEqual(c.sid, "")

    def test_logout_revocation_is_verified(self):
        c = self.client([{}, {"authPassed": "0"}])
        c.sid = "SECRET"
        c.logout()
        self.assertEqual(c.sid, "")
        self.assertEqual(
            [r.qnap_operation for r in self.requests], ["auth.logout", "auth.check_session"]
        )

    def test_logout_not_confirmed_raises(self):
        c = self.client([{}, {"authPassed": "1"}])
        c.sid = "SECRET"
        with self.assertRaises(QnapError):
            c.logout()
        self.assertEqual(c.sid, "")

    def test_expiry_clears_session(self):
        c = self.client([{"authPassed": "0"}])
        c.sid = "SECRET"
        with self.assertRaises(SessionExpired):
            c.check_session()
        self.assertEqual(c.sid, "")
