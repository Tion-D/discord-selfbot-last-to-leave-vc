import os
import json
import ssl
import threading
import asyncio
from typing import Optional

import certifi
import requests
import websockets
from flask import Flask, request

app = Flask(__name__)

INDEX_HTML = """
<!doctype html>
<html>
<head><title>Discord VC Controller</title></head>
<body>
  <h1>Discord Voice Channel Controller</h1>
  <form method="POST" action="/action">
    <label>Guild&nbsp;ID:</label><br>
    <input name="guild_id"><br><br>

    <label>Voice&nbsp;Channel&nbsp;ID:</label><br>
    <input name="voice_channel_id"><br><br>

    <label>AFK&nbsp;Check&nbsp;Channel&nbsp;ID&nbsp;(optional):</label><br>
    <input name="afk_channel_id"><br><br>

    <button name="action" value="join">Join&nbsp;VC</button>
    <button name="action" value="leave">Leave&nbsp;VC</button>
  </form>
</body>
</html>
"""


@app.route("/")
def home() -> str:
    return INDEX_HTML


@app.route("/action", methods=["POST"])
def action() -> str:
    global discord_ws, bot_loop, afk_channel_id_global

    guild_id = request.form.get("guild_id")
    voice_channel_id = request.form.get("voice_channel_id")
    afk_channel_id = request.form.get("afk_channel_id")
    action_type = request.form.get("action")

    afk_channel_id_global = afk_channel_id or None

    payload = {
        "op": 4,
        "d": {
            "guild_id": guild_id,
            "channel_id": voice_channel_id if action_type == "join" else None,
            "self_mute": False,
            "self_deaf": False,
        },
    }

    if discord_ws is None or bot_loop is None:
        return "Discord bot is not connected yet."

    try:
        fut = asyncio.run_coroutine_threadsafe(
            discord_ws.send(json.dumps(payload)), bot_loop
        )
        fut.result(timeout=5)
        return (
            f"{action_type.capitalize()} executed. "
            f"AFK-check listening "
            f"{'enabled' if afk_channel_id_global else 'disabled'}."
        )
    except Exception as exc:
        return f"Error sending command: {exc}"


CURRENT_TOKEN = os.getenv("DISCORD_TOKEN")
if not CURRENT_TOKEN:
    raise SystemExit("Error: DISCORD_TOKEN environment variable not set.")

GATEWAY_URL = "wss://gateway.discord.gg/?v=10&encoding=json"
INTENTS = 1 | 512 | 1024

discord_ws: Optional[websockets.WebSocketClientProtocol] = None
bot_loop: Optional[asyncio.AbstractEventLoop] = None
afk_channel_id_global: Optional[str] = None


async def heartbeat(ws, interval, seq_fn):
    try:
        while True:
            await asyncio.sleep(interval)
            await ws.send(json.dumps({"op": 1, "d": seq_fn()}))
    except websockets.ConnectionClosed:
        pass


async def connect_to_gateway():
    global discord_ws, afk_channel_id_global
    ssl_ctx = ssl.create_default_context(cafile=certifi.where())

    while True:
        discord_ws = None
        try:
            async with websockets.connect(
                GATEWAY_URL, ssl=ssl_ctx, max_size=None
            ) as ws:
                discord_ws = ws
                seq = None

                hello = json.loads(await ws.recv())
                hb_interval = hello["d"]["heartbeat_interval"] / 1000
                print(f"[GW] HELLO – heartbeat every {hb_interval}s")

                await ws.send(
                    json.dumps(
                        {
                            "op": 2,
                            "d": {
                                "token": CURRENT_TOKEN,
                                "intents": INTENTS,
                                "properties": {
                                    "$os": "windows",
                                    "$browser": "custom",
                                    "$device": "custom",
                                },
                                "presence": {
                                    "status": "online",
                                    "since": None,
                                    "activities": [],
                                    "afk": False,
                                },
                                "compress": False,
                            },
                        }
                    )
                )
                print("[GW] IDENTIFY sent")

                hb_task = asyncio.create_task(
                    heartbeat(ws, hb_interval, lambda: seq)
                )

                async for raw in ws:
                    data = json.loads(raw)
                    if (s := data.get("s")) is not None:
                        seq = s

                    if (
                        data.get("t") == "MESSAGE_REACTION_ADD"
                        and afk_channel_id_global
                    ):
                        d = data["d"]
                        if (
                            d["channel_id"] == afk_channel_id_global
                            and d["emoji"]["name"] == "✅"
                        ):
                            msg_id = d["message_id"]
                            emoji = "%E2%9C%85"
                            url = (
                                "https://discord.com/api/v10/channels/"
                                f"{afk_channel_id_global}/messages/{msg_id}/"
                                f"reactions/{emoji}/@me"
                            )
                            hdrs = {"Authorization": f"Bot {CURRENT_TOKEN}"}
                            requests.put(url, headers=hdrs, timeout=10)

                hb_task.cancel()

        except Exception as exc:
            print(f"[GW] error: {exc!r} – reconnecting in 5 s")
            await asyncio.sleep(5)


def run_bot():
    global bot_loop
    bot_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(bot_loop)
    bot_loop.create_task(connect_to_gateway())
    bot_loop.run_forever()


# ──────────────────────────── main ──────────────────────────── #

if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    flask_port = int(os.getenv("PORT", 3000))
    print(f"Flask listening on :{flask_port}")
    app.run(host="0.0.0.0", port=flask_port)
