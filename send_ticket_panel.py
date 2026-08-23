# send_ticket_panel.py

import os

import discord
from dotenv import load_dotenv

from ticket import TicketView


load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")

PANEL_CHANNEL_ID = 1541000137428570112


intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(
    intents=intents
)


@client.event
async def on_ready():

    print(
        f"Logged in as {client.user}"
    )

    channel = client.get_channel(
        PANEL_CHANNEL_ID
    )

    if channel is None:

        print(
            "Could not find panel channel."
        )

        await client.close()
        return

    embed = discord.Embed(
        title="🎫 Support Center",
        description=(
            "Need help?\n\n"
            "Click the button below to create "
            "a private support ticket.\n\n"
            "Our support team will be notified "
            "when you create a ticket."
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text="Support Ticket System"
    )

    await channel.send(
        embed=embed,
        view=TicketView()
    )

    print(
        "Ticket panel sent successfully."
    )

    await client.close()


if not TOKEN:
    raise ValueError(
        "DISCORD_BOT_TOKEN missing from .env"
    )


client.run(TOKEN)