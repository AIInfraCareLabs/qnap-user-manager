import unittest
from qnap_sdk import QnapClient, QnapError, UnverifiedOperation
from qnap_sdk.models import User


def make_client(body):
    manifest = {
        "firmware": "fixture",
        "operations": {
            "users.list": {
                "verified": True,
                "evidence": "unit test only",
                "path": "/cgi-bin/fixture.cgi",
                "method": "GET",
                "read_only": True,
                "parameters": [],
                "success": {"field": "result", "values": ["0"]},
                "model": {
                    "items_path": "users.user",
                    "fields": {"username": "name", "disabled": "disabled", "uid": "uid"},
                },
            }
        },
    }
    return QnapClient(
        "https://fixture.example", "fixture", manifest, "SECRET", transport=lambda req: body
    )


class ResourceTests(unittest.TestCase):
    def test_single_xml_user_is_collection(self):
        client = make_client(
            b"<r><result>0</result><users><user><name>alice</name><disabled>0</disabled><uid>1001</uid></user></users></r>"
        )
        self.assertEqual(client.users.list(), [User(username="alice", disabled=False, uid=1001)])

    def test_multiple_xml_users(self):
        client = make_client(
            b"<r><result>0</result><users><user><name>a</name><disabled>0</disabled><uid>1</uid></user><user><name>b</name><disabled>1</disabled><uid>2</uid></user></users></r>"
        )
        self.assertEqual([u.disabled for u in client.users.list()], [False, True])

    def test_missing_model_rejected_before_request(self):
        client = make_client(b"")
        del client.manifest["operations"]["users.list"]["model"]
        with self.assertRaises(UnverifiedOperation):
            client.users.list()

    def test_unknown_flag_is_error(self):
        client = make_client(
            b'{"result":"0","users":{"user":{"name":"a","disabled":"maybe","uid":"1"}}}'
        )
        with self.assertRaises(QnapError):
            client.users.list()


if __name__ == "__main__":
    unittest.main()
