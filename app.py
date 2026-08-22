# Create a file named ".env" in the same folder with this line inside:
# DISCORD_BOT_TOKEN=your_token_here

import os
import discord
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")

intents = discord.Intents.default()
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"Bot is online as {client.user}")

client.run(TOKEN)