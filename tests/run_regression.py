"""Run offline SDK regression with network connections and processes forbidden."""

import io
import json
import platform
import sys
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def forbidden(*args, **kwargs):
    raise AssertionError("Offline regression forbids network connections and process launches")


def main():
    output = io.StringIO()
    started = time.monotonic()
    with (
        patch("socket.socket.connect", forbidden),
        patch("socket.socket.connect_ex", forbidden),
        patch("subprocess.Popen", forbidden),
    ):
        suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_*.py")
        result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    log = output.getvalue()
    print(log, end="")
    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "mode": "Offline: injected transports and anonymized response fixtures",
        "browser_required": False,
        "network_connections_forbidden": True,
        "process_launches_forbidden": True,
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "passed": result.wasSuccessful(),
        "duration_seconds": round(time.monotonic() - started, 3),
        "limitations": ["Does not make fresh requests to a real NAS or verify SMB authentication."],
    }
    directory = ROOT / "reports"
    directory.mkdir(exist_ok=True)
    (directory / "offline-regression.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    (directory / "offline-regression.txt").write_text(log)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
