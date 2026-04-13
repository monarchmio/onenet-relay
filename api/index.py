"""
OneNET HTTP推送 验证+转发服务 (Vercel Serverless - Flask WSGI)
"""
from flask import Flask, request, Response
import hashlib
import base64
import json
import os

app = Flask(__name__)

TOKEN = os.environ.get("ONENET_TOKEN", "mytoken")
FORWARD_URL = os.environ.get("FORWARD_URL", "")


def calculate_signature(token, nonce, msg):
    md5 = hashlib.md5()
    md5.update((token + nonce + msg).encode('utf-8'))
    return base64.b64encode(md5.digest()).decode('utf-8')


@app.route('/', defaults={'path': ''}, methods=['GET', 'POST'])
@app.route('/<path:path>', methods=['GET', 'POST'])
def catch_all(path):
    if request.method == 'GET':
        msg = request.args.get('msg')
        nonce = request.args.get('nonce')
        signature = request.args.get('signature')

        print(f"GET: msg={msg}, nonce={nonce}, signature={signature}")

        if not msg:
            return Response("OneNET Relay Service is running", status=200,
                            content_type='text/plain; charset=utf-8')

        if nonce and signature:
            expected = calculate_signature(TOKEN, nonce, msg)
            print(f"签名: expected={expected}, received={signature}, match={expected == signature}")

        # 关键：返回纯 msg 文本，无任何多余字符
        return Response(msg, status=200, content_type='text/plain; charset=utf-8')

    elif request.method == 'POST':
        try:
            body = request.get_data()
            print(f"POST: {body.decode('utf-8', errors='replace')[:500]}")

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
        except Exception as e:
            print(f"POST错误: {e}")

        return Response("OK", status=200, content_type='text/plain')
