import os

import discord
from dotenv import load_dotenv

from ticket import TicketPanelView


load_dotenv()

TOKEN = os.getenv(
    "DISCORD_BOT_TOKEN"
)

PANEL_CHANNEL_ID = 1541000137428570112


intents = discord.Intents.default()

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
            "❌ Panel channel not found."
        )

        await client.close()
        return

    embed = discord.Embed(
        title="🎫 Support Center",
        description=(
            "Need help? Select the category "
            "that best describes your request.\n\n"
            "A private ticket will be created "
            "for you and our staff team will "
            "be notified."
        ),
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="💰 Refunds",
        value="Refund-related requests",
        inline=True
    )

    embed.add_field(
        name="🐛 Bugs",
        value="Report technical issues",
        inline=True
    )

    embed.add_field(
        name="❓ Questions",
        value="Ask our support team",
        inline=True
    )

    embed.add_field(
        name="💬 General",
        value="General support",
        inline=True
    )

    embed.add_field(
        name="🤝 Partnership Requests",
        value="Business/partnership requests",
        inline=True
    )

    embed.add_field(
        name="🚨 Report User",
        value="Report a Discord user",
        inline=True
    )

    embed.add_field(
        name="🔨 Ban Appeals",
        value="Appeal a server ban",
        inline=True
    )

    embed.set_footer(
        text="Support Ticket System"
    )

    await channel.send(
        embed=embed,
        view=TicketPanelView()
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
