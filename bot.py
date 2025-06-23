import os
import threading
import asyncio
import json
import ssl
import certifi
import requests

import websockets
from flask import Flask, request, render_template_string

app = Flask(__name__)

index_html = """
<!doctype html>
<html>
<head>
  <title>Discord VC Controller</title>
</head>
<body>
  <h1>Discord Voice Channel Controller</h1>
  <form method="POST" action="/action">
    <label for="guild_id">Guild ID:</label><br>
    <input type="text" id="guild_id" name="guild_id" placeholder="Enter Guild ID"><br><br>

    <label for="voice_channel_id">Voice Channel ID:</label><br>
    <input type="text" id="voice_channel_id" name="voice_channel_id" placeholder="Enter Voice Channel ID"><br><br>

    <label for="afk_channel_id">AFK Check Channel ID (optional):</label><br>
    <input type="text" id="afk_channel_id" name="afk_channel_id" placeholder="Enter AFK Check Channel ID"><br><br>

    <button type="submit" name="action" value="join">Join VC</button>
    <button type="submit" name="action" value="leave">Leave VC</button>
  </form>
</body>
</html>
"""

@app.route("/")
def home():
    return index_html

@app.route("/action", methods=["POST"])
def action():
    global discord_ws, bot_loop

    guild_id = request.form.get("guild_id")
    voice_channel_id = request.form.get("voice_channel_id")
    afk_channel_id = request.form.get("afk_channel_id")
    action_type = request.form.get("action")

    if action_type == "join":
        payload = {"op": 4, "d": {"guild_id": guild_id, "channel_id": voice_channel_id, "self_mute": False, "self_deaf": False}}
    elif action_type == "leave":
        payload = {"op": 4, "d": {"guild_id": guild_id, "channel_id": None, "self_mute": False, "self_deaf": False}}
    else:
        return "Invalid action."

    if discord_ws is None or bot_loop is None:
        return "Discord bot is not connected yet."

    try:
        future = asyncio.run_coroutine_threadsafe(discord_ws.send(json.dumps(payload)), bot_loop)
        future.result(timeout=5)

        if action_type == "join" and afk_channel_id:
            headers = {"Authorization": f"Bot {CURRENT_TOKEN}", "Content-Type": "application/json"}
            msg_url = f"https://discord.com/api/v10/channels/{afk_channel_id}/messages?limit=1"
            resp = requests.get(msg_url, headers=headers)
            if resp.ok and isinstance(resp.json(), list) and resp.json():
                last_msg = resp.json()[0]
                message_id = last_msg.get("id")
                emoji = "%E2%9C%85"
                react_url = f"https://discord.com/api/v10/channels/{afk_channel_id}/messages/{message_id}/reactions/{emoji}/@me"
                react = requests.put(react_url, headers=headers)
                if not react.ok:
                    return f"Joined VC, but failed to react: {react.status_code} {react.text}"
            else:
                return f"Joined VC, but failed to fetch AFK messages: {resp.status_code} {resp.text}"

        return f"Action '{action_type}' executed."
    except Exception as e:
        return f"Error sending command: {e}"


# ------------ Gateway Connection & Bot Loop ------------

discord_ws = None
bot_loop = None
CURRENT_TOKEN = os.environ.get("TOKEN", "YOUR_DISCORD_TOKEN")

GATEWAY_URL = "wss://gateway.discord.gg/?v=10&encoding=json"

async def connect_to_gateway():
    global discord_ws
    ssl_context = ssl.create_default_context(cafile=certifi.where())

    while True:
        try:
            async with websockets.connect(GATEWAY_URL, ssl=ssl_context, max_size=None) as ws:
                discord_ws = ws
                hello_payload = await ws.recv()
                hello_data = json.loads(hello_payload)
                heartbeat_interval = hello_data["d"]["heartbeat_interval"]
                print(f"[GATEWAY] HELLO received. Heartbeat interval: {heartbeat_interval}ms")

                identify_payload = {
                    "op": 2,
                    "d": {
                        "token": CURRENT_TOKEN,
                        "intents": 513,
                        "properties": {"$os": "windows", "$browser": "chrome", "$device": "pc"},
                        "presence": {"status": "online", "since": None, "activities": [], "afk": False},
                        "compress": False,
                    }
                }
                await ws.send(json.dumps(identify_payload))
                print("[GATEWAY] Sent Identify payload.")

                async def heartbeat():
                    while True:
                        await asyncio.sleep(heartbeat_interval / 1000)
                        await ws.send(json.dumps({"op": 1, "d": None}))
                        print("[GATEWAY] Heartbeat sent.")
                asyncio.create_task(heartbeat())

                while True:
                    message = await ws.recv()
                    # handle other events if needed
        except websockets.ConnectionClosed as cc:
            print(f"Gateway connection closed: {cc}. Reconnecting in 5s...")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"Unexpected error: {e}. Reconnecting in 5s...")
            await asyncio.sleep(5)


def run_bot():
    global bot_loop
    bot_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(bot_loop)
    bot_loop.create_task(connect_to_gateway())
    bot_loop.run_forever()

if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

    port = int(os.environ.get("PORT", 3000))
    print(f"Starting Flask on port {port}")
    app.run(host="0.0.0.0", port=port)
