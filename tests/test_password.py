import copy
import json
import unittest
from urllib.parse import parse_qs
from qnap_sdk import QnapClient, QnapError

from qnap_sdk import get_profile

PROFILE = get_profile()
U = "sdk_test_0913_u"


class PasswordTests(unittest.TestCase):
    def client(self, check="0", change="0"):
        self.requests = []

        def transport(r):
            self.requests.append(r)
            if r.qnap_operation == "users.list":
                return json.dumps(
                    {
                        "authPassed": "1",
                        "userroot": {
                            "ret": "0",
                            "count": "1",
                            "data": {
                                "user": {
                                    "username": U,
                                    "userid": "1002",
                                    "description": "",
                                    "user_enable": "0",
                                }
                            },
                        },
                    }
                ).encode()
            if r.qnap_operation == "users.get":
                return json.dumps(
                    {
                        "authPassed": "1",
                        "userInfo": {
                            "username": U,
                            "uid": "1002",
                            "description": "",
                            "chk_disable": "1",
                        },
                    }
                ).encode()
            if r.qnap_operation == "users.groups":
                return json.dumps(
                    {"authPassed": "1", "func": {"ownContent": {"ownGroup": "everyone"}}}
                ).encode()
            return json.dumps(
                {
                    "authPassed": "1",
                    "func": {
                        "userPasswordEdit": {"passwordCheck": check, "passwordChange": change}
                    },
                }
            ).encode()

        return QnapClient(
            "https://nas.invalid",
            PROFILE["firmware"],
            copy.deepcopy(PROFILE),
            "SECRET",
            transport=transport,
            allow_test_writes=True,
            test_prefix="sdk_test_0913_",
        )

    def test_reset_encoding_and_no_enable_fields(self):
        import base64

        c = self.client()
        password = "Valid-Password-123!"
        c.users.reset_password(U, password)
        writes = [r for r in self.requests if r.qnap_operation == "users.set_password"]
        self.assertEqual(len(writes), 1)
        form = parse_qs(writes[0].data.decode(), keep_blank_values=True)
        self.assertEqual(base64.b64decode(form["password"][0]).decode(), password)
        self.assertEqual(form["need_check"], ["no"])
        self.assertEqual(form["old_password"], [""])
        self.assertNotIn("a_enable", form)
        self.assertNotIn("a_expire", form)

    def test_old_password_check_failure_is_not_success(self):
        c = self.client(check="1")
        with self.assertRaises(QnapError):
            c.users.reset_password(U, "Valid-Password-123!")
        self.assertEqual(sum(r.qnap_operation == "users.set_password" for r in self.requests), 1)

    def test_change_failure_is_not_success(self):
        c = self.client(change="1")
        with self.assertRaises(QnapError):
            c.users.reset_password(U, "Valid-Password-123!")

    def test_invalid_password_rejected_before_network(self):
        for password in ("", "x" * 65, None):
            c = self.client()
            with self.assertRaises(QnapError):
                c.users.reset_password(U, password)
            self.assertEqual(self.requests, [])
