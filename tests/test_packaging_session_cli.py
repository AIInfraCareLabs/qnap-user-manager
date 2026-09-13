"""Installed API contracts, private session storage and CLI lifecycle tests."""

import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from qnap_sdk import (
    DEFAULT_FIRMWARE,
    QnapError,
    UnverifiedOperation,
    available_profiles,
    get_profile,
)
from qnap_sdk.cli import main
from qnap_sdk.session import load_session, save_session


class ProfileTests(unittest.TestCase):
    def test_bundled_profile_matches_discovery_mirror(self):
        mirror = Path(__file__).resolve().parent.parent / "discovery/endpoints.json"
        if mirror.exists():
            self.assertEqual(get_profile(), json.loads(mirror.read_text()))
        self.assertIn(DEFAULT_FIRMWARE, available_profiles())
        self.assertEqual(get_profile()["firmware"], DEFAULT_FIRMWARE)

    def test_loading_returns_independent_copy(self):
        first = get_profile()
        first["operations"].clear()
        self.assertTrue(get_profile()["operations"])

    def test_unknown_firmware_refused(self):
        with self.assertRaises(UnverifiedOperation):
            get_profile("QTS unknown")


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "private/session.txt"

    def test_atomic_save_load_and_replace(self):
        save_session(self.path, "synthetic-session")
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(load_session(self.path), "synthetic-session")
        save_session(self.path, "replacement")
        self.assertEqual(load_session(self.path), "replacement")
        self.assertEqual(list(self.path.parent.glob(".qnap-session-*")), [])

    def test_invalid_identifiers_rejected(self):
        for sid in ("", "\n", "a\rb", "a" * 4097, None):
            with self.subTest(sid_type=type(sid).__name__), self.assertRaises(QnapError):
                save_session(self.path, sid)

    def test_public_file_refused(self):
        save_session(self.path, "synthetic-session")
        os.chmod(self.path, 0o644)
        with self.assertRaises(QnapError):
            load_session(self.path)

    def test_symlink_refused(self):
        save_session(self.path, "synthetic-session")
        alias = self.path.parent / "alias"
        alias.symlink_to(self.path)
        with self.assertRaises(QnapError):
            load_session(alias)

    def test_corrupt_file_refused(self):
        for content in ("", "a\nb", "a" * 4097):
            save_session(self.path, "placeholder")
            self.path.write_text(content)
            with self.subTest(length=len(content)), self.assertRaises(QnapError):
                load_session(self.path)

    def test_replace_failure_leaves_original_and_cleans_temporary(self):
        save_session(self.path, "original")
        with patch("qnap_sdk.session.os.replace", side_effect=OSError("synthetic")):
            with self.assertRaises(OSError):
                save_session(self.path, "replacement")
        self.assertEqual(load_session(self.path), "original")
        self.assertEqual(list(self.path.parent.glob(".qnap-session-*")), [])


class CLITests(unittest.TestCase):
    def run_cli(self, *arguments):
        out, err = io.StringIO(), io.StringIO()
        with (
            patch("sys.argv", ["qnap-manager", *arguments]),
            contextlib.redirect_stdout(out),
            contextlib.redirect_stderr(err),
        ):
            result = main()
        return result, out.getvalue(), err.getvalue()

    def test_profiles_and_contracts_work_without_files_or_network(self):
        for command in ("profiles", "contracts"):
            result, out, err = self.run_cli(command)
            self.assertEqual(result, 0)
            self.assertIsInstance(json.loads(out), dict)
            self.assertEqual(err, "")

    def test_version(self):
        with self.assertRaises(SystemExit) as exit_info:
            self.run_cli("--version")
        self.assertEqual(exit_info.exception.code, 0)

    def test_login_saves_private_session_and_hides_secrets(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "session"
            client = Mock(sid="synthetic-sid")
            with (
                patch("qnap_sdk.cli.getpass.getpass", return_value="synthetic-password"),
                patch("qnap_sdk.cli.QnapClient.authenticate", return_value=client) as auth,
            ):
                result, out, _ = self.run_cli(
                    "login",
                    "--origin",
                    "https://nas.invalid",
                    "--username",
                    "test",
                    "--session-file",
                    str(path),
                )
            self.assertEqual(result, 0)
            self.assertEqual(load_session(path), "synthetic-sid")
            self.assertNotIn("synthetic", out)
            auth.assert_called_once()
            client.close.assert_called_once()

    def test_failed_save_revokes_new_session(self):
        client = Mock(sid="synthetic-sid")
        with (
            patch("qnap_sdk.cli.getpass.getpass", return_value="password"),
            patch("qnap_sdk.cli.QnapClient.authenticate", return_value=client),
            patch("qnap_sdk.cli.save_session", side_effect=OSError("secret must not appear")),
        ):
            result, out, err = self.run_cli(
                "login",
                "--origin",
                "https://nas.invalid",
                "--username",
                "test",
                "--session-file",
                "/unused",
            )
        self.assertEqual(result, 1)
        client.logout.assert_called_once()
        self.assertNotIn("secret", out + err)

    def test_logout_removes_saved_session_after_confirmation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "session"
            save_session(path, "synthetic-sid")
            with patch("qnap_sdk.cli.QnapClient") as client:
                result, _, _ = self.run_cli(
                    "logout", "--origin", "https://nas.invalid", "--session-file", str(path)
                )
            self.assertEqual(result, 0)
            client.return_value.logout.assert_called_once()
            self.assertFalse(path.exists())

    def test_logout_failure_keeps_file_for_inspection(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "session"
            save_session(path, "synthetic-sid")
            with patch("qnap_sdk.cli.QnapClient") as client:
                client.return_value.logout.side_effect = QnapError("synthetic")
                result, _, _ = self.run_cli(
                    "logout", "--origin", "https://nas.invalid", "--session-file", str(path)
                )
            self.assertEqual(result, 1)
            self.assertTrue(path.exists())
