"""Offline discovery: inventories contain parameter names, never request values."""

import json
import re
from pathlib import Path
from urllib.parse import urlsplit, parse_qsl


def discover_har(path, origin):
    expected = urlsplit(origin)
    if (
        expected.scheme not in ("http", "https")
        or not expected.hostname
        or expected.username
        or expected.password
        or expected.query
        or expected.fragment
        or expected.path not in ("", "/")
    ):
        raise ValueError("HTTP(S) origin without credentials or path required")
    records = {}
    for entry in json.loads(Path(path).read_text()).get("log", {}).get("entries", []):
        request = entry.get("request", {})
        url = urlsplit(request.get("url", ""))
        if (url.scheme, url.hostname, url.port) != (
            expected.scheme,
            expected.hostname,
            expected.port,
        ):
            continue
        if not url.path.startswith("/cgi-bin/") or not url.path.endswith(".cgi"):
            continue
        names = {name for name, _ in parse_qsl(url.query)}
        names.update(item["name"] for item in request.get("queryString", []) if "name" in item)
        post = request.get("postData", {})
        names.update(item["name"] for item in post.get("params", []) if "name" in item)
        if "application/x-www-form-urlencoded" in post.get("mimeType", ""):
            names.update(name for name, _ in parse_qsl(post.get("text", "")))
        key = (request.get("method", ""), url.path)
        records.setdefault(key, set()).update(names)
    return [
        {
            "method": method,
            "path": path,
            "parameters": sorted(names),
            "verified": False,
            "read_only": None,
            "evidence": "HAR observation; no dynamic validation",
        }
        for (method, path), names in sorted(records.items())
    ]


def discover_js(directory):
    records = set()
    for path in Path(directory).rglob("*.js"):
        for match in re.finditer(
            r"/cgi-bin/[A-Za-z0-9_./-]+\.cgi", path.read_text(errors="replace")
        ):
            records.add(match.group())
    return [
        {"path": path, "verified": False, "read_only": None, "evidence": "JS literal only"}
        for path in sorted(records)
    ]
