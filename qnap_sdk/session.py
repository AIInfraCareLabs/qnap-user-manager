"""Private SID files for explicitly requested command-line session persistence."""

import os
import stat
import tempfile
from pathlib import Path
from .client import QnapError


def save_session(path: str | Path, sid: str) -> None:
    """Atomically replace a SID file with mode 0600; never store passwords."""
    if not isinstance(sid, str) or not sid or len(sid) > 4096 or "\n" in sid or "\r" in sid:
        raise QnapError("Invalid session identifier")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".qnap-session-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(sid + "\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def load_session(path: str | Path) -> str:
    """Read a private regular file, refusing symlinks and oversized contents."""
    path = Path(path)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    if path.is_symlink():
        raise QnapError("Session symlinks are not accepted")
    fd = os.open(path, flags)
    with os.fdopen(fd, "r", encoding="utf-8") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) & 0o077:
            raise QnapError("Session file must be regular and private (0600)")
        sid = stream.read(4098).strip()
    if not sid or len(sid) > 4096 or "\n" in sid or "\r" in sid:
        raise QnapError("Invalid session file")
    return sid
