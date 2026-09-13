import argparse
import getpass
import json
import sys
from pathlib import Path
from .client import QnapClient, QnapError
from .discovery import discover_har, discover_js
from .profile import DEFAULT_FIRMWARE, available_profiles, get_profile
from .session import save_session, load_session


def main():
    parser = argparse.ArgumentParser(description="QNAP 内部用户管理 / 接口发现")
    from . import __version__

    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)
    har = sub.add_parser("discover-har", help="离线分析 HAR，仅保存参数名")
    har.add_argument("file")
    har.add_argument("--origin", required=True)
    js = sub.add_parser("discover-js", help="离线检索前端 JS 中的 CGI 路径")
    js.add_argument("directory")
    contracts = sub.add_parser("contracts", help="显示固件接口的验证状态")
    contracts.add_argument("profile", nargs="?")
    sub.add_parser("profiles", help="列出随包安装的固件契约")
    for name in ("login", "logout"):
        auth = sub.add_parser(name, help="原生 HTTP 登录或退出")
        auth.add_argument("--origin", required=True)
        auth.add_argument("--firmware", default=DEFAULT_FIRMWARE)
        auth.add_argument("--session-file", required=True)
        auth.add_argument("--allow-http", action="store_true")
        auth.add_argument("--ca-file")
        if name == "login":
            auth.add_argument("--username", required=True)
    call = sub.add_parser("call", help="调用已验证接口；SID 通过隐藏输入提供")
    call.add_argument("operation")
    call.add_argument("--origin", required=True)
    call.add_argument("--firmware", required=True)
    call.add_argument("--profile", required=True)
    call.add_argument("--ca-file")
    call.add_argument("--params-file", help="JSON 参数文件；含密码时请设置权限 0600")
    call.add_argument("--write", action="store_true", help="明确开放正常资源写入")
    call.add_argument("--allow-http", action="store_true")
    call.add_argument("--test-write", action="store_true")
    call.add_argument("--target")
    args = parser.parse_args()
    try:
        if args.command == "profiles":
            data = {"firmwares": available_profiles()}
        elif args.command in ("login", "logout"):
            manifest = get_profile(args.firmware)
            if args.command == "login":
                password = getpass.getpass("QNAP 管理密码（隐藏输入）：")
                client = QnapClient.authenticate(
                    args.origin,
                    args.firmware,
                    manifest,
                    args.username,
                    password,
                    allow_http=args.allow_http,
                    ca_file=args.ca_file,
                )
                password = None
                try:
                    save_session(args.session_file, client.sid)
                except Exception:
                    client.logout()
                    raise
                finally:
                    client.close()
            else:
                client = QnapClient(
                    args.origin,
                    args.firmware,
                    manifest,
                    load_session(args.session_file),
                    allow_http=args.allow_http,
                    ca_file=args.ca_file,
                )
                client.logout()
                Path(args.session_file).unlink()
            data = {"operation": args.command, "status": "success"}
        elif args.command == "discover-har":
            data = discover_har(args.file, args.origin)
        elif args.command == "discover-js":
            data = discover_js(args.directory)
        elif args.command == "contracts":
            profile = json.loads(Path(args.profile).read_text()) if args.profile else get_profile()
            data = {
                "firmware": profile.get("firmware"),
                "operations": [
                    {
                        "operation": name,
                        "verified": spec.get("verified") is True,
                        "read_only": spec.get("read_only"),
                    }
                    for name, spec in profile.get("operations", {}).items()
                ],
            }
        else:
            profile = json.loads(Path(args.profile).read_text())
            params = json.loads(Path(args.params_file).read_text()) if args.params_file else {}
            sid = getpass.getpass("请先登录 QTS，输入临时 SID（隐藏输入，不保存）：")
            with QnapClient(
                args.origin,
                args.firmware,
                profile,
                sid,
                ca_file=args.ca_file,
                allow_test_writes=args.test_write,
                allow_writes=args.write,
                allow_http=args.allow_http,
            ) as client:
                client.call(args.operation, target=args.target, **params)
            # Never print arbitrary NAS responses, which can contain credentials.
            data = {"operation": args.operation, "status": "success"}
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0
    except (QnapError, ValueError, OSError, EOFError):
        print("操作未完成：请检查接口验证状态、会话、参数、文件及证书。", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
