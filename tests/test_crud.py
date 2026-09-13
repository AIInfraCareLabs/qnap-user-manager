"""Failure-oriented tests using the actual device contract, with synthetic identities."""

import copy
import json
import unittest
from qnap_sdk import QnapClient, QnapError, Permission

from qnap_sdk import get_profile

PROFILE = get_profile()
U = "sdk_test_0913_u"
S = "sdk_test_0913_s"


def user_list(count=1):
    return {
        "authPassed": "1",
        "userroot": {
            "ret": "0",
            "count": str(count),
            "data": {
                "user": {"username": U, "userid": "1002", "description": "old", "user_enable": "1"}
            },
        },
    }


def user_get():
    return {
        "authPassed": "1",
        "userInfo": {
            "username": U,
            "uid": "1002",
            "description": "old",
            "email": "user@example.invalid",
            "tel": "1234",
            "tel_country_code": "+86",
            "chk_disable": "0",
            "year": "2026",
            "month": "9",
            "day": "13",
        },
    }


def permission_get(code="R", effective="R"):
    row = {"sharename": S, "preview": effective}
    if code is not None:
        row["type"] = code
    return {
        "authPassed": "1",
        "func": {"ownContent": {"shareroot": {"ret": "0", "data": {"count": "1", "share": row}}}},
    }


class CRUDTests(unittest.TestCase):
    def client(self, reply, **options):
        self.requests = []

        def transport(request):
            self.requests.append(request)
            return json.dumps(reply(request)).encode()

        return QnapClient(
            "https://nas.invalid",
            PROFILE["firmware"],
            copy.deepcopy(PROFILE),
            "DO_NOT_LOG",
            transport=transport,
            test_prefix="sdk_test_0913_",
            verification_timeout=0,
            **options,
        )

    def test_default_write_is_rejected_before_network(self):
        c = self.client(lambda r: {"authPassed": "1"})
        with self.assertRaises(QnapError):
            c.call("users.update", target=U, a_description="new")
        self.assertEqual(self.requests, [])

    def test_test_permission_cannot_touch_existing_share(self):
        c = self.client(lambda r: {"authPassed": "1"}, allow_test_writes=True)
        with self.assertRaises(QnapError):
            c.call(
                "permissions.user_set",
                target=U,
                rd_share_len=1,
                rw_share_len=0,
                no_share_len=0,
                empty_share_len=0,
                rd_share0="Public",
            )
        self.assertEqual(self.requests, [])

    def test_authenticated_but_silently_ignored_write_fails_readback(self):
        c = self.client(
            lambda r: user_get() if r.qnap_operation == "users.get" else {"authPassed": "1"},
            allow_test_writes=True,
        )
        with self.assertRaises(QnapError):
            c.call("users.update", target=U, a_description="new")
        self.assertEqual([r.qnap_operation for r in self.requests], ["users.update", "users.get"])

    def test_permission_counts_are_checked_before_network(self):
        c = self.client(lambda r: {"authPassed": "1"}, allow_test_writes=True)
        with self.assertRaises(QnapError):
            c.call("permissions.user_set", target=U, rd_share_len=2, rd_share0=S)
        self.assertEqual(self.requests, [])

    def test_revoke_keeps_inherited_permission_distinct(self):
        def reply(r):
            if r.qnap_operation == "users.list":
                return user_list()
            if r.qnap_operation == "permissions.user_get":
                return permission_get(None, "R")
            return {"authPassed": "1", "userInfo": {"setting_result": "0"}}

        c = self.client(reply, allow_test_writes=True)
        result = c.permissions.revoke(U, S)
        self.assertIsNone(result.permission)
        self.assertEqual(result.effective_permission, Permission.READ_ONLY)
        self.assertEqual(sum(r.qnap_operation == "permissions.user_set" for r in self.requests), 1)

    def test_permission_failure_does_not_retry_write(self):
        c = self.client(
            lambda r: (
                permission_get("W")
                if r.qnap_operation == "permissions.user_get"
                else {"authPassed": "1"}
            ),
            allow_test_writes=True,
        )
        with self.assertRaises(QnapError):
            c.call("permissions.user_set", target=U, rd_share_len=1, rd_share0=S)
        self.assertEqual(
            [r.qnap_operation for r in self.requests],
            ["permissions.user_set", "permissions.user_get"],
        )

    def test_async_deletion_polls_reads_and_sends_one_write(self):
        reads = 0

        def reply(r):
            nonlocal reads
            if r.qnap_operation == "users.list":
                reads += 1
                return (
                    user_list()
                    if reads == 1
                    else {"authPassed": "1", "userroot": {"ret": "0", "count": "0"}}
                )
            return {"authPassed": "1"}

        c = self.client(reply, allow_test_writes=True)
        c.verification_timeout = 1
        c.call("users.delete", target=U)
        self.assertEqual(sum(r.qnap_operation == "users.delete" for r in self.requests), 1)
        self.assertEqual(reads, 2)

    def test_pagination_repeated_page_is_rejected(self):
        c = self.client(lambda r: user_list(2))
        with self.assertRaises(QnapError):
            c.users.list_all(page_size=1)

    def test_update_preserves_contact_fields(self):
        from urllib.parse import parse_qs

        old = user_get()

        def reply(r):
            if r.qnap_operation == "users.get":
                return old
            if r.qnap_operation == "users.list":
                return user_list()
            if r.qnap_operation == "users.groups":
                return {"authPassed": "1", "func": {"ownContent": {"ownGroup": "everyone"}}}
            values = parse_qs(r.data.decode(), keep_blank_values=True)
            self.assertEqual(values["a_email"], ["user@example.invalid"])
            self.assertEqual(values["a_tel"], ["1234"])
            self.assertEqual(values["a_uid"], ["1002"])
            old["userInfo"]["description"] = values["a_description"][0]
            return {"authPassed": "1"}

        c = self.client(reply, allow_test_writes=True)
        self.assertEqual(c.users.update(U, description="new").description, "new")

    def test_unavailable_readback_blocks_write(self):
        c = self.client(lambda r: {"authPassed": "1"}, allow_test_writes=True)
        c.manifest["operations"].pop("users.get")
        with self.assertRaises(QnapError):
            c.call("users.update", target=U, a_description="new")
        self.assertEqual(self.requests, [])

    def test_shared_folder_update_preserves_name_mangling_and_snapshots(self):
        from urllib.parse import parse_qs

        properties = {
            "shareName": S,
            "comment": "old",
            "path": "/" + S,
            "selectedVol": "1",
            "hidden": "0",
            "oplocks": "1",
            "supportNameMangling": "yes",
            "ftp_wonly": {"val": "0"},
            "recyclePerShare": "1",
            "recycleAdministratorsOnly": "1",
            "qsync": "0",
            "hide_unreadable": "yes",
            "share_enumeration": "no",
            "timemachine": "0",
            "showSnapshots": "yes",
        }

        def reply(r):
            if r.qnap_operation == "shares.list":
                return {
                    "authPassed": "1",
                    "func": {
                        "ownContent": {
                            "shareInfo": {
                                "ret": "0",
                                "shareCount": "1",
                                "data": {"share": {"shareName": S}},
                            }
                        }
                    },
                }
            if r.qnap_operation == "shares.get":
                return {"authPassed": "1", "shareProperty": properties}
            values = parse_qs(r.data.decode(), keep_blank_values=True)
            self.assertEqual(values["mangled_names"], ["1"])
            self.assertEqual(values["showSnapshots"], ["1"])
            self.assertEqual(values["recycle_bin"], ["1"])
            self.assertEqual(values["manual_path"], ["/" + S])
            self.assertEqual(values["oplocks"], ["1"])
            properties["comment"] = values["share_comment"][0]
            return {"authPassed": "1", "shareProperty": {"setting_result": "0"}}

        c = self.client(reply, allow_test_writes=True)
        self.assertEqual(c.shares.update(S, description="new").description, "new")

    def test_disable_requires_boolean_before_network(self):
        c = self.client(lambda r: {})
        with self.assertRaises(QnapError):
            c.users.set_disabled(U, "false")
        self.assertEqual(self.requests, [])
