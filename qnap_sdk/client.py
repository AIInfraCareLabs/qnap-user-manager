"""No guessed CGI actions. Every request requires a firmware-specific contract."""

import json
import math
import re
import time
import ssl
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Callable


class QnapError(Exception):
    pass


class UnverifiedOperation(QnapError):
    pass


class SessionExpired(QnapError):
    pass


def decode_response(body: bytes):
    if len(body) > 8 * 1024 * 1024:
        raise QnapError("Response exceeds size limit")
    try:
        value = json.loads(body)
        if not isinstance(value, dict):
            raise QnapError("Expected an object response")
        return value
    except (ValueError, UnicodeError):
        pass
    if b"<!DOCTYPE" in body.upper() or b"<!ENTITY" in body.upper():
        raise QnapError("Unsafe XML response")
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        raise QnapError("Expected JSON or XML; possible login page") from None

    def convert(node):
        if not len(node):
            return node.text or ""
        result = {}
        for child in node:
            value = convert(child)
            if child.tag in result:
                previous = result[child.tag]
                result[child.tag] = (
                    previous + [value] if isinstance(previous, list) else [previous, value]
                )
            else:
                result[child.tag] = value
        return result

    value = convert(root)
    if not isinstance(value, dict):
        raise QnapError("Expected an object response")
    return value


def field(data, path):
    for name in path.split("."):
        if not isinstance(data, dict) or name not in data:
            raise QnapError("Response does not match verified contract")
        data = data[name]
    return data


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise QnapError("Redirect rejected; check NAS address")


@dataclass(repr=False)
class QnapClient:
    base_url: str
    firmware: str
    manifest: dict
    sid: str
    ca_file: str | None = None
    timeout: float = 15
    allow_test_writes: bool = False
    test_prefix: str = "sdk_test_"
    transport: Callable | None = None
    allow_http: bool = False
    allow_writes: bool = False
    verification_timeout: float = 30

    def __post_init__(self):
        url = urllib.parse.urlsplit(self.base_url)
        if (
            url.scheme not in (("https", "http") if self.allow_http else ("https",))
            or not url.hostname
            or url.username
            or url.password
            or url.query
            or url.fragment
            or url.path not in ("", "/")
        ):
            raise QnapError("Use an HTTPS NAS origin without credentials or path")
        try:
            url.port
        except ValueError:
            raise QnapError("Invalid NAS port") from None
        if (
            not isinstance(self.timeout, (int, float))
            or not math.isfinite(self.timeout)
            or self.timeout <= 0
        ):
            raise QnapError("timeout must be positive and finite")
        if (
            not isinstance(self.verification_timeout, (int, float))
            or not math.isfinite(self.verification_timeout)
            or self.verification_timeout < 0
        ):
            raise QnapError("verification_timeout must be nonnegative and finite")
        self.base_url = self.base_url.rstrip("/")
        if self.firmware != self.manifest.get("firmware"):
            raise UnverifiedOperation("Exact firmware profile required")
        if not self.sid:
            raise QnapError("A session is required")
        if not isinstance(self.test_prefix, str) or len(self.test_prefix) < 8:
            raise QnapError("Test prefix must contain at least 8 characters")
        context = ssl.create_default_context(cafile=self.ca_file)
        self._opener = urllib.request.build_opener(
            NoRedirect(), urllib.request.HTTPSHandler(context=context)
        )

    @classmethod
    def authenticate(
        cls, base_url, firmware, manifest, username, password, *, security_code=None, **options
    ):
        client = cls(base_url, firmware, manifest, "INITIALIZING", **options)
        client.close()
        client.login(username, password, security_code=security_code)
        return client

    def login(self, username, password, *, security_code=None):
        from .auth import login

        return login(self, username, password, security_code)

    def check_session(self):
        from .auth import check_session

        return check_session(self)

    def logout(self):
        from .auth import logout

        return logout(self)

    def __repr__(self):
        return f"QnapClient(firmware={self.firmware!r})"

    def close(self):
        """Forget the local session. Does not claim to log out on the NAS."""
        self.sid = ""

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def call(self, operation: str, *, target: str | None = None, **parameters):
        spec = self.manifest.get("operations", {}).get(operation)
        if not spec or spec.get("verified") is not True or not spec.get("evidence"):
            raise UnverifiedOperation(f"No verified contract for {operation}")
        if not self.sid:
            raise SessionExpired("Session cleared; login required")
        path = spec.get("path", "")
        if (
            not path.startswith("/cgi-bin/")
            or not path.endswith(".cgi")
            or any(v in path for v in ("?", "#", "..", "\\", "%", "//"))
        ):
            raise QnapError("Invalid CGI path")
        method = spec.get("method")
        if method not in ("GET", "POST"):
            raise QnapError("Unsupported request method")
        if spec.get("read_only") is not True:
            if not target or (
                not self.allow_writes
                and (not self.allow_test_writes or not target.startswith(self.test_prefix))
            ):
                raise QnapError("Writes require explicit test mode and a prefixed test target")
            target_key = spec.get("target_parameter")
            if not target_key or target_key not in spec.get("parameters", []):
                raise QnapError("Missing verified target parameter")
            if target_key in parameters and parameters[target_key] != target:
                raise QnapError("Target mismatch")
            parameters[target_key] = target
            if not self.allow_writes:
                for key in parameters:
                    scoped = key in spec.get("scoped_parameters", []) or any(
                        re.fullmatch(p, key) for p in spec.get("scoped_patterns", [])
                    )
                    if scoped:
                        values = (
                            parameters[key]
                            if isinstance(parameters[key], (list, tuple))
                            else [parameters[key]]
                        )
                        if any(
                            not isinstance(v, str) or not v.startswith(self.test_prefix)
                            for v in values
                        ):
                            raise QnapError("Test writes cannot modify other resources")
        allowed = set(spec.get("parameters", []))
        fixed = spec.get("fixed", {})
        session_key = spec.get("session_parameter", "sid")
        unknown = {
            k
            for k in parameters
            if k not in allowed
            and not any(re.fullmatch(p, k) for p in spec.get("parameter_patterns", []))
        }
        if unknown or set(parameters) & (set(fixed) | {session_key}):
            raise QnapError("Unexpected or reserved parameters")
        if set(spec.get("required", [])) - (
            set(parameters) | set(fixed) | set(spec.get("defaults", {}))
        ):
            raise QnapError("Required parameter missing")
        if spec.get("verification", {}).get("kind") == "permission":
            for prefix in ("rd_share", "rw_share", "no_share", "empty_share"):
                if str(parameters.get(prefix + "_len", 0)) != str(int(prefix + "0" in parameters)):
                    raise QnapError("Permission counts do not match entries")
            if (
                sum(
                    key in parameters
                    for key in ("rd_share0", "rw_share0", "no_share0", "empty_share0")
                )
                != 1
            ):
                raise QnapError("Exactly one permission change per request is required")
        success = spec.get("success")
        if not success or not success.get("field") or not success.get("values"):
            raise UnverifiedOperation("Contract requires explicit success criteria")
        verification = spec.get("verification")
        if (
            verification
            and self.manifest["operations"].get(verification.get("operation"), {}).get("read_only")
            is not True
        ):
            raise UnverifiedOperation("Readback operation is unavailable")
        form = {**spec.get("defaults", {}), **fixed, **parameters, session_key: self.sid}
        query_keys = set(spec.get("query_parameters", []))
        query = form if method == "GET" else {k: v for k, v in form.items() if k in query_keys}
        body_form = {k: v for k, v in form.items() if k not in query_keys}
        encoded_query = urllib.parse.urlencode(query, doseq=True)
        url = self.base_url + path + ("?" + encoded_query if encoded_query else "")
        request = urllib.request.Request(
            url,
            data=urllib.parse.urlencode(body_form, doseq=True).encode()
            if method == "POST"
            else None,
            method=method,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json, application/xml",
            },
        )
        request.qnap_operation = operation
        try:
            if self.transport:
                body = self.transport(request)
            else:
                with self._opener.open(request, timeout=self.timeout) as response:
                    body = response.read(8 * 1024 * 1024 + 1)
        except urllib.error.HTTPError as error:
            if error.code in (401, 403):
                self.close()
                raise SessionExpired(
                    "Authentication or authorization failed; login required"
                ) from None
            raise QnapError(f"NAS HTTP error {error.code}") from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise QnapError(
                "NAS connection failed; check address, certificate and connectivity"
            ) from None
        data = decode_response(body)
        expiry = spec.get("session_expired")
        if expiry and str(field(data, expiry["field"])) in [str(v) for v in expiry["values"]]:
            self.close()
            raise SessionExpired("NAS session expired; login required")
        success = spec.get("success")
        if not success:
            raise UnverifiedOperation("Contract requires explicit success criteria")
        if str(field(data, success["field"])) not in [str(v) for v in success["values"]]:
            raise QnapError("NAS operation failed")
        for check in spec.get("success_checks", []):
            if str(field(data, check["field"])) not in [str(v) for v in check["values"]]:
                raise QnapError("NAS rejected the requested change")
        if spec.get("verification"):
            self._verify(spec["verification"], target, parameters)
        return data

    def _verify(self, verification, target, parameters):
        if verification.get("kind") == "absence":
            deadline = time.monotonic() + self.verification_timeout
            while True:
                spec = self.manifest["operations"][verification["operation"]]
                lower = 0
                present = False
                while True:
                    args = dict(verification.get("parameters", {}))
                    if "lower" in spec.get("parameters", []):
                        args.update(lower=lower, upper=lower + 1000)
                    observed = self.call(verification["operation"], **args)
                    total = int(field(observed, verification["count_field"]))
                    if total == 0:
                        break
                    rows = field(observed, verification["collection"])
                    if isinstance(rows, dict):
                        rows = [rows]
                    if not rows:
                        raise QnapError("Deletion verification pagination made no progress")
                    if any(field(r, verification["identity"]) == target for r in rows):
                        present = True
                        break
                    lower += len(rows)
                    if lower >= total:
                        break
                    if "lower" not in spec.get("parameters", []) or lower > 100000:
                        raise QnapError("Cannot confirm complete deletion list")
                if not present:
                    return
                if time.monotonic() >= deadline:
                    raise QnapError("Deletion not confirmed; inspect NAS before retrying")
                time.sleep(0.2)
        if verification.get("kind") == "permission":
            columns = {"rd_share0": "R", "rw_share0": "W", "no_share0": "I", "empty_share0": ""}
            changed = [key for key in columns if key in parameters]
            if len(changed) != 1:
                raise QnapError("Exactly one permission change per request is required")
            key = changed[0]
            verification = {
                "operation": verification["operation"],
                "parameters": {
                    verification["subject_parameter"]: "$target",
                    "lower": 0,
                    "upper": 1000,
                },
                "collection": "func.ownContent.shareroot.data.share",
                "identity": "sharename",
                "match_parameter": key,
                "checks": [{"field": "type", "value": columns[key], "default": ""}],
            }
        read_operation = verification["operation"]
        read_spec = self.manifest["operations"].get(read_operation, {})
        if read_spec.get("read_only") is not True:
            raise QnapError("Mutation verification must use a read-only operation")
        args = {
            key: target
            if value == "$target"
            else parameters.get(value[1:])
            if isinstance(value, str) and value.startswith("$")
            else value
            for key, value in verification.get("parameters", {}).items()
        }
        deadline = time.monotonic() + self.verification_timeout
        while True:
            observed = self.call(read_operation, **args)
            valid = True
            selected = observed
            if verification.get("collection"):
                rows = field(observed, verification["collection"])
                if isinstance(rows, dict):
                    rows = [rows]
                wanted = parameters[verification["match_parameter"]]
                selected = next(
                    (r for r in rows if field(r, verification["identity"]) == wanted), None
                )
                if selected is None:
                    valid = False
            for check in verification.get("checks", []):
                key = check.get("parameter")
                if key and key not in parameters:
                    continue
                expected = parameters[key] if key else check.get("value", target)
                if check.get("transform") == "invert_bool":
                    expected = "1" if str(expected) == "0" else "0"
                if selected is None:
                    continue
                try:
                    actual = field(selected, check["field"])
                except QnapError:
                    if "default" not in check:
                        raise
                    actual = check["default"]
                if "contains" in check:
                    if (str(expected) in (actual.split(", ") if actual else [])) != check[
                        "contains"
                    ]:
                        valid = False
                elif str(actual) != str(expected):
                    valid = False
            if valid:
                return
            if time.monotonic() >= deadline:
                raise QnapError(
                    "Write returned but readback did not confirm the requested state; inspect NAS before retrying"
                )
            time.sleep(0.2)

    def list_users(self, **params):
        return self.call("users.list", **params)

    def create_user(self, username, **params):
        return self.call("users.create", target=username, **params)

    def update_user(self, username, **params):
        return self.call("users.update", target=username, **params)

    def delete_user(self, username, **params):
        return self.call("users.delete", target=username, **params)

    def list_groups(self, **params):
        return self.call("groups.list", **params)

    def list_shares(self, **params):
        return self.call("shares.list", **params)

    @property
    def users(self):
        from .resources import Users

        return Users(self)

    @property
    def groups(self):
        from .resources import Groups

        return Groups(self)

    @property
    def shares(self):
        from .resources import Shares

        return Shares(self)

    @property
    def permissions(self):
        from .resources import Permissions

        return Permissions(self)

    @property
    def quota(self):
        from .resources import Quotas

        return Quotas(self)
