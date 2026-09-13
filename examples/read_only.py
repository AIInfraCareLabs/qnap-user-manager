"""Run: python read_only.py --origin https://nas.example.internal --username manager."""

import argparse
from getpass import getpass
from qnap_sdk import QnapClient, DEFAULT_FIRMWARE, get_profile


def main():
    parser = argparse.ArgumentParser(description="Native QNAP login and read-only inventory")
    parser.add_argument("--origin", required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--firmware", default=DEFAULT_FIRMWARE)
    parser.add_argument("--ca-file")
    parser.add_argument("--allow-http", action="store_true")
    args = parser.parse_args()
    client = QnapClient.authenticate(
        args.origin,
        args.firmware,
        get_profile(args.firmware),
        args.username,
        getpass("QNAP password: "),
        ca_file=args.ca_file,
        allow_http=args.allow_http,
    )
    try:
        client.check_session()
        print("users:", len(client.users.list_all()))
        print("groups:", len(client.groups.list_all()))
        print("shares:", len(client.shares.list_all()))
    finally:
        client.logout()


if __name__ == "__main__":
    main()
