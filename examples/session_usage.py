"""Explicit SID persistence; no password or SID is printed."""

import argparse
from getpass import getpass
from qnap_sdk import QnapClient, DEFAULT_FIRMWARE, get_profile
from qnap_sdk.session import load_session, save_session


def main():
    parser = argparse.ArgumentParser(description="Save, reload, check and revoke a QNAP session")
    parser.add_argument("--origin", required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--session-file", required=True)
    parser.add_argument("--ca-file")
    args = parser.parse_args()
    profile = get_profile()
    client = QnapClient.authenticate(
        args.origin,
        DEFAULT_FIRMWARE,
        profile,
        args.username,
        getpass("QNAP password: "),
        ca_file=args.ca_file,
    )
    try:
        save_session(args.session_file, client.sid)
        restored = QnapClient(
            args.origin,
            DEFAULT_FIRMWARE,
            profile,
            load_session(args.session_file),
            ca_file=args.ca_file,
        )
        try:
            print("session valid:", restored.check_session())
        finally:
            restored.close()
    finally:
        client.logout()
        from pathlib import Path

        Path(args.session_file).unlink(missing_ok=True)


if __name__ == "__main__":
    main()
