# Discord-SelfBot-Join-Leave-VC

```markdown
# Discord Voice Channel Controller Bot

> **Disclaimer:**  
> This project is provided for educational purposes only.  
> **WARNING:** Using user tokens (selfbots) is against Discord’s Terms of Service and may lead to account termination. It is recommended to use a **bot token** from the [Discord Developer Portal](https://discord.com/developers/applications).

## Overview

This project is a simple Discord bot that connects to Discord’s Gateway via websockets and lets you control its voice channel connection through a web interface built with Flask. With the web interface, you can:

- **Enter a Discord token, Guild ID, and Voice Channel ID.**
- **Click a button to make the bot join or leave a voice channel.**

The bot is designed to run continuously and reconnect automatically if the connection is lost. It also allows you to update the token on the fly via the web form.

## Features

- **Web Interface:**  
  A simple HTML form that takes:
  - Guild ID
  - Voice Channel ID

  And provides two buttons:
  - **Join VC**
  - **Leave VC**

- **Background Discord Bot:**  
  Uses asynchronous websockets to connect to Discord’s Gateway, sending Identify and heartbeat payloads.  
  Automatically reconnects on disconnect.

- **Token Management:**  
  Uses the env, Set your environment variable to DISCORD_TOKEN

## Requirements

- Python 3.10+
- [websockets](https://pypi.org/project/websockets/)
- [httpx](https://pypi.org/project/httpx/)
- [certifi](https://pypi.org/project/certifi/)
- [colorama](https://pypi.org/project/colorama/)
- [Flask](https://pypi.org/project/Flask/)
```
## Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/Tion-D/Discord-SelfBot-Join-Leave-VC.git
   cd Discord-SelfBot-Join-Leave-VC
   ```

2. **Install dependencies using pip and the provided `requirements.txt`:**

   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. **Run the Bot:**
  - Put your discord token in env, set your environment variable to DISCORD_TOKEN
   ```bash
   python bot.py
   ```

2. **Control via Web Interface:**

   - Open your browser and navigate to the server URL (e.g., `http://localhost:3000`).
   - Enter the **Guild ID**, and **Voice Channel ID**.
   - Click **Join VC** to have the bot join the voice channel or **Leave VC** to disconnect.

## Deployment

This project is suitable for deployment on platforms like **Railway**, **Render**, or **Heroku**.  

### Example Start Command:
```bash
python bot.py
```

## Troubleshooting

- **Authentication Failed (4004):**  
  Ensure that you are using a valid token. Make sure to remove the "".
- **Connection Issues:**  
  The bot will attempt to reconnect automatically if the connection is lost.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request with your improvements.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
```
