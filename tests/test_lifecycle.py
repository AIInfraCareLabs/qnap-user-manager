"""Stateful device-contract simulation through the native request boundary."""

import json
import unittest
from urllib.parse import parse_qs, urlsplit
from qnap_sdk import QnapClient, Permission, QnapError, get_profile

U, G, S = "sdk_test_fixture_u", "sdk_test_fixture_g", "sdk_test_fixture_s"


class Device:
    def __init__(self):
        self.users, self.groups, self.shares, self.permissions = {}, {}, {}, {}
        self.operations = []

    def __call__(self, request):
        op = request.qnap_operation
        self.operations.append(op)
        values = parse_qs(urlsplit(request.full_url).query, keep_blank_values=True)
        values.update(parse_qs((request.data or b"").decode(), keep_blank_values=True))
        p = {key: value[0] for key, value in values.items()}
        assert p["sid"] == "synthetic"
        reply = {"authPassed": "1"}
        if op == "users.create":
            self.users[U] = dict(
                username=U,
                uid="1002",
                description=p["a_description"],
                email="",
                tel="",
                tel_country_code="",
                chk_disable="0",
                year="2026",
                month="9",
                day="13",
            )
        elif op == "users.update":
            self.users[U]["description"] = p["a_description"]
            if "a_enable" in p:
                self.users[U]["chk_disable"] = str(1 - int(p["a_enable"]))
        elif op == "users.set_password":
            reply["func"] = {"userPasswordEdit": {"passwordCheck": "0", "passwordChange": "0"}}
        elif op == "users.delete":
            self.users.pop(U)
        elif op == "users.list":
            reply["userroot"] = {
                "ret": "0",
                "count": str(len(self.users)),
                "data": {
                    "user": [
                        dict(
                            username=k,
                            userid=v["uid"],
                            description=v["description"],
                            user_enable=str(1 - int(v["chk_disable"])),
                        )
                        for k, v in self.users.items()
                    ]
                },
            }
        elif op == "users.get":
            reply["userInfo"] = self.users[p["userName"]]
        elif op == "users.groups":
            reply["func"] = {
                "ownContent": {
                    "ownGroup": ", ".join(
                        ["everyone"] + [k for k, v in self.groups.items() if U in v["members"]]
                    )
                }
            }
        elif op == "groups.create":
            self.groups[G] = {"groupName": G, "description": p["a_description"], "members": []}
        elif op == "groups.update":
            self.groups[G]["description"] = p["a_description"]
        elif op == "groups.members_update":
            if "select_user" in p:
                self.groups[G]["members"].append(p["select_user"])
            else:
                self.groups[G]["members"].remove(p["unselect_user"])
            reply["setting_result"] = "0"
        elif op == "groups.members":
            reply["func"] = {"ownContent": {"ownUser": ", ".join(self.groups[G]["members"])}}
        elif op == "groups.get":
            reply["group"] = self.groups[G]
        elif op == "groups.list":
            reply["grouproot"] = {
                "ret": "0",
                "count": str(len(self.groups)),
                "data": {
                    "group": [
                        dict(groupname=k, description=v["description"])
                        for k, v in self.groups.items()
                    ]
                },
            }
        elif op == "groups.delete":
            self.groups.pop(G)
        elif op == "shares.create":
            self.shares[S] = dict(
                shareName=S,
                comment=p["comment"],
                path="/" + S,
                selectedVol=p["vol_no"],
                hidden="0",
                oplocks="1",
                supportNameMangling="yes",
                ftp_wonly={"val": "0"},
                recyclePerShare="1",
                recycleAdministratorsOnly="1",
                qsync="0",
                hide_unreadable="yes",
                share_enumeration="no",
                timemachine="0",
                showSnapshots="yes",
            )
            reply["func"] = {"ownContent": {"return": "0"}}
        elif op == "shares.get":
            reply["shareProperty"] = self.shares[p["sharename"]]
        elif op == "shares.list":
            reply["func"] = {
                "ownContent": {
                    "shareInfo": {
                        "ret": "0",
                        "shareCount": str(len(self.shares)),
                        "data": {"share": [{"shareName": k} for k in self.shares]},
                    }
                }
            }
        elif op == "shares.update":
            share = self.shares.pop(S)
            share.update(
                shareName=p["new_sname"], comment=p["share_comment"], hidden=p["share_hidden"]
            )
            self.shares[p["new_sname"]] = share
            reply["shareProperty"] = {"setting_result": "0"}
        elif op == "shares.delete":
            self.shares.pop(S)
            reply["func"] = {"ownContent": {"return": "0"}}
        elif op.startswith("permissions."):
            kind = op.split(".")[1].split("_")[0]
            if op.endswith("_set"):
                self.permissions[kind] = next(
                    code
                    for prefix, code in [
                        ("rd_share", "R"),
                        ("rw_share", "W"),
                        ("no_share", "I"),
                        ("empty_share", ""),
                    ]
                    if prefix + "0" in p
                )
                reply["userInfo"] = {"setting_result": "0"}
            else:
                code = self.permissions.get(kind, "")
                row = {"sharename": S, "preview": code or "R"}
                if code:
                    row["type"] = code
                reply["func"] = {
                    "ownContent": {"shareroot": {"ret": "0", "data": {"count": "1", "share": row}}}
                }
        else:
            raise AssertionError(op)
        return json.dumps(reply).encode()


class LifecycleTests(unittest.TestCase):
    def test_crud_password_disable_membership_permissions_and_cleanup(self):
        device = Device()
        profile = get_profile()
        client = QnapClient(
            "https://nas.invalid",
            profile["firmware"],
            profile,
            "synthetic",
            transport=device,
            allow_test_writes=True,
            verification_timeout=0,
        )
        self.assertEqual(
            client.users.create(U, "synthetic-password", description="created").description,
            "created",
        )
        self.assertTrue(client.users.disable(U).disabled)
        client.users.reset_password(U, "replacement")
        self.assertTrue(client.users.update(U, description="updated").disabled)
        self.assertFalse(client.users.enable(U).disabled)
        self.assertEqual(client.groups.create(G, description="group", members=[U]).members, (U,))
        self.assertIn(G, client.users.get(U).groups)
        self.assertEqual(client.groups.update(G, description="updated").description, "updated")
        self.assertEqual(client.groups.remove_member(G, U), ())
        self.assertEqual(client.groups.add_member(G, U), (U,))
        self.assertEqual(
            client.shares.create(S, volume=1, description="share").description, "share"
        )
        self.assertEqual(
            client.shares.update(S, description="updated", hidden=True).description, "updated"
        )
        for subject, kind in ((U, "user"), (G, "group")):
            for permission in (Permission.READ_ONLY, Permission.READ_WRITE, Permission.DENY):
                self.assertEqual(
                    client.permissions.grant(subject, S, permission, subject_type=kind).permission,
                    permission,
                )
            revoked = client.permissions.delete(subject, S, subject_type=kind)
            self.assertIsNone(revoked.permission)
            self.assertEqual(revoked.effective_permission, Permission.READ_ONLY)
        client.shares.delete(S)
        client.groups.delete(G)
        client.users.delete(U)
        self.assertEqual(
            (client.users.list_all(), client.groups.list_all(), client.shares.list_all()),
            ([], [], []),
        )
        self.assertEqual(device.operations.count("users.set_password"), 1)

    def test_invalid_creation_password_is_rejected_without_request(self):
        device = Device()
        profile = get_profile()
        client = QnapClient(
            "https://nas.invalid", profile["firmware"], profile, "synthetic", transport=device
        )
        with self.assertRaises(QnapError):
            client.users.create(U, "密" * 22)
        self.assertEqual(device.operations, [])
