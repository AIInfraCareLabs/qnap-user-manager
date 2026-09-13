"""Loopback read-only internal dashboard using the verified SDK."""

import argparse
import dataclasses
import json
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from .client import QnapClient
from .browser_transport import BrowserTransport

PAGE = """<!doctype html><html lang="zh"><meta charset="utf-8"><title>QNAP 用户管理</title><style>body{font:16px system-ui;background:#f4f6f8;color:#203040;max-width:1080px;margin:40px auto}section{background:white;padding:24px;margin:20px 0;border-radius:12px}table{border-collapse:collapse;width:100%}td,th{text-align:left;padding:12px;border-bottom:1px solid #eee}button{padding:10px 20px;cursor:pointer}small{color:#657080}</style><h1>QNAP 用户管理</h1><p>QTS 5.1.9.2954 · 实时只读管理</p><button id="refresh">刷新</button><p id="status"></p><main id="content"></main><small>SDK 已验证用户、组、共享目录及权限增删改查；此界面提供只读查看。</small><script>
const main=document.getElementById('content'),status=document.getElementById('status');
async function load(){status.textContent='正在读取 NAS…';try{const r=await fetch(location.pathname+'/data');const data=await r.json();if(!r.ok)throw Error();main.replaceChildren();for(const [name,rows] of Object.entries(data)){const section=document.createElement('section'),h=document.createElement('h2');h.textContent=({users:'用户',groups:'用户组',shares:'共享文件夹'})[name]+'（'+rows.length+'）';section.append(h);const table=document.createElement('table');for(const row of rows){const tr=document.createElement('tr');for(const key of (name==='users'?['username','description','disabled']:name==='groups'?['name','description']:['name'])){const td=document.createElement('td');td.textContent=key==='disabled'?(row[key]?'已禁用':'已启用'):row[key];tr.append(td)}table.append(tr)}section.append(table);main.append(section)}status.textContent='读取成功 · '+new Date().toLocaleTimeString()}catch{status.textContent='读取失败，请检查独立 QTS 窗口的登录状态。'}}document.getElementById('refresh').onclick=load;load();</script></html>"""


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--controller", required=True)
    p.add_argument("--profile", required=True)
    p.add_argument("--port", type=int, default=0)
    p.add_argument("--token")
    a = p.parse_args()
    controller = json.loads(Path(a.controller).read_text())
    profile = json.loads(Path(a.profile).read_text())
    client = QnapClient(
        controller["origin"],
        profile["firmware"],
        profile,
        "BROWSER_MANAGED",
        transport=BrowserTransport(controller["url"], profile),
        allow_http=controller["origin"].startswith("http:"),
    )
    token = a.token or secrets.token_hex(24)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            if self.headers.get("Host") != "127.0.0.1:" + str(
                self.server.server_port
            ) or self.path not in ("/" + token, "/" + token + "/data"):
                self.send_error(404)
                return
            try:
                if self.path.endswith("/data"):
                    body = json.dumps(
                        {
                            k: [dataclasses.asdict(x) for x in getattr(client, k).list()]
                            for k in ("users", "groups", "shares")
                        },
                        ensure_ascii=False,
                    ).encode()
                    mime = "application/json"
                else:
                    body = PAGE.encode()
                    mime = "text/html; charset=utf-8"
                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Frame-Options", "DENY")
                self.end_headers()
                self.wfile.write(body)
            except Exception:
                self.send_error(502, "NAS read failed")

    server = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    print("http://127.0.0.1:" + str(server.server_port) + "/" + token, flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
