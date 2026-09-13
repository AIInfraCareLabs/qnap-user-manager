"""Authorized real-NAS regression using QnapClient's native HTTP transport."""

import argparse
import json
import secrets
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from qnap_sdk import QnapClient, Permission  # noqa: E402 - checkout runner bootstrap


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--origin", required=True)
    parser.add_argument(
        "--session-file", required=True, help="0600 file containing a temporary NAS SID"
    )
    parser.add_argument("--volume", type=int, default=1)
    args = parser.parse_args()
    session_file = Path(args.session_file)
    if stat.S_IMODE(session_file.stat().st_mode) & 0o077:
        parser.error("Session file must be private (chmod 600)")
    from qnap_sdk import get_profile

    profile = get_profile()
    client = QnapClient(
        args.origin,
        profile["firmware"],
        profile,
        session_file.read_text().strip(),
        allow_http=args.origin.startswith("http:"),
        allow_test_writes=True,
        test_prefix="sdk_test_0913_",
    )
    assert client.transport is None  # Native urllib transport; no browser bridge.
    names = {"users": "sdk_test_0913_u", "groups": "sdk_test_0913_g", "shares": "sdk_test_0913_s"}

    def inventory():
        return {
            kind: sorted(
                row.username if kind == "users" else row.name
                for row in getattr(client, kind).list_all()
            )
            for kind in names
        }

    baseline = inventory()
    if any(name in baseline[kind] for kind, name in names.items()):
        raise RuntimeError("Test resource already exists; refusing to modify it")
    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "Real NAS, native urllib transport, no browser",
        "firmware_profile": profile["firmware"],
        "checks": [],
        "cleanup_errors": [],
    }
    touched = set()

    def check(name, function):
        value = function()
        report["checks"].append(name)
        print("PASS " + name, flush=True)
        return value

    def require(condition):
        if not condition:
            raise RuntimeError("Live readback assertion failed")

    failed = False
    try:
        u, g, s = (names[k] for k in ("users", "groups", "shares"))
        touched.add("groups")
        check("groups.create", lambda: client.groups.create(g, description="Direct SDK regression"))
        touched.add("users")
        check(
            "users.create",
            lambda: client.users.create(u, secrets.token_urlsafe(24) + "aA1!", groups=[g]),
        )
        touched.add("shares")
        check(
            "shares.create",
            lambda: client.shares.create(
                s, volume=args.volume, description="Direct SDK regression"
            ),
        )
        check(
            "users.update",
            lambda: require(
                client.users.update(u, description="Updated direct test").description
                == "Updated direct test"
            ),
        )
        check(
            "groups.update",
            lambda: require(
                client.groups.update(g, description="Updated direct test").description
                == "Updated direct test"
            ),
        )
        check("groups.remove_member", lambda: client.groups.remove_member(g, u))
        check("groups.add_member", lambda: client.groups.add_member(g, u))
        check(
            "shares.update",
            lambda: require(
                client.shares.update(s, description="Updated direct test", hidden=True).description
                == "Updated direct test"
            ),
        )
        check(
            "users.reset_password",
            lambda: client.users.reset_password(u, secrets.token_urlsafe(24) + "aA1!"),
        )
        check("users.disable", lambda: require(client.users.disable(u).disabled is True))
        check(
            "users.reset_disabled_password",
            lambda: client.users.reset_password(u, secrets.token_urlsafe(24) + "aA1!"),
        )
        check("users.stays_disabled", lambda: require(client.users.get(u).disabled is True))
        check("users.enable", lambda: require(client.users.enable(u).disabled is False))
        for kind, subject in [("user", u), ("group", g)]:
            for permission in [Permission.READ_ONLY, Permission.READ_WRITE, Permission.DENY, None]:
                check(
                    "permissions." + kind + "." + (permission.value if permission else "revoke"),
                    lambda k=kind, x=subject, p=permission: client.permissions.set(
                        x, s, p, subject_type=k
                    ),
                )
    except Exception as error:
        failed = True
        report["failure_type"] = type(error).__name__  # No credentials or raw response output.
        print("FAILED; attempting test-resource cleanup", flush=True)
    finally:
        for kind in ("users", "groups", "shares"):
            if kind not in touched:
                continue
            try:
                if names[kind] in inventory()[kind]:
                    if kind == "shares":
                        client.shares.delete(names[kind], delete_files=True)
                    else:
                        getattr(client, kind).delete(names[kind])
                report["checks"].append(kind + ".cleanup")
            except Exception as error:
                report["cleanup_errors"].append(
                    {"resource": kind, "error_type": type(error).__name__}
                )
        try:
            report["baseline_restored"] = inventory() == baseline
        except Exception:
            report["baseline_restored"] = False
        client.close()
        report["passed"] = (
            not failed and not report["cleanup_errors"] and report["baseline_restored"]
        )
        folder = ROOT / "reports"
        folder.mkdir(exist_ok=True)
        (folder / "live-direct-regression.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
