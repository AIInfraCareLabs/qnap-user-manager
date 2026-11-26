"""Membership reads must not send pagination parameters the NAS ignores."""

import copy
import json
import unittest
from urllib.parse import parse_qs, urlsplit

from qnap_sdk import QnapClient, get_profile

PROFILE = get_profile()


def assert_no_pagination(test, request):
    query = parse_qs(urlsplit(request.full_url).query, keep_blank_values=True)
    form = parse_qs(request.data.decode(), keep_blank_values=True)
    test.assertNotIn("lower", query)
    test.assertNotIn("upper", query)
    test.assertNotIn("lower", form)
    test.assertNotIn("upper", form)


class MembershipWireTests(unittest.TestCase):
    def client(self):
        self.requests = []

        def transport(request):
            self.requests.append(request)
            return json.dumps(
                {
                    "authPassed": "1",
                    "func": {
                        "ownContent": {
                            "ownUser": "sdk_test_u",
                            "ownGroup": "sdk_test_g",
                        }
                    },
                }
            ).encode()

        return QnapClient(
            "https://nas.invalid",
            PROFILE["firmware"],
            copy.deepcopy(PROFILE),
            "synthetic",
            transport=transport,
            allow_test_writes=True,
            test_prefix="sdk_test_",
        )

    def test_membership_reads_have_no_pagination_parameters(self):
        client = self.client()

        self.assertEqual(client.groups.members("sdk_test_g"), ("sdk_test_u",))
        self.assertEqual(client.users.groups("sdk_test_u"), ("sdk_test_g",))
        self.assertEqual(len(self.requests), 2)
        for request in self.requests:
            assert_no_pagination(self, request)

    def test_membership_update_readback_has_no_pagination_parameters(self):
        client = self.client()

        self.assertEqual(client.groups.add_member("sdk_test_g", "sdk_test_u"), ("sdk_test_u",))
        readbacks = [r for r in self.requests if r.qnap_operation == "groups.members"]
        self.assertTrue(readbacks)
        for request in readbacks:
            assert_no_pagination(self, request)


if __name__ == "__main__":
    unittest.main()
