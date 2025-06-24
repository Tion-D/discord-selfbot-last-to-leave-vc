import os
import threading
import asyncio
import json
import ssl
import certifi
import requests
import websockets
from flask import Flask, request

app = Flask(__name__)

index_html = """
<!doctype html>
<html>
<head><title>Discord VC Controller</title></head>
<body>
  <h1>Discord Voice Channel Controller</h1>
  <form method="POST" action="/action">
    <label for="guild_id">Guild ID:</label><br>
    <input type="text" id="guild_id" name="guild_id"><br><br>

    <label for="voice_channel_id">Voice Channel ID:</label><br>
    <input type="text" id="voice_channel_id" name="voice_channel_id"><br><br>

    <label for="afk_channel_id">AFK Check Channel ID (optional):</label><br>
    <input type="text" id="afk_channel_id" name="afk_channel_id"><br><br>

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
    global discord_ws, bot_loop, afk_channel_id_global

    guild_id        = request.form.get("guild_id")
    voice_channel_id = request.form.get("voice_channel_id")
    afk_channel_id   = request.form.get("afk_channel_id")
    action_type      = request.form.get("action")

    afk_channel_id_global = afk_channel_id or None

    payload = {
        "op": 4,
        "d": {
            "guild_id": guild_id,
            "channel_id": voice_channel_id if action_type == "join" else None,
            "self_mute": False,
            "self_deaf": False
        }
    }

    if discord_ws is None or bot_loop is None:
        return "Discord bot is not connected yet."

    try:
        future = asyncio.run_coroutine_threadsafe(discord_ws.send(json.dumps(payload)), bot_loop)
        future.result(timeout=5)
        return f"{action_type.capitalize()} executed. AFK-check listening {'enabled' if afk_channel_id_global else 'disabled'}."
    except Exception as e:
        return f"Error sending command: {e}"


discord_ws = None
bot_loop   = None

CURRENT_TOKEN = os.environ.get("DISCORD_TOKEN")
if not CURRENT_TOKEN:
    print("Error: DISCORD_TOKEN environment variable not set.")
    exit(1)

GATEWAY_URL = "wss://gateway.discord.gg/?v=10&encoding=json"

INTENTS = 1 | 512 | 1024

async def connect_to_gateway():
    global discord_ws, afk_channel_id_global
    ssl_context = ssl.create_default_context(cafile=certifi.where())

    while True:
        try:
            async with websockets.connect(GATEWAY_URL, ssl=ssl_context, max_size=None) as ws:
                discord_ws = ws

                hello = json.loads(await ws.recv())
                hb_interval = hello["d"]["heartbeat_interval"] / 1000
                print(f"[GATEWAY] HELLO – heartbeat every {hb_interval}s")

                await ws.send(json.dumps({
                    "op": 2,
                    "d": {
                        "token": CURRENT_TOKEN,
                        "intents": INTENTS,
                        "properties": {"$os": "windows", "$browser": "custom", "$device": "custom"},
                        "presence": {"status": "online", "since": None, "activities": [], "afk": False},
                        "compress": False
                    }
                }))
                print("[GATEWAY] IDENTIFY sent.")

                async def heartbeat():
                    while True:
                        await asyncio.sleep(hb_interval)
                        await ws.send(json.dumps({"op": 1, "d": None}))
                asyncio.create_task(heartbeat())

                while True:
                    raw = await ws.recv()
                    data = json.loads(raw)

                    if data.get("t") == "MESSAGE_REACTION_ADD" and afk_channel_id_global:
                        d = data["d"]
                        if d["channel_id"] == afk_channel_id_global and d["emoji"]["name"] == "✅":
                            msg_id = d["message_id"]
                            emoji  = "%E2%9C%85"
                            url = f"https://discord.com/api/v10/channels/{afk_channel_id_global}/messages/{msg_id}/reactions/{emoji}/@me"
                            headers = {
                                "Authorization": f"Bot {CURRENT_TOKEN}",
                                "Content-Type": "application/json"
                            }
                            requests.put(url, headers=headers)

        except websockets.ConnectionClosed as cc:
            print(f"Gateway closed: {cc}. Reconnecting in 5 s…")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"Unexpected error: {e}. Reconnecting in 5 s…")
            await asyncio.sleep(5)


def run_bot():
    global bot_loop
    bot_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(bot_loop)
    bot_loop.create_task(connect_to_gateway())
    bot_loop.run_forever()


if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 3000))
    print(f"Flask running on :{port}")
    app.run(host="0.0.0.0", port=port)
