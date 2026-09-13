import json
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs
from qnap_sdk import QnapClient, QnapError, UnverifiedOperation, SessionExpired
from qnap_sdk.client import decode_response
from qnap_sdk.discovery import discover_har


def profile(read_only=True):
    return {
        "firmware": "fixture-1",
        "operations": {
            "users.list": {
                "path": "/cgi-bin/fixture.cgi",
                "method": "POST",
                "verified": True,
                "evidence": "UNIT TEST FIXTURE ONLY",
                "read_only": read_only,
                "parameters": ["user"],
                "target_parameter": "user",
                "success": {"field": "status", "values": [0]},
                "session_expired": {"field": "status", "values": [401]},
            }
        },
    }


class SDKTests(unittest.TestCase):
    def client(self, spec=None, body=b'{"status":0}', **options):
        self.requests = []

        def transport(request):
            self.requests.append(request)
            return body

        return QnapClient(
            "https://nas.example",
            "fixture-1",
            spec or profile(),
            "SECRET",
            transport=transport,
            **options,
        )

    def test_request_and_no_session_in_repr(self):
        client = self.client()
        self.assertEqual(client.list_users(), {"status": 0})
        self.assertEqual(parse_qs(self.requests[0].data.decode())["sid"], ["SECRET"])
        self.assertNotIn("SECRET", repr(client))

    def test_unverified_never_requests(self):
        spec = profile()
        spec["operations"]["users.list"]["verified"] = False
        with self.assertRaises(UnverifiedOperation):
            self.client(spec).list_users()
        self.assertEqual(self.requests, [])

    def test_wrong_firmware(self):
        with self.assertRaises(UnverifiedOperation):
            QnapClient("https://nas.example", "other", profile(), "SECRET")

    def test_write_guard(self):
        client = self.client(profile(False))
        with self.assertRaises(QnapError):
            client.call("users.list", target="sdk_test_user")
        self.assertEqual(self.requests, [])
        client = self.client(profile(False), allow_test_writes=True)
        with self.assertRaises(QnapError):
            client.call("users.list", target="admin")
        with self.assertRaises(QnapError):
            client.call("users.list", target="sdk_test_user", user="admin")
        self.assertEqual(self.requests, [])
        client.call("users.list", target="sdk_test_user")
        self.assertEqual(parse_qs(self.requests[0].data.decode())["user"], ["sdk_test_user"])

    def test_reserved_parameter(self):
        with self.assertRaises(QnapError):
            self.client().list_users(sid="evil")
        self.assertEqual(self.requests, [])

    def test_expiry_clears_session(self):
        client = self.client(body=b'{"status":401}')
        with self.assertRaises(SessionExpired):
            client.list_users()
        self.assertEqual(client.sid, "")

    def test_failure_is_not_success(self):
        with self.assertRaises(QnapError):
            self.client(body=b'{"status":3}').list_users()
        with self.assertRaises(QnapError):
            self.client(body=b"<html>Login</html>").list_users()

    def test_xml_repeated_and_entity_rejected(self):
        self.assertEqual(decode_response(b"<r><u>a</u><u>b</u></r>"), {"u": ["a", "b"]})
        with self.assertRaises(QnapError):
            decode_response(b"<!DOCTYPE r><r/>")

    def test_https_only(self):
        with self.assertRaises(QnapError):
            QnapClient("http://nas.example", "fixture-1", profile(), "SECRET")

    def test_missing_success_contract_never_requests(self):
        spec = profile()
        del spec["operations"]["users.list"]["success"]
        with self.assertRaises(UnverifiedOperation):
            self.client(spec).list_users()
        self.assertEqual(self.requests, [])

    def test_encoded_path_rejected(self):
        spec = profile()
        spec["operations"]["users.list"]["path"] = "/cgi-bin/%2e%2e/evil.cgi"
        with self.assertRaises(QnapError):
            self.client(spec).list_users()
        self.assertEqual(self.requests, [])

    def test_offline_har_supports_authorized_http_origin(self):
        content = {
            "log": {
                "entries": [
                    {
                        "request": {
                            "url": "http://nas.example.internal:5000/cgi-bin/fixture.cgi?sid=SECRET",
                            "method": "GET",
                        }
                    }
                ]
            }
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "capture.har"
            path.write_text(json.dumps(content))
            data = discover_har(path, "http://nas.example.internal:5000")
        self.assertEqual(len(data), 1)
        self.assertNotIn("SECRET", json.dumps(data))
        self.assertFalse(data[0]["verified"])

    def test_har_drops_secrets_and_other_hosts(self):
        content = {
            "log": {
                "entries": [
                    {
                        "request": {
                            "url": "https://nas.example/cgi-bin/test.cgi?sid=SECRET",
                            "method": "POST",
                            "postData": {
                                "mimeType": "application/x-www-form-urlencoded",
                                "text": "pwd=PASSWORD",
                            },
                        }
                    },
                    {"request": {"url": "https://other.example/cgi-bin/evil.cgi", "method": "GET"}},
                ]
            }
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "capture.har"
            path.write_text(json.dumps(content))
            data = discover_har(path, "https://nas.example")
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["parameters"], ["pwd", "sid"])
        self.assertNotIn("SECRET", json.dumps(data))
        self.assertNotIn("PASSWORD", json.dumps(data))
        self.assertFalse(data[0]["verified"])


if __name__ == "__main__":
    unittest.main()
