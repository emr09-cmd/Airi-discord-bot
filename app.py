# app.py
# .env:
# DISCORD_BOT_TOKEN=your_token_here

import os
import hashlib

from dotenv import load_dotenv
import discord

from ticket import setup_ticket_system


# ============================================================
# CONFIG
# ============================================================

load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")

GUILD_ID = 1540389537589633105
LOG_CHANNEL_ID = 1540674475635245218


# ============================================================
# BAD IMAGE HASHES
# ============================================================

BAD_HASHES = {
    "170319463df4b6d43f74949967d06e27ed0ec74ab877be790f05cee46899f7b3",
    "20e3840356e17e6974b5c98a4ea5ce7c6b05806b4e89be8b3861b51416f0da8c",
    "82144c80130cb019562f344503bb31197de7253896f8a059766336a781b0057d",
    "7bdec72c0e02c461254d100ffa8ae4459536fb1028e740475aa24d918d99d591",
    "066e050b5a93586d211458ec7fc6af17bbcca468c1d042c78d98cfa18810a396",
    "c0d47547a6bdf044670f9c1065099da88553a59d03be89c7b46a75ec8861e6d9",
    "874412421398a5ac289ee221072a5fcf4e890dde4fd8469cceeb4ece6057bdaa",
    "204b0503b603055f5c3c5827abface7d677541fd4403f80d36891c4b921dc469",
    "56b1887cf0d844ef4ec635b9d4883a955817f3e6ca06efbb8e10f4f7f9ff5fa8",
}


# ============================================================
# DISCORD CLIENT
# ============================================================

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)


# ============================================================
# TICKET SYSTEM
# ============================================================

# This connects app.py to ticket.py.
setup_ticket_system(client)


# ============================================================
# HASH FUNCTION
# ============================================================

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ============================================================
# BOT READY
# ============================================================

@client.event
async def on_ready():
    print(f"Bot is online as {client.user}")
    print(f"Connected to {len(client.guilds)} server(s)")


# ============================================================
# MESSAGE SCANNER
# ============================================================

@client.event
async def on_message(message):
    # Ignore the bot's own messages.
    if message.author == client.user:
        return

    # Ignore messages outside the configured server.
    if message.guild is None or message.guild.id != GUILD_ID:
        return

    # Ignore messages without attachments.
    if not message.attachments:
        return

    matched = False

    # Check every attachment.
    for att in message.attachments:
        try:
            data = await att.read()

            h = sha256_bytes(data)

            if h in BAD_HASHES:
                matched = True
                break

        except Exception as e:
            print(f"Could not read attachment: {e}")
            continue

    # Delete the message if a bad hash was found.
    if matched:

        try:
            await message.delete()
            print(
                f"Deleted scam image from "
                f"{message.author} ({message.author.id})"
            )

        except Exception as e:
            print(f"Could not delete message: {e}")

        # Send log message.
        try:
            ch = client.get_channel(LOG_CHANNEL_ID)

            if ch is None:
                ch = await client.fetch_channel(LOG_CHANNEL_ID)

            if ch is not None:
                await ch.send(
                    "Scam image has been deleted"
                )

        except Exception as e:
            print(f"Could not send log message: {e}")


# ============================================================
# START BOT
# ============================================================

if __name__ == "__main__":

    if not TOKEN:
        raise ValueError(
            "DISCORD_BOT_TOKEN missing from .env"
        )

    client.run(TOKEN)