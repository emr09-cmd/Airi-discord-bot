# mc_status.py
# Minecraft server status – posts once, then edits the same message every 2 minutes.

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any

import discord
from discord.ext import tasks
import requests


# ============================================================
# CONFIG
# ============================================================

STATUS_CHANNEL_ID = 1541156601497522226
SERVER_ADDRESS = "testemr09mc.falixsrv.me"
API_URL = f"https://api.mcsrvstat.us/3/{SERVER_ADDRESS}"

# File where the status message ID is saved (survives restarts)
MESSAGE_ID_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "mc_status_message_id.txt"
)


# ============================================================
# MESSAGE ID PERSISTENCE
# ============================================================

def load_message_id() -> Optional[int]:
    try:
        if not os.path.exists(MESSAGE_ID_FILE):
            return None
        with open(MESSAGE_ID_FILE, "r", encoding="utf-8") as f:
            raw = f.read().strip()
        if not raw:
            return None
        return int(raw)
    except Exception as e:
        print(f"[MC STATUS] Failed to load message ID: {e}")
        return None


def save_message_id(message_id: int) -> None:
    try:
        with open(MESSAGE_ID_FILE, "w", encoding="utf-8") as f:
            f.write(str(message_id))
        print(f"[MC STATUS] Saved message ID: {message_id}")
    except Exception as e:
        print(f"[MC STATUS] Failed to save message ID: {e}")


# ============================================================
# API FETCH
# ============================================================

def fetch_server_status() -> Optional[Dict[str, Any]]:
    """Fetch status from mcsrvstat.us. Returns dict or None on error."""
    try:
        resp = requests.get(API_URL, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data
    except requests.Timeout:
        print("[MC STATUS] API request timed out")
        return None
    except requests.RequestException as e:
        print(f"[MC STATUS] API request failed: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"[MC STATUS] Invalid JSON from API: {e}")
        return None
    except Exception as e:
        print(f"[MC STATUS] Unexpected fetch error: {e}")
        return None


# ============================================================
# EMBED BUILDER
# ============================================================

def build_status_embed(data: Optional[Dict[str, Any]]) -> discord.Embed:
    now = datetime.now(timezone.utc)

    if data is None:
        embed = discord.Embed(
            title="Minecraft Server Status",
            description="❌ Could not reach the status API.",
            color=discord.Color.dark_grey(),
            timestamp=now
        )
        embed.add_field(name="Server", value=f"`{SERVER_ADDRESS}`", inline=False)
        embed.set_footer(text="Updates every 2 minutes")
        return embed

    online = data.get("online", False)

    if online:
        players = data.get("players", {})
        online_count = players.get("online", 0)
        max_count = players.get("max", 0)
        version = data.get("version") or data.get("protocol", {}).get("name", "Unknown")
        software = data.get("software", "Unknown")
        motd_list = data.get("motd", {}).get("clean", [])
        motd = "\n".join(motd_list).strip() if motd_list else "—"

        player_list = players.get("list") or []
        if player_list:
            names = [p.get("name", "?") for p in player_list[:15]]
            players_text = ", ".join(f"`{n}`" for n in names)
            if len(player_list) > 15:
                players_text += f" +{len(player_list) - 15} more"
        else:
            players_text = "No players online" if online_count == 0 else f"{online_count} player(s)"

        embed = discord.Embed(
            title="🟢 Server Online",
            color=discord.Color.green(),
            timestamp=now
        )
        embed.add_field(name="Address", value=f"`{SERVER_ADDRESS}`", inline=False)
        embed.add_field(name="Players", value=f"**{online_count}** / **{max_count}**", inline=True)
        embed.add_field(name="Version", value=f"`{version}`", inline=True)
        embed.add_field(name="Software", value=f"`{software}`", inline=True)
        embed.add_field(name="MOTD", value=motd[:200] or "—", inline=False)
        embed.add_field(name="Online Players", value=players_text[:1024], inline=False)
    else:
        embed = discord.Embed(
            title="🔴 Server Offline",
            description="The server is currently offline or unreachable.",
            color=discord.Color.red(),
            timestamp=now
        )
        embed.add_field(name="Address", value=f"`{SERVER_ADDRESS}`", inline=False)

    embed.set_footer(text="Updates every 2 minutes • mcsrvstat.us")
    return embed


# ============================================================
# UPDATE LOGIC
# ============================================================

async def update_status_message(client: discord.Client) -> None:
    """Fetch status and either edit the saved message or send a new one."""
    channel = client.get_channel(STATUS_CHANNEL_ID)
    if channel is None:
        try:
            channel = await client.fetch_channel(STATUS_CHANNEL_ID)
        except Exception as e:
            print(f"[MC STATUS] Cannot access channel {STATUS_CHANNEL_ID}: {e}")
            return

    if not isinstance(channel, discord.TextChannel):
        print(f"[MC STATUS] Channel {STATUS_CHANNEL_ID} is not a text channel")
        return

    data = fetch_server_status()
    embed = build_status_embed(data)

    message_id = load_message_id()
    message = None

    if message_id is not None:
        try:
            message = await channel.fetch_message(message_id)
        except discord.NotFound:
            print(f"[MC STATUS] Saved message {message_id} not found – will send a new one")
            message = None
        except discord.Forbidden:
            print("[MC STATUS] Missing permission to fetch/edit messages in the status channel")
            return
        except Exception as e:
            print(f"[MC STATUS] Error fetching message {message_id}: {e}")
            message = None

    if message is not None:
        try:
            await message.edit(embed=embed)
            print("[MC STATUS] Message updated successfully")
            return
        except discord.Forbidden:
            print("[MC STATUS] Missing permission to edit the status message")
            return
        except Exception as e:
            print(f"[MC STATUS] Failed to edit message: {e} – will send a new one")
            message = None

    # No existing message (or edit failed) → send new and save ID
    try:
        new_msg = await channel.send(embed=embed)
        save_message_id(new_msg.id)
        print(f"[MC STATUS] Sent new status message (ID: {new_msg.id})")
    except discord.Forbidden:
        print("[MC STATUS] Missing permission to send messages in the status channel")
    except Exception as e:
        print(f"[MC STATUS] Failed to send status message: {e}")


# ============================================================
# BACKGROUND TASK
# ============================================================

@tasks.loop(minutes=2)
async def status_loop(client: discord.Client):
    try:
        await update_status_message(client)
    except Exception as e:
        print(f"[MC STATUS] Unhandled error in status loop: {e}")


def start_status_task(client: discord.Client) -> None:
    """Call this once from on_ready to start the 2-minute updater."""
    if status_loop.is_running():
        print("[MC STATUS] Status loop already running")
        return

    status_loop.start(client)
    print("[MC STATUS] Status loop started (every 2 minutes)")
