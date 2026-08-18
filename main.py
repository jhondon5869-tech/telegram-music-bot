"""
Telegram Music Voice Chat Bot
==============================
Architecture:
  - Bot client (BOT_TOKEN)  -> receives /play, /stop commands in groups
  - Userbot (STRING_SESSION) -> joins voice chats and streams audio via PyTgCalls
  - yt-dlp                   -> searches YouTube and resolves stream URLs
"""

from __future__ import annotations

import asyncio
import logging
import sys

# Compatibility patch: py-tgcalls may import GroupcallForbidden from pyrogram
import pyrogram.errors as _pyrogram_errors

if not hasattr(_pyrogram_errors, "GroupcallForbidden"):

    class GroupcallForbidden(Exception):
        ID = "GROUPCALL_FORBIDDEN"
        MESSAGE = "The group call has forbidden the action."

    _pyrogram_errors.GroupcallForbidden = GroupcallForbidden
    if hasattr(_pyrogram_errors, "exceptions"):
        _pyrogram_errors.exceptions.GroupcallForbidden = GroupcallForbidden

from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from pyrogram.types import Message
from pytgcalls import PyTgCalls
from pytgcalls.exceptions import (
    NoActiveGroupCall,
    NotInCallError,
)
from pytgcalls.types import MediaStream
from pytgcalls.types.stream import AudioQuality, Flags

import config
from youtube import format_duration, search_youtube

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("music-bot")

userbot = Client(
    name="music_assistant",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    session_string=config.STRING_SESSION,
    in_memory=True,
)

bot = Client(
    name="music_bot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN,
    in_memory=True,
)

call_py = PyTgCalls(userbot)
_active_chats: set[int] = set()


async def has_active_voice_chat(chat_id: int) -> bool:
    """Return True if the group currently has a live voice/video chat."""
    try:
        chat = await userbot.get_chat(chat_id)
        if getattr(chat, "is_call_active", False):
            return True
        if getattr(chat, "call_active", False):
            return True
    except Exception as exc:
        log.debug("Could not read call state for %s: %s", chat_id, exc)
    return False


def build_audio_stream(youtube_url: str) -> MediaStream:
    """Build a PyTgCalls MediaStream for audio-only YouTube playback."""
    return MediaStream(
        youtube_url,
        audio_parameters=AudioQuality.HIGH,
        video_flags=Flags.IGNORE,
    )


async def safe_reply(message: Message, text: str, **kwargs) -> Message | None:
    """Reply to a message, respecting FloodWait."""
    try:
        return await message.reply_text(text, **kwargs)
    except FloodWait as exc:
        log.warning("FloodWait %ss — sleeping before reply", exc.value)
        await asyncio.sleep(exc.value)
        return await message.reply_text(text, **kwargs)


async def play_in_voice_chat(chat_id: int, youtube_url: str) -> None:
    """Join the group's voice chat (via userbot) and start streaming."""
    stream = build_audio_stream(youtube_url)
    await call_py.play(chat_id, stream)
    _active_chats.add(chat_id)


async def leave_voice_chat(chat_id: int) -> None:
    """Stop playback and leave the voice chat."""
    try:
        await call_py.leave_call(chat_id)
    except NotInCallError:
        pass
    finally:
        _active_chats.discard(chat_id)


@bot.on_message(filters.command(["start", "help"]) & filters.group)
async def help_handler(_: Client, message: Message) -> None:
    await safe_reply(
        message,
        "**Music Voice Chat Bot**\n\n"
        "Commands:\n"
        "• `/play <song name>` — Search YouTube and play in voice chat\n"
        "• `/stop` or `/end` — Stop music and leave voice chat\n"
        "• `/help` — Show this message\n\n"
        "**Setup checklist:**\n"
        "1. Add this bot to your group\n"
        "2. Add the assistant user account to the same group\n"
        "3. Start a voice chat in the group\n"
        "4. Send `/play never gonna give you up`",
    )


@bot.on_message(filters.command("play") & filters.group)
async def play_handler(_: Client, message: Message) -> None:
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await safe_reply(message, "Usage: `/play <song name or YouTube URL>`")
        return

    query = parts[1].strip()
    status = await safe_reply(message, f"Searching YouTube for: **{query}**…")

    track = await search_youtube(query)
    if not track:
        if status:
            await status.edit_text(f"Could not find anything for: **{query}**")
        return

    chat_id = message.chat.id

    if not await has_active_voice_chat(chat_id):
        if status:
            await status.edit_text(
                "No active voice chat in this group.\n\n"
                "Start a voice chat first, then send `/play` again."
            )
        return

    title = track["title"]
    duration = format_duration(track["duration"]) if track["duration"] else "?"
    url = track["url"]
    requester = message.from_user.mention if message.from_user else "Unknown"

    if status:
        await status.edit_text(
            f"**Now playing:** {title}\n"
            f"Duration: `{duration}`\n"
            f"Requested by: {requester}\n\n"
            f"Joining voice chat…"
        )

    try:
        await play_in_voice_chat(chat_id, url)
        if status:
            await status.edit_text(
                f"**Now playing:** {title}\n"
                f"Duration: `{duration}`\n"
                f"Requested by: {requester}"
            )

    except NoActiveGroupCall:
        if status:
            await status.edit_text(
                "No active voice chat found.\n\n"
                "Please start a voice chat in this group and try again."
            )

    except GroupCallForbidden:
        if status:
            await status.edit_text(
                "The assistant cannot join this voice chat.\n\n"
                "Make sure the assistant account is in the group and has "
                "**Manage Voice Chats** permission."
            )

    except AlreadyJoinedError:
        try:
            await leave_voice_chat(chat_id)
            await play_in_voice_chat(chat_id, url)
            if status:
                await status.edit_text(f"**Now playing:** {title}")
        except Exception as retry_exc:
            log.error("Retry after AlreadyJoinedError failed: %s", retry_exc)
            if status:
                await status.edit_text(f"Failed to start playback: {retry_exc}")

    except FloodWait as exc:
        if status:
            await status.edit_text(f"Rate limited. Try again in {exc.value} seconds.")
        await asyncio.sleep(exc.value)

    except Exception as exc:
        log.exception("Play failed in chat %s", chat_id)
        if status:
            await status.edit_text(
                f"Failed to play **{title}**.\n\n"
                f"Error: `{exc}`\n\n"
                "Check that FFmpeg is installed and the assistant is in the group."
            )


@bot.on_message(filters.command(["stop", "end"]) & filters.group)
async def stop_handler(_: Client, message: Message) -> None:
    chat_id = message.chat.id

    if chat_id not in _active_chats:
        try:
            await leave_voice_chat(chat_id)
        except Exception:
            pass
        await safe_reply(message, "Nothing is playing right now.")
        return

    try:
        await leave_voice_chat(chat_id)
        await safe_reply(message, "Stopped playback and left the voice chat.")
    except NotInCallError:
        _active_chats.discard(chat_id)
        await safe_reply(message, "Already left the voice chat.")
    except Exception as exc:
        log.exception("Stop failed in chat %s", chat_id)
        await safe_reply(message, f"Error while stopping: `{exc}`")


async def main() -> None:
    log.info("Starting Music Voice Chat Bot…")

    await userbot.start()
    me = await userbot.get_me()
    log.info("Assistant (userbot) started as: %s (@%s)", me.first_name, me.username)

    await bot.start()
    bot_me = await bot.get_me()
    log.info("Bot started as: @%s", bot_me.username)

    await call_py.start()
    log.info("PyTgCalls engine started")

    log.info("━" * 50)
    log.info("Bot is online! Add it to a group and use /play")
    log.info("Press Ctrl+C to stop.")
    log.info("━" * 50)

    stop_event = asyncio.Event()
    try:
        await stop_event.wait()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        log.info("Shutting down…")
        for chat_id in list(_active_chats):
            try:
                await leave_voice_chat(chat_id)
            except Exception:
                pass
        await call_py.stop()
        await bot.stop()
        await userbot.stop()
        log.info("Shutdown complete.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
