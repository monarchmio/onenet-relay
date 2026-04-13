"""
OneNET HTTP推送 验证+转发服务 (Vercel Serverless)
"""
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import hashlib
import base64
import json
import os

TOKEN = os.environ.get("ONENET_TOKEN", "mytoken")
FORWARD_URL = os.environ.get("FORWARD_URL", "")


def calculate_signature(token, nonce, msg):
    md5 = hashlib.md5()
    md5.update((token + nonce + msg).encode('utf-8'))
    return base64.b64encode(md5.digest()).decode('utf-8')


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        msg = params.get('msg', [None])[0]
        nonce = params.get('nonce', [None])[0]
        signature = params.get('signature', [None])[0]

        if not msg:
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write("OneNET Relay Service is running".encode('utf-8'))
            return

        # 签名验证（可选）
        if nonce and signature:
            expected = calculate_signature(TOKEN, nonce, msg)
            print(f"签名校验: expected={expected}, received={signature}, match={expected == signature}")

        # 关键：返回纯文本 msg
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(msg.encode('utf-8'))

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length else b''

        print(f"POST推送: {body.decode('utf-8', errors='replace')[:500]}")

        # 转发到本地后端
        if FORWARD_URL:
            try:
                import urllib.request
                req = urllib.request.Request(
                    f"{FORWARD_URL}/api/onenet/push",
                    data=body,
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                urllib.request.urlopen(req, timeout=3)
            except Exception as e:
                print(f"转发失败: {e}")

        # 必须快速返回200
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"OK")
