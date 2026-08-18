# Telegram Music Voice Chat Bot

A Python bot that plays YouTube music in Telegram group voice chats using **Pyrogram**, **PyTgCalls**, and **yt-dlp**.

## How it works

```
User sends /play  →  Bot (Pyrogram)  →  yt-dlp searches YouTube
                                              │
                                              ▼
                                    PyTgCalls + Userbot (String Session)
                                              │
                                              ▼
                              Assistant joins VC and streams audio via FFmpeg
```

| Component | Role |
|-----------|------|
| **Bot** (`BOT_TOKEN`) | Receives `/play`, `/stop` commands in groups |
| **Assistant** (`STRING_SESSION`) | User account that joins voice chats and streams audio |
| **PyTgCalls** | Handles WebRTC voice chat streaming |
| **yt-dlp** | Searches YouTube and resolves audio streams |
| **FFmpeg** | Transcodes audio for Telegram voice chat (required by PyTgCalls) |

## Prerequisites

1. **Python 3.10+** — [python.org/downloads](https://www.python.org/downloads/)
2. **FFmpeg** — must be on your system `PATH`
3. **Telegram credentials** — from [my.telegram.org](https://my.telegram.org/apps)
4. **A bot token** — from [@BotFather](https://t.me/BotFather)
5. **A user account** — the assistant that joins voice chats (cannot be a bot account)

## Step 1 — Install FFmpeg

### Windows

**Option A — winget (recommended):**
```powershell
winget install Gyan.FFmpeg
```

**Option B — Chocolatey:**
```powershell
choco install ffmpeg
```

**Option C — Manual:**
1. Download from [ffmpeg.org/download.html](https://ffmpeg.org/download.html)
2. Extract and add the `bin` folder to your system PATH

Verify:
```powershell
ffmpeg -version
ffprobe -version
```

## Step 2 — Set up the project in Cursor

Open the integrated terminal in Cursor (`Ctrl + `` ` ``) and run:

```powershell
cd telegram-music-bot

# Create a virtual environment
python -m venv .venv

# Activate it (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

## Step 3 — Configure credentials

Your credentials are already in `.env`. If you need to regenerate:

```powershell
copy .env.example .env
# Edit .env with your API_ID, API_HASH, BOT_TOKEN, STRING_SESSION
```

| Variable | Description |
|----------|-------------|
| `API_ID` | From [my.telegram.org/apps](https://my.telegram.org/apps) |
| `API_HASH` | Same page as API_ID |
| `BOT_TOKEN` | From [@BotFather](https://t.me/BotFather) |
| `STRING_SESSION` | Pyrogram session for the assistant user account |

To generate a new string session:
```powershell
python generate_session.py
```

## Step 4 — Prepare your Telegram group

1. **Add the bot** to your group (via @BotFather invite link).
2. **Add the assistant user account** (the account used for `STRING_SESSION`) to the same group.
3. Give the assistant **Manage Voice Chats** permission (Admin → Permissions).
4. **Start a voice chat** in the group before using `/play`.

## Step 5 — Run the bot

```powershell
cd telegram-music-bot
.\.venv\Scripts\Activate.ps1
python main.py
```

You should see:
```
Assistant (userbot) started as: YourName (@username)
Bot started as: @YourBotName
PyTgCalls engine started
Bot is online! Add it to a group and use /play
```

## Commands

| Command | Description |
|---------|-------------|
| `/play <song name>` | Search YouTube and play in the active voice chat |
| `/play <YouTube URL>` | Play a specific YouTube link |
| `/stop` or `/end` | Stop playback and leave the voice chat |
| `/help` | Show command list |

**Example:**
```
/play never gonna give you up
/play https://www.youtube.com/watch?v=dQw4w9WgXcQ
/stop
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `ffmpeg not found` | Install FFmpeg and restart the terminal |
| `No active voice chat` | Start a voice chat in the group first |
| `Assistant cannot join` | Add assistant to group with **Manage Voice Chats** permission |
| `No module named 'pytgcalls'` | Run `pip install py-tgcalls[pyrogram]` |
| `SESSION_STRING invalid` | Regenerate with `python generate_session.py` |
| `FloodWait` errors | Wait the specified seconds; avoid spamming commands |
| Bot responds but no audio | Ensure FFmpeg works: `ffmpeg -version` |

## Project structure

```
telegram-music-bot/
├── main.py              # Core bot logic and command handlers
├── config.py            # Loads credentials from .env
├── youtube.py           # YouTube search via yt-dlp
├── generate_session.py    # Helper to create STRING_SESSION
├── requirements.txt     # Python dependencies
├── .env                 # Your credentials (never commit this)
├── .env.example         # Template for credentials
└── README.md            # This file
```

## Security notes

- **Never commit `.env`** to git — it contains secrets.
- If credentials were shared publicly, regenerate your bot token via @BotFather and create a new string session.
- The assistant account is a real Telegram user — treat its session string like a password.

## License

MIT — use freely for personal projects.
