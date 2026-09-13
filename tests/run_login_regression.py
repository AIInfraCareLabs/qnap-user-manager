"""Hidden terminal credential entry, native login/session regression and live CRUD."""

import argparse
import getpass
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from qnap_sdk import QnapClient, SessionExpired  # noqa: E402 - checkout runner bootstrap


from qnap_sdk.session import save_session  # noqa: E402


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--origin", required=True)
    p.add_argument("--username", default="manager")
    p.add_argument("--session-file", required=True)
    args = p.parse_args()
    # Refuse a pipe that could echo passwords or capture credentials in a log.
    if not sys.stdin.isatty():
        p.error("Run this command in an interactive terminal")
    from qnap_sdk import get_profile

    profile = get_profile()
    password = getpass.getpass("QNAP 管理密码（隐藏输入）：")
    security_code = None
    client = None
    path = Path(args.session_file)
    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "browser_required": False,
        "checks": [],
        "passed": False,
    }

    def login():
        return QnapClient.authenticate(
            args.origin,
            profile["firmware"],
            profile,
            args.username,
            password,
            security_code=security_code,
            allow_http=args.origin.startswith("http:"),
        )

    try:
        try:
            client = login()
        except Exception as error:
            if "Two-step verification required" not in str(error):
                raise
            security_code = getpass.getpass("双重验证代码（隐藏输入）：")
            client = login()
        client.check_session()
        report["checks"].extend(["login", "session_check"])
        old_sid = client.sid
        client.logout()
        report["checks"].append("logout_revocation")
        old = QnapClient(
            args.origin,
            profile["firmware"],
            profile,
            old_sid,
            allow_http=args.origin.startswith("http:"),
        )
        try:
            old.check_session()
        except SessionExpired:
            report["checks"].append("revoked_session_rejected")
        else:
            raise RuntimeError("Revoked session was still accepted")
        finally:
            old.close()
            old_sid = None
        client = login()
        client.check_session()
        report["checks"].append("relogin")
        save_session(path, client.sid)
        print("nas-session 已生成（权限 0600）；开始原生 HTTP 回归。", flush=True)
        spec = importlib.util.spec_from_file_location(
            "live_regression", ROOT / "tests/run_live_regression.py"
        )
        live = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(live)
        previous = sys.argv
        try:
            sys.argv = ["run_live_regression", "--origin", args.origin, "--session-file", str(path)]
            code = live.main()
        finally:
            sys.argv = previous
        client.logout()
        path.unlink(missing_ok=True)
        report["checks"].append("post_regression_logout")
        if code != 0:
            raise RuntimeError("Live regression failed; inspect cleanup report")
        # Keep a freshly authenticated SID for the requested nas-session file.
        client = login()
        client.check_session()
        save_session(path, client.sid)
        report["checks"].append("fresh_session_saved")
        report["passed"] = True
        report["session_file"] = str(path)
        report["session_valid_at_save"] = True
        print("真实回归通过；新 nas-session 已保存。SID 和密码未输出。", flush=True)
        client.close()
        client = None
    except Exception as error:
        report["failure_type"] = type(error).__name__
        print("回归未完成：" + type(error).__name__ + "。认证失败不自动重试。", flush=True)
        if client:
            try:
                client.logout()
            except Exception:
                report["logout_cleanup_failed"] = True
        path.unlink(missing_ok=True)
    finally:
        password = None
        security_code = None
        directory = ROOT / "reports"
        directory.mkdir(exist_ok=True)
        (directory / "live-auth-regression.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
