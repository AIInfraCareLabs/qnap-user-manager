"""Native QTS password login and current-session logout, without a browser."""

import base64
import urllib.error
import urllib.parse
import urllib.request
from .client import QnapError, SessionExpired, decode_response, field


def request(client, path, parameters, operation):
    req = urllib.request.Request(
        client.base_url + path,
        data=urllib.parse.urlencode(parameters).encode(),
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    req.qnap_operation = operation
    try:
        if client.transport:
            body = client.transport(req)
        else:
            with client._opener.open(req, timeout=client.timeout) as response:
                body = response.read(8 * 1024 * 1024 + 1)
    except urllib.error.HTTPError as error:
        if error.code in (401, 403):
            client.close()
            raise SessionExpired("Authentication or authorization rejected") from None
        raise QnapError(f"Authentication HTTP error {error.code}") from None
    except (urllib.error.URLError, OSError, TimeoutError):
        raise QnapError("Authentication connection failed") from None
    return decode_response(body)


def login(client, username, password, security_code=None):
    if (
        not isinstance(username, str)
        or not username
        or not isinstance(password, str)
        or not password
    ):
        raise QnapError("Username and password required")
    if client.sid:
        raise QnapError("Logout or clear the existing session before logging in again")
    parameters = {
        "user": username,
        "pwd": base64.b64encode(password.encode("utf-8")).decode(),
        "serviceKey": 1,
        "client_app": "QNAP Python SDK",
        "dont_verify_2sv_again": 0,
    }
    if security_code is not None:
        parameters["security_code"] = security_code
    data = request(client, "/cgi-bin/authLogin.cgi", parameters, "auth.login")
    if (
        str(data.get("need_2_step_verification", "0")) == "1"
        and str(data.get("authPassed", "0")) != "1"
    ):
        raise QnapError("Two-step verification required; provide security_code")
    if str(field(data, "authPassed")) != "1":
        raise SessionExpired("Login rejected")
    sid = field(data, "authSid")
    if not isinstance(sid, str) or not sid or len(sid) > 4096:
        raise QnapError("Login did not return a valid session")
    client.sid = sid


def check_session(client):
    if not client.sid:
        raise SessionExpired("No active session")
    data = request(
        client, "/cgi-bin/authLogin.cgi", {"sid": client.sid, "service": 1}, "auth.check_session"
    )
    if str(field(data, "authPassed")) != "1":
        client.close()
        raise SessionExpired("NAS session expired")
    return True


def logout(client):
    if not client.sid:
        return
    sid = client.sid
    try:
        request(client, "/cgi-bin/authLogout.cgi", {"sid": sid, "logout": 1}, "auth.logout")
        observed = request(
            client, "/cgi-bin/authLogin.cgi", {"sid": sid, "service": 1}, "auth.check_session"
        )
        if str(field(observed, "authPassed")) != "0":
            raise QnapError("NAS logout not confirmed")
    finally:
        client.close()
