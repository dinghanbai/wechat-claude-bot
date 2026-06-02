import os
import hashlib
import xml.etree.ElementTree as ET
from flask import Flask, request
from openai import OpenAI
import time

app = Flask(__name__)

WECHAT_TOKEN = os.environ.get("WECHAT_TOKEN", "mytoken123")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)

def check_signature(signature, timestamp, nonce):
    tmp_list = sorted([WECHAT_TOKEN, timestamp, nonce])
    tmp_str = "".join(tmp_list)
    sha1 = hashlib.sha1(tmp_str.encode("utf-8")).hexdigest()
    return sha1 == signature

def ask_deepseek(user_message):
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": user_message}],
            max_tokens=1000,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"抱歉，出现了错误：{str(e)}"

def make_reply_xml(to_user, from_user, content):
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
    if not check_signature(signature, timestamp, nonce):
        return "验证失败", 403
    if request.method == "GET":
        echostr = request.args.get("echostr", "")
        return echostr
    xml_data = ET.fromstring(request.data)
    msg_type = xml_data.find("MsgType").text
    to_user = xml_data.find("ToUserName").text
    from_user = xml_data.find("FromUserName").text
    if msg_type == "text":
        user_msg = xml_data.find("Content").text
        reply = ask_deepseek(user_msg)
        return make_reply_xml(from_user, to_user, reply)
    return make_reply_xml(from_user, to_user, "目前只支持文字消息哦～")

@app.route("/")
def index():
    return "微信机器人运行中 ✅"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
