"""Local bridge transport; the NAS session remains in an independent browser."""

import base64
import json
import urllib.parse
import urllib.request
from .client import QnapError


class BrowserTransport:
    def __init__(self, controller, manifest):
        url = urllib.parse.urlsplit(controller)
        if (
            url.scheme != "http"
            or url.hostname != "127.0.0.1"
            or not url.port
            or url.query
            or url.fragment
        ):
            raise QnapError("Expected a loopback browser controller")
        self.controller, self.manifest = controller.rstrip("/"), manifest

    def __call__(self, request):
        query = urllib.parse.parse_qs(
            urllib.parse.urlsplit(request.full_url).query, keep_blank_values=True
        )
        form = urllib.parse.parse_qs((request.data or b"").decode(), keep_blank_values=True)
        values = {**query, **form}
        op = getattr(request, "qnap_operation", None)
        spec = self.manifest.get("operations", {}).get(op)
        if not spec or spec.get("verified") is not True:
            raise QnapError("Cannot identify verified operation")
        parameters = {
            k: v if len(v) > 1 else v[0] for k, v in values.items() if k in spec["parameters"]
        }
        for key in ("lower", "upper"):
            if key in parameters:
                parameters[key] = int(parameters[key])
        command = urllib.request.Request(
            self.controller + "/sdk",
            data=json.dumps({"operation": op, "parameters": parameters}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(command, timeout=20) as response:
            data = json.load(response)
        if data.get("status") != 200:
            raise QnapError("Browser replay failed")
        return base64.b64decode(data["body"], validate=True)
