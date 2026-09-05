from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Any
from urllib.request import Request, urlopen

import discord
from discord.ext import tasks

STATUS_CHANNEL_ID = 1545678997197946910
SERVER_ADDRESS = "104.243.39.147:25694"
API_URL = f"https://api.mcsrvstat.us/3/{SERVER_ADDRESS}"
MESSAGE_ID_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mc_status_message_id.txt")


def load_message_id() -> int | None:
    try:
        with open(MESSAGE_ID_FILE, "r", encoding="utf-8") as file:
            value = file.read().strip()
        return int(value) if value else None
    except (FileNotFoundError, ValueError):
        return None


def save_message_id(message_id: int) -> None:
    with open(MESSAGE_ID_FILE, "w", encoding="utf-8") as file:
        file.write(str(message_id))


def fetch_server_status() -> dict[str, Any] | None:
    request = Request(API_URL, headers={"User-Agent": "DiscordBotDashboard/1.0"})
    try:
        with urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as error:
        print(f"[MC STATUS] API request failed: {error}")
        return None


def build_status_embed(data: dict[str, Any] | None) -> discord.Embed:
    now = datetime.now(timezone.utc)
    if data is None:
        embed = discord.Embed(
            title="Minecraft Server Status",
            description="Unable to reach the status API.",
            color=discord.Color.dark_grey(),
            timestamp=now,
        )
        embed.add_field(name="Server", value=f"`{SERVER_ADDRESS}`", inline=False)
        embed.set_footer(text="Status updates automatically")
        return embed

    if not data.get("online", False):
        embed = discord.Embed(
            title="🔴 Minecraft Server Offline",
            description="The server is offline or unreachable.",
            color=discord.Color.red(),
            timestamp=now,
        )
        embed.add_field(name="Server", value=f"`{SERVER_ADDRESS}`", inline=False)
        embed.set_footer(text="Status updates automatically")
        return embed

    players = data.get("players") or {}
    motd = "\n".join((data.get("motd") or {}).get("clean") or []).strip() or "-"
    version = data.get("version") or (data.get("protocol") or {}).get("name") or "Unknown"
    player_names = [player.get("name", "?") for player in players.get("list") or []]
    players_text = ", ".join(f"`{name}`" for name in player_names[:20])
    if len(player_names) > 20:
        players_text += f" +{len(player_names) - 20} more"
    if not players_text:
        players_text = "No players online" if players.get("online", 0) == 0 else f"{players.get('online', 0)} player(s) online"

    embed = discord.Embed(
        title="🟢 Minecraft Server Online",
        description=motd[:1024],
        color=discord.Color.green(),
        timestamp=now,
    )
    embed.add_field(name="Server", value=f"`{SERVER_ADDRESS}`", inline=False)
    embed.add_field(name="Players", value=f"**{players.get('online', 0)}** / **{players.get('max', 0)}**", inline=True)
    embed.add_field(name="Version", value=f"`{version}`", inline=True)
    embed.add_field(name="Software", value=f"`{data.get('software') or 'Unknown'}`", inline=True)
    embed.add_field(name="Online Players", value=players_text[:1024], inline=False)
    embed.set_footer(text="Status updates automatically")
    return embed


async def update_status_message(client: discord.Client) -> None:
    channel = client.get_channel(STATUS_CHANNEL_ID)
    if channel is None:
        try:
            channel = await client.fetch_channel(STATUS_CHANNEL_ID)
        except (discord.Forbidden, discord.HTTPException) as error:
            print(f"[MC STATUS] Cannot access channel {STATUS_CHANNEL_ID}: {error}")
            return

    if not isinstance(channel, discord.TextChannel):
        print(f"[MC STATUS] Channel {STATUS_CHANNEL_ID} is not a text channel")
        return

    data = await asyncio.to_thread(fetch_server_status)
    embed = build_status_embed(data)
    message_id = load_message_id()

    if message_id:
        try:
            message = await channel.fetch_message(message_id)
            await message.edit(embed=embed)
            print(f"[MC STATUS] Updated message {message_id}")
            return
        except discord.NotFound:
            print(f"[MC STATUS] Saved message {message_id} was not found; sending a replacement")
        except discord.Forbidden as error:
            print(f"[MC STATUS] Missing permission to edit message: {error}")
            return
        except discord.HTTPException as error:
            print(f"[MC STATUS] Could not edit message: {error}")
            return

    try:
        message = await channel.send(embed=embed)
        save_message_id(message.id)
        print(f"[MC STATUS] Sent message {message.id}")
    except discord.Forbidden as error:
        print(f"[MC STATUS] Missing permission to send message: {error}")
    except discord.HTTPException as error:
        print(f"[MC STATUS] Could not send message: {error}")


async def resend_status_message(client: discord.Client) -> None:
    """Delete the saved status message and send a fresh one."""
    channel = client.get_channel(STATUS_CHANNEL_ID)
    if channel is None:
        channel = await client.fetch_channel(STATUS_CHANNEL_ID)
    if not isinstance(channel, discord.TextChannel):
        raise RuntimeError(f"Channel {STATUS_CHANNEL_ID} is not a text channel")

    old_message_id = load_message_id()
    if old_message_id:
        try:
            old_message = await channel.fetch_message(old_message_id)
            await old_message.delete(reason="Minecraft status message replaced")
        except discord.NotFound:
            pass

    data = await asyncio.to_thread(fetch_server_status)
    message = await channel.send(embed=build_status_embed(data))
    save_message_id(message.id)
    print(f"[MC STATUS] Replaced message with {message.id}")


@tasks.loop(minutes=2)
async def status_loop(client: discord.Client) -> None:
    await update_status_message(client)


def start_status_task(client: discord.Client) -> None:
    if not status_loop.is_running():
        status_loop.start(client)
        print("[MC STATUS] Status loop started")
