"""Shared-folder enumeration uses the verified half-open pagination window."""

import copy
import json
import unittest
from urllib.parse import parse_qs, urlsplit

from qnap_sdk import QnapClient, get_profile

PROFILE = get_profile()
NAMES = [f"sdk_test_share{i}" for i in range(5)]


class SharesPaginationTests(unittest.TestCase):
    def client(self):
        self.requests = []
        total = len(NAMES)

        def transport(request):
            self.requests.append(request)
            query = parse_qs(urlsplit(request.full_url).query, keep_blank_values=True)
            form = parse_qs(request.data.decode(), keep_blank_values=True)
            values = {**query, **form}
            lower = int(values.get("lower", ["0"])[0])
            upper = int(values.get("upper", [str(total)])[0])
            page = [{"shareName": name} for name in NAMES[lower:upper]]
            return json.dumps(
                {
                    "authPassed": "1",
                    "func": {
                        "ownContent": {
                            "shareInfo": {
                                "ret": "0",
                                "shareCount": str(total),
                                "data": {"share": page},
                            }
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
        )

    def test_list_all_paginates(self):
        client = self.client()

        shares = client.shares.list_all(page_size=2)

        self.assertEqual([share.name for share in shares], NAMES)
        windows = []
        for request in self.requests:
            query = parse_qs(urlsplit(request.full_url).query, keep_blank_values=True)
            form = parse_qs(request.data.decode(), keep_blank_values=True)
            values = {**query, **form}
            windows.append((int(values["lower"][0]), int(values["upper"][0])))
        self.assertEqual(windows, [(0, 2), (2, 4), (4, 6)])

    def test_list_accepts_explicit_window(self):
        client = self.client()

        shares = client.shares.list(lower=1, upper=3)

        self.assertEqual([share.name for share in shares], NAMES[1:3])


if __name__ == "__main__":
    unittest.main()
