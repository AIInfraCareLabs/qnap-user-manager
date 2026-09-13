"""Native transport failures, authentication boundaries and parser limits."""

import io
import json
import unittest
import urllib.error
from unittest.mock import Mock
from qnap_sdk import QnapClient, QnapError, SessionExpired, get_profile
from qnap_sdk.client import decode_response, NoRedirect


class TransportTests(unittest.TestCase):
    def client(self):
        profile = get_profile()
        return QnapClient("https://nas.invalid", profile["firmware"], profile, "synthetic")

    def test_native_read_uses_timeout_and_bounded_size(self):
        client = self.client()
        response = Mock()
        response.read.return_value = b'{"authPassed":"1","userroot":{"ret":"0","count":"0"}}'
        client._opener = Mock()
        client._opener.open.return_value.__enter__ = Mock(return_value=response)
        client._opener.open.return_value.__exit__ = Mock(return_value=False)
        self.assertEqual(client.users.list(), [])
        response.read.assert_called_once_with(8 * 1024 * 1024 + 1)
        self.assertEqual(client._opener.open.call_args.kwargs["timeout"], 15)

    def test_http_unauthorized_clears_session_for_auth_and_resource(self):
        for action in ("check_session", "list_users"):
            for code in (401, 403):
                client = self.client()
                client._opener = Mock()
                client._opener.open.side_effect = urllib.error.HTTPError(
                    "https://nas.invalid", code, "secret", {}, io.BytesIO()
                )
                with self.subTest(action=action, code=code), self.assertRaises(SessionExpired):
                    getattr(client, action)()
                self.assertEqual(client.sid, "")

    def test_connection_and_server_errors_are_sanitized_and_not_retried(self):
        errors = (
            urllib.error.URLError("private detail"),
            TimeoutError("private detail"),
            urllib.error.HTTPError("https://nas.invalid", 500, "private detail", {}, io.BytesIO()),
        )
        for action in ("check_session", "list_users"):
            for error in errors:
                client = self.client()
                client._opener = Mock()
                client._opener.open.side_effect = error
                with (
                    self.subTest(action=action, error=type(error).__name__),
                    self.assertRaises(QnapError) as caught,
                ):
                    getattr(client, action)()
                self.assertNotIn("private detail", str(caught.exception))
                self.assertEqual(client._opener.open.call_count, 1)

    def test_bad_timeouts_and_port(self):
        for options in (
            {"timeout": 0},
            {"timeout": float("nan")},
            {"verification_timeout": -1},
            {"verification_timeout": float("inf")},
            {"test_prefix": None},
        ):
            with self.subTest(options=options), self.assertRaises(QnapError):
                QnapClient(
                    "https://nas.invalid", "fixture", {"firmware": "fixture"}, "sid", **options
                )
        with self.assertRaises(QnapError):
            QnapClient("https://nas.invalid:bad", "fixture", {"firmware": "fixture"}, "sid")

    def test_parser_requires_structured_bounded_safe_response(self):
        for body in (
            b"[]",
            b"null",
            b"1",
            b"<root/>",
            b"<html",
            b"<!DOCTYPE a><a/>",
            b"x" * (8 * 1024 * 1024 + 1),
        ):
            with self.subTest(length=len(body)), self.assertRaises(QnapError):
                decode_response(body)

    def test_redirects_refused(self):
        with self.assertRaises(QnapError):
            NoRedirect().redirect_request(None, None, 302, "", {}, "https://elsewhere.invalid")

    def test_auth_input_and_empty_lifecycle(self):
        client = self.client()
        with self.assertRaises(QnapError):
            client.login("test", "password")
        client.close()
        for username, password in (("", "password"), ("test", ""), (None, "password")):
            with self.assertRaises(QnapError):
                client.login(username, password)
        with self.assertRaises(SessionExpired):
            client.check_session()
        client.logout()

    def test_auth_security_code_and_invalid_sid(self):
        client = self.client()
        client.close()
        captured = []

        def transport(request):
            captured.append(request)
            return json.dumps({"authPassed": "1", "authSid": ""}).encode()

        client.transport = transport
        with self.assertRaises(QnapError):
            client.login("test", "password", security_code="123456")
        self.assertIn(b"security_code=123456", captured[0].data)
        self.assertEqual(client.sid, "")
