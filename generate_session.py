"""Generate a Pyrogram STRING_SESSION for the assistant userbot.

Run once:
    python generate_session.py

Follow the prompts to log in with the Telegram account that will join voice chats.
"""

import asyncio

from pyrogram import Client

from config import API_ID, API_HASH


async def main() -> None:
    print("=" * 55)
    print("  Pyrogram String Session Generator")
    print("=" * 55)
    print()
    print("Log in with the USER account that will join voice chats.")
    print("(This is NOT the bot account from @BotFather.)")
    print()

    async with Client(
        "session_generator",
        api_id=API_ID,
        api_hash=API_HASH,
        in_memory=True,
    ) as app:
        session_string = await app.export_session_string()
        print()
        print("Your STRING_SESSION (copy this into .env):")
        print("-" * 55)
        print(session_string)
        print("-" * 55)
        print()
        print("Add it to your .env file as STRING_SESSION=...")


if __name__ == "__main__":
    asyncio.run(main())
