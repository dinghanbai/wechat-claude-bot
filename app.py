import os
import hashlib
import xml.etree.ElementTree as ET
from flask import Flask, request
import anthropic
import time

app = Flask(__name__)

# 从环境变量读取配置
WECHAT_TOKEN = os.environ.get("WECHAT_TOKEN", "your_token_here")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def check_signature(signature, timestamp, nonce):
    """验证微信请求签名"""
    tmp_list = sorted([WECHAT_TOKEN, timestamp, nonce])
    tmp_str = "".join(tmp_list)
    sha1 = hashlib.sha1(tmp_str.encode("utf-8")).hexdigest()
    return sha1 == signature


def ask_claude(user_message):
    """调用 Claude API 获取回复"""
    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": user_message}],
        )
        return message.content[0].text
    except Exception as e:
        return f"抱歉，出现了错误：{str(e)}"


def make_reply_xml(to_user, from_user, content):
    """生成微信回复 XML"""
    return f"""<xml>
<ToUserName><![CDATA[{to_user}]]></ToUserName>
<FromUserName><![CDATA[{from_user}]]></FromUserName>
<CreateTime>{int(time.time())}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[{content}]]></Content>
</xml>"""


@app.route("/wechat", methods=["GET", "POST"])
def wechat():
    signature = request.args.get("signature", "")
    timestamp = request.args.get("timestamp", "")
    nonce = request.args.get("nonce", "")

    # 微信服务器验证
    if not check_signature(signature, timestamp, nonce):
        return "验证失败", 403

    if request.method == "GET":
        # 第一次验证时，微信会发 GET 请求
        echostr = request.args.get("echostr", "")
        return echostr

    # 处理用户消息（POST 请求）
    xml_data = ET.fromstring(request.data)
    msg_type = xml_data.find("MsgType").text
    to_user = xml_data.find("ToUserName").text
    from_user = xml_data.find("FromUserName").text

    if msg_type == "text":
        user_msg = xml_data.find("Content").text
        reply = ask_claude(user_msg)
        return make_reply_xml(from_user, to_user, reply)

    # 非文字消息暂不支持
    return make_reply_xml(from_user, to_user, "目前只支持文字消息哦～")


@app.route("/")
def index():
    return "Claude 微信机器人运行中 ✅"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
