"""
OneNET HTTP推送 验证+转发服务
部署到 Render 等云平台，接收 OneNET 推送并转发到本地后端。
"""
from flask import Flask, request, Response
import hashlib
import base64
import json
import logging
import os
import requests as req
from datetime import datetime

app = Flask(__name__)

# 配置
TOKEN = os.environ.get("ONENET_TOKEN", "mytoken")
# 本地后端的 cpolar 地址（用于转发数据）
FORWARD_URL = os.environ.get("FORWARD_URL", "")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 内存存储最近的推送数据（云端查看用）
push_history = []


def calculate_signature(token, nonce, msg):
    md5 = hashlib.md5()
    md5.update((token + nonce + msg).encode('utf-8'))
    return base64.b64encode(md5.digest()).decode('utf-8')


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        msg = request.args.get('msg')
        nonce = request.args.get('nonce')
        signature = request.args.get('signature')

        logger.info(f"GET验证: msg={msg}, nonce={nonce}, signature={signature}")

        if not msg:
            return "OneNET Relay Service is running", 200

        # 签名验证（可选）
        if nonce and signature:
            expected = calculate_signature(TOKEN, nonce, msg)
            logger.info(f"签名校验: expected={expected}, received={signature}")
            if expected == signature:
                logger.info("签名验证通过!")
            else:
                logger.warning("签名不匹配，仍返回msg")

        # 关键：返回纯文本 msg
        return Response(msg, content_type='text/plain; charset=utf-8')

    elif request.method == 'POST':
        try:
            payload = request.get_json(force=True, silent=True) or {}
            logger.info(f"POST推送: {json.dumps(payload, ensure_ascii=False)[:500]}")

            # 存储到历史
            push_history.append({
                "time": datetime.now().isoformat(),
                "data": payload
            })
            # 只保留最近100条
            while len(push_history) > 100:
                push_history.pop(0)

            # 转发到本地后端
            if FORWARD_URL:
                try:
                    resp = req.post(
                        f"{FORWARD_URL}/api/onenet/push",
                        json=payload,
                        timeout=3,
                        headers={"Content-Type": "application/json"}
                    )
                    logger.info(f"转发到 {FORWARD_URL}: {resp.status_code}")
                except Exception as e:
                    logger.warning(f"转发失败: {e}")

        except Exception as e:
            logger.error(f"处理POST出错: {e}")

        # 必须快速返回200
        return Response("OK", status=200, content_type='text/plain')


@app.route('/history')
def history():
    """查看最近的推送记录"""
    return json.dumps(push_history[-20:], ensure_ascii=False, indent=2), 200, {'Content-Type': 'application/json'}


@app.route('/status')
def status():
    return json.dumps({
        "service": "OneNET Relay",
        "token": TOKEN[:3] + "***",
        "forward_url": FORWARD_URL or "(not set)",
        "history_count": len(push_history),
        "time": datetime.now().isoformat()
    }, ensure_ascii=False), 200, {'Content-Type': 'application/json'}


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
