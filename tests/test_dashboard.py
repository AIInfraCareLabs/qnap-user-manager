"""Dashboard inventory must include every row, not only the first list page."""

import unittest

from qnap_sdk.dashboard import collect_inventory
from qnap_sdk.models import Group, Share, User


class FakeResource:
    def __init__(self, rows):
        self.rows = rows
        self.list_all_calls = 0

    def list(self):
        raise AssertionError("Dashboard must use list_all()")

    def list_all(self):
        self.list_all_calls += 1
        return self.rows


class FakeClient:
    def __init__(self, users, groups, shares):
        self.users = FakeResource(users)
        self.groups = FakeResource(groups)
        self.shares = FakeResource(shares)


class DashboardTests(unittest.TestCase):
    def test_inventory_collects_all_rows(self):
        users = [User(username=f"user{i:02d}") for i in range(25)]
        groups = [Group(name=f"group{i:02d}") for i in range(12)]
        shares = [Share(name=f"share{i:02d}") for i in range(11)]
        client = FakeClient(users, groups, shares)

        data = collect_inventory(client)

        self.assertEqual([row["username"] for row in data["users"]], [u.username for u in users])
        self.assertEqual(len(data["groups"]), 12)
        self.assertEqual(len(data["shares"]), 11)
        self.assertEqual(
            (
                client.users.list_all_calls,
                client.groups.list_all_calls,
                client.shares.list_all_calls,
            ),
            (1, 1, 1),
        )


if __name__ == "__main__":
    unittest.main()
