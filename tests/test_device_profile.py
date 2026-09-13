from qnap_sdk import get_profile
import pathlib
import unittest
from urllib.parse import urlsplit, parse_qs
from qnap_sdk import QnapClient

ROOT = pathlib.Path(__file__).resolve().parent.parent


class DeviceProfileTests(unittest.TestCase):
    def test_captured_response_mapping_and_wire_parameters(self):
        profile = get_profile()

        def transport(req):
            q = parse_qs(urlsplit(req.full_url).query)
            f = parse_qs(req.data.decode())
            name = {"user": "users.list", "group": "groups.list", "share": "shares.list"}[
                q["subfunc"][0]
            ]
            self.assertEqual(q["sid"], ["test-session"])
            self.assertNotIn("sid", f)
            if name != "shares.list":
                self.assertEqual(f["upper"], ["10"])
                self.assertEqual(q["getdata"], ["1"])
            return (ROOT / "tests/fixtures" / (name + ".xml")).read_bytes()

        c = QnapClient(
            "https://test.invalid",
            profile["firmware"],
            profile,
            "test-session",
            transport=transport,
        )
        users = c.users.list()
        self.assertEqual(len(users), 3)
        self.assertEqual([x.disabled for x in users], [True, False, True])
        self.assertEqual(len(c.groups.list()), 3)
        self.assertEqual(len(c.shares.list()), 2)
