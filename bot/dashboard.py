# dashboard.py
# Web dashboard for the Discord bot + server.
# Runs INSIDE the bot process (same event loop) so it can see the live
# discord.Client. Pure Python – aiohttp (already a discord.py dependency).
#
# Port: 7131
# Login: DASHBOARD_PASSWORD from .env (default "admin" – change it!)

from __future__ import annotations

import html
import os
import secrets
import time
from datetime import datetime, timezone

import discord
from aiohttp import web

import main as bot_main            # your existing bot (client, tree, BAD_HASHES ...)
import mc_status                   # Minecraft status updater
import ticket                      # your existing ticket module
from ticket import (
    TICKET_TYPES,
    TicketControlView,
    TicketPanelView,
    get_ticket_owner_id,
    is_ticket,
    is_ticket_closed,
    log_ticket,
    set_owner_send_permission,
    update_ticket_topic,
)

DASHBOARD_PORT = 7131
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "admin")
PANEL_CHANNEL_ID = 1541000137428570112          # same as send_panel.py

client: discord.Client = bot_main.client
START_TIME = time.time()

# very small in-memory session store
_sessions: set[str] = set()
_action_log: list[dict] = []   # last 100 dashboard actions
_flash: dict[str, str] = {}    # token -> message


def _log(text: str) -> None:
    _action_log.insert(0, {
        "time": datetime.now(timezone.utc).strftime("%H:%M:%S UTC"),
        "text": text,
    })
    del _action_log[100:]
    print(f"[DASHBOARD] {text}")


def e(v) -> str:
    return html.escape(str(v))


# ============================================================
# AUTH
# ============================================================

def _token(request: web.Request) -> str | None:
    return request.cookies.get("dash_session")


def logged_in(request: web.Request) -> bool:
    t = _token(request)
    return t is not None and t in _sessions


def require_login(handler):
    async def wrapper(request: web.Request):
        if not logged_in(request):
            raise web.HTTPFound("/login")
        return await handler(request)
    return wrapper


# ============================================================
# HELPERS
# ============================================================

def get_guild() -> discord.Guild | None:
    return client.get_guild(bot_main.GUILD_ID)


def uptime_str() -> str:
    s = int(time.time() - START_TIME)
    d, s = divmod(s, 86400)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    parts = []
    if d:
        parts.append(f"{d}d")
    if h:
        parts.append(f"{h}h")
    parts.append(f"{m}m")
    parts.append(f"{s}s")
    return " ".join(parts)


def ticket_channels(guild: discord.Guild) -> list[dict]:
    out = []
    for ch in guild.text_channels:
        if not is_ticket(ch):
            continue
        topic = ch.topic or ""
        ttype = "unknown"
        for part in topic.split("|"):
            if part.startswith("type:"):
                ttype = part[len("type:"):]
        emoji, name = TICKET_TYPES.get(ttype, ("🎫", ttype))
        owner_id = get_ticket_owner_id(ch)
        member = guild.get_member(owner_id) if owner_id else None
        out.append({
            "id": ch.id,
            "name": ch.name,
            "type": ttype,
            "type_label": f"{emoji} {name}",
            "closed": is_ticket_closed(ch),
            "owner_id": owner_id,
            "owner": str(member) if member else (str(owner_id) if owner_id else "?"),
            "created": ch.created_at.strftime("%Y-%m-%d %H:%M"),
        })
    out.sort(key=lambda t: (t["closed"], t["name"]))
    return out


def channel_name(cid: int) -> str:
    ch = client.get_channel(cid)
    return f"#{ch.name}" if ch is not None else "not found"


def role_name(guild: discord.Guild | None, rid: int) -> str:
    if guild is None:
        return "?"
    r = guild.get_role(rid)
    return f"@{r.name}" if r else "not found"


# ============================================================
# LAYOUT
# ============================================================

CSS = """
*{box-sizing:border-box}body{margin:0;font-family:ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#0d1117;color:#d6deea;background-image:radial-gradient(circle at 85% -10%,#19324a 0,transparent 34%),linear-gradient(135deg,#0d1117 0%,#111923 100%)}
a{color:#00a8fc;text-decoration:none}a:hover{text-decoration:underline}
.top{background:#111923eF;border-bottom:1px solid #27384a;padding:15px clamp(16px,4vw,48px);display:flex;align-items:center;gap:28px;position:sticky;top:0;z-index:5;backdrop-filter:blur(14px)}
.top .brand{font-weight:700;color:#fff;font-size:18px}.top nav a{margin-right:14px;color:#b5bac1;font-weight:500}
.top nav a.active,.top nav a:hover{color:#fff;background:#20354a;text-decoration:none}.top .right{margin-left:auto;display:flex;gap:10px;align-items:center;color:#8fa4b8;font-size:13px;white-space:nowrap}
.wrap{max-width:1240px;margin:0 auto;padding:34px clamp(16px,4vw,48px) 60px}
h1{font-size:30px;letter-spacing:-.04em;color:#f5fbff;margin:0 0 22px}h2{font-size:15px;color:#f5fbff;margin:0 0 14px}
.grid{display:grid;gap:16px}.g4{grid-template-columns:repeat(auto-fit,minmax(220px,1fr))}.g2{grid-template-columns:repeat(auto-fit,minmax(340px,1fr))}
.card{background:#151f2b;border:1px solid #293d50;border-radius:8px;padding:20px;box-shadow:0 12px 30px #05080c38}
.stat .lbl{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:#949ba4}.stat .val{font-size:28px;font-weight:700;color:#fff;margin-top:4px}
.stat .sub{font-size:12px;color:#949ba4;margin-top:2px}
table{width:100%;border-collapse:collapse;font-size:14px}th,td{padding:10px 8px;text-align:left;border-bottom:1px solid #3f4147}th{color:#949ba4;font-weight:600;font-size:12px;text-transform:uppercase}
tr:last-child td{border-bottom:0}code{background:#1e1f22;padding:2px 6px;border-radius:4px;font-size:13px;color:#f2f3f5}
.badge{display:inline-block;padding:3px 9px;border-radius:999px;font-size:12px;font-weight:600}
.ok{background:#23a55a33;color:#57f287}.bad{background:#da373c33;color:#f23f43}.mid{background:#f0b23233;color:#f0b232}.neu{background:#4e505833;color:#b5bac1}
.btn{display:inline-block;border:0;border-radius:5px;padding:8px 14px;font-size:13px;font-weight:700;cursor:pointer;color:#061018;background:#68d5ff;font-family:inherit}
.btn:hover{filter:brightness(1.1)}.btn.red{background:#da373c}.btn.green{background:#23a55a}.btn.grey{background:#4e5058}.btn.sm{padding:5px 10px;font-size:12px}
form.inline{display:inline}.flash{background:#5865f233;border:1px solid #5865f2;color:#fff;padding:10px 14px;border-radius:8px;margin-bottom:16px}
input[type=text],input[type=password]{width:100%;padding:10px;border-radius:6px;border:1px solid #3f4147;background:#1e1f22;color:#fff;font-size:14px;font-family:inherit}
.muted{color:#8fa4b8;font-size:13px}.mono{font-family:ui-monospace,Consolas,monospace;font-size:12px;word-break:break-all}
.embed{border-left:4px solid #5865f2;background:#1e1f22;border-radius:6px;padding:12px 14px}.embed.green{border-color:#23a55a}.embed.red{border-color:#da373c}.embed.grey{border-color:#4e5058}
.embed .t{font-weight:700;color:#fff;margin-bottom:6px}.embed .f{margin-top:8px}.embed .f b{display:block;font-size:12px;color:#fff}
.login{max-width:380px;margin:80px auto}
ul.log{list-style:none;padding:0;margin:0;font-size:13px}ul.log li{padding:8px 0;border-bottom:1px solid #293d50}ul.log li span{color:#8fa4b8;margin-right:8px}@media(max-width:720px){.top{align-items:flex-start;flex-wrap:wrap;gap:10px}.top nav{order:3;width:100%;overflow:auto;flex-wrap:nowrap}.top .right{margin-left:auto}.g2{grid-template-columns:minmax(0,1fr)}.card{padding:16px}table{display:block;overflow-x:auto;white-space:nowrap}}
"""


def page(title: str, body: str, active: str = "", flash: str | None = None) -> web.Response:
    user = e(client.user) if client.user else "connecting…"
    nav = ""
    for href, label, key in [
        ("/", "Overview", "overview"),
        ("/tickets", "Tickets", "tickets"),
        ("/minecraft", "Minecraft", "minecraft"),
        ("/security", "Scam Filter", "security"),
        ("/server", "Server", "server"),
        ("/logs", "Activity", "logs"),
    ]:
        cls = ' class="active"' if key == active else ""
        nav += f'<a href="{href}"{cls}>{label}</a>'
    flash_html = f'<div class="flash">{e(flash)}</div>' if flash else ""
    doc = f"""<!doctype html><html><head><meta charset="utf-8"><title>{e(title)} · Bot Dashboard</title>
<meta name="viewport" content="width=device-width,initial-scale=1"><style>{CSS}</style></head><body>
<div class="top"><span class="brand">🤖 Bot Dashboard</span><nav>{nav}</nav>
<div class="right"><span>{user}</span><a class="btn grey sm" href="/logout">Logout</a></div></div>
<div class="wrap">{flash_html}{body}</div></body></html>"""
    return web.Response(text=doc, content_type="text/html")


def redirect_with_flash(request: web.Request, url: str, msg: str) -> web.HTTPFound:
    t = _token(request)
    if t:
        _flash[t] = msg
    return web.HTTPFound(url)


def pop_flash(request: web.Request) -> str | None:
    t = _token(request)
    return _flash.pop(t, None) if t else None


# ============================================================
# ROUTES – AUTH
# ============================================================

async def login_get(request: web.Request):
    err = request.query.get("err")
    err_html = '<div class="flash" style="border-color:#da373c;background:#da373c33">Wrong password.</div>' if err else ""
    body = f"""<div class="login"><div class="card"><h1>🤖 Bot Dashboard</h1>{err_html}
<form method="post"><input type="password" name="password" placeholder="Dashboard password" autofocus>
<br><br><button class="btn" style="width:100%">Login</button></form>
<p class="muted">Set <code>DASHBOARD_PASSWORD</code> in your .env</p></div></div>"""
    return web.Response(
        text=f"<!doctype html><html><head><meta charset='utf-8'><title>Login</title><style>{CSS}</style></head><body>{body}</body></html>",
        content_type="text/html",
    )


async def login_post(request: web.Request):
    data = await request.post()
    if secrets.compare_digest(str(data.get("password", "")), DASHBOARD_PASSWORD):
        tok = secrets.token_urlsafe(32)
        _sessions.add(tok)
        resp = web.HTTPFound("/")
        resp.set_cookie("dash_session", tok, httponly=True, samesite="Lax", max_age=60 * 60 * 24 * 7)
        _log("Dashboard login")
        raise resp
    raise web.HTTPFound("/login?err=1")


async def logout(request: web.Request):
    t = _token(request)
    if t:
        _sessions.discard(t)
    resp = web.HTTPFound("/login")
    resp.del_cookie("dash_session")
    raise resp


# ============================================================
# ROUTES – OVERVIEW
# ============================================================

@require_login
async def overview(request: web.Request):
    guild = get_guild()
    tickets = ticket_channels(guild) if guild else []
    open_t = sum(1 for t in tickets if not t["closed"])
    status = "Online" if client.is_ready() else "Connecting"
    latency = f"{client.latency * 1000:.0f} ms" if client.is_ready() else "—"

    guild_card = (
        f"""<div class="card"><h2>Server</h2>
<table><tr><td>Name</td><td><b>{e(guild.name)}</b></td></tr>
<tr><td>Members</td><td>{guild.member_count}</td></tr>
<tr><td>Text channels</td><td>{len(guild.text_channels)}</td></tr>
<tr><td>Roles</td><td>{len(guild.roles)}</td></tr>
<tr><td>Owner</td><td>{e(guild.owner)}</td></tr>
<tr><td>Guild ID</td><td><code>{guild.id}</code></td></tr></table></div>"""
        if guild else
        f'<div class="card"><h2>Server</h2><span class="badge bad">Guild {bot_main.GUILD_ID} not found</span><p class="muted">Is the bot in the server?</p></div>'
    )

    body = f"""<h1>Overview</h1>
<div class="grid g4">
<div class="card stat"><div class="lbl">Bot status</div><div class="val"><span class="badge {'ok' if client.is_ready() else 'mid'}">{status}</span></div><div class="sub">Latency {latency}</div></div>
<div class="card stat"><div class="lbl">Uptime</div><div class="val">{uptime_str()}</div><div class="sub">{len(client.guilds)} server(s) connected</div></div>
<div class="card stat"><div class="lbl">Open tickets</div><div class="val">{open_t}</div><div class="sub">{len(tickets) - open_t} closed · <a href="/tickets">manage</a></div></div>
<div class="card stat"><div class="lbl">Scam hashes</div><div class="val">{len(bot_main.BAD_HASHES)}</div><div class="sub">image filter active</div></div>
</div><br>
<div class="grid g2">
{guild_card}
<div class="card"><h2>Modules</h2><table>
<tr><td>🎫 Ticket system</td><td><span class="badge {'ok' if getattr(client, 'ticket_system_loaded', False) else 'mid'}">{'loaded' if getattr(client, 'ticket_system_loaded', False) else 'pending'}</span></td></tr>
<tr><td>🛡️ Scam image filter</td><td><span class="badge ok">active</span> <span class="muted">logs → {e(channel_name(bot_main.LOG_CHANNEL_ID))}</span></td></tr>
<tr><td>/deleteticket</td><td><span class="badge {'ok' if bot_main.tree.get_command('deleteticket') else 'mid'}">{'registered' if bot_main.tree.get_command('deleteticket') else 'pending'}</span></td></tr>
</table></div></div>"""
    return page("Overview", body, "overview", pop_flash(request))


# ============================================================
# ROUTES – TICKETS
# ============================================================

@require_login
async def tickets_page(request: web.Request):
    guild = get_guild()
    if guild is None:
        return page("Tickets", "<h1>Tickets</h1><div class='card'>Guild not found.</div>", "tickets")
    tickets = ticket_channels(guild)
    rows = ""
    for t in tickets:
        st = '<span class="badge bad">CLOSED</span>' if t["closed"] else '<span class="badge ok">OPEN</span>'
        toggle = (
            f'<form class="inline" method="post" action="/tickets/{t["id"]}/reopen"><button class="btn green sm">🔓 Reopen</button></form>'
            if t["closed"] else
            f'<form class="inline" method="post" action="/tickets/{t["id"]}/close"><button class="btn red sm">🔒 Close</button></form>'
        )
        rows += f"""<tr><td><a href="https://discord.com/channels/{guild.id}/{t['id']}" target="_blank">#{e(t['name'])}</a></td>
<td>{e(t['type_label'])}</td><td>{e(t['owner'])}</td><td>{st}</td><td>{t['created']}</td>
<td style="white-space:nowrap">{toggle}
<form class="inline" method="post" action="/tickets/{t['id']}/delete" onsubmit="return confirm('Permanently delete #{e(t['name'])}?')"><button class="btn grey sm">🗑️ Delete</button></form></td></tr>"""
    if not rows:
        rows = '<tr><td colspan="6" class="muted">No ticket channels found.</td></tr>'

    types = "".join(f"<tr><td>{e(em)} {e(nm)}</td><td><code>ticket:{e(k)}</code></td></tr>" for k, (em, nm) in TICKET_TYPES.items())
    body = f"""<h1>Tickets</h1>
<div class="card"><table><thead><tr><th>Channel</th><th>Type</th><th>Owner</th><th>Status</th><th>Created</th><th>Actions</th></tr></thead><tbody>{rows}</tbody></table></div><br>
<div class="grid g2">
<div class="card"><h2>Ticket panel</h2><p class="muted">Sends the "🎫 Support Center" panel (same as <code>send_panel.py</code>) to {e(channel_name(PANEL_CHANNEL_ID))} (<code>{PANEL_CHANNEL_ID}</code>).</p>
<form method="post" action="/tickets/send-panel" onsubmit="return confirm('Send the ticket panel now?')"><button class="btn">📨 Send ticket panel</button></form></div>
<div class="card"><h2>Configuration</h2><table>
<tr><td>Category</td><td>{e(channel_name(ticket.TICKET_CATEGORY_ID))} <code>{ticket.TICKET_CATEGORY_ID}</code></td></tr>
<tr><td>Log channel</td><td>{e(channel_name(ticket.TICKET_LOG_CHANNEL_ID))} <code>{ticket.TICKET_LOG_CHANNEL_ID}</code></td></tr>
<tr><td>Staff role</td><td>{e(role_name(guild, ticket.STAFF_ROLE_ID))} <code>{ticket.STAFF_ROLE_ID}</code></td></tr>
</table><br><h2>Ticket types</h2><table>{types}</table></div></div>"""
    return page("Tickets", body, "tickets", pop_flash(request))


def _get_ticket_channel(request: web.Request) -> discord.TextChannel:
    guild = get_guild()
    ch = guild.get_channel(int(request.match_info["id"])) if guild else None
    if ch is None or not is_ticket(ch):
        raise web.HTTPNotFound(text="Ticket channel not found")
    return ch


@require_login
async def ticket_close(request: web.Request):
    ch = _get_ticket_channel(request)
    if is_ticket_closed(ch):
        raise redirect_with_flash(request, "/tickets", f"#{ch.name} is already closed.")
    if await update_ticket_topic(ch, closed=True) is None:
        raise redirect_with_flash(request, "/tickets", "❌ Failed to update topic (Manage Channels?).")
    owner_id = get_ticket_owner_id(ch)
    perm_ok = await set_owner_send_permission(ch, owner_id, allow=False)
    embed = discord.Embed(
        title="🔴 Ticket Closed",
        description=(
            "This ticket has been closed.\n\n"
            "The ticket owner can **no longer send messages**.\n\n"
            "Staff or the ticket owner can open it again with "
            "**🔓 Reopen Ticket**.\n\n"
            "Staff can permanently delete this ticket with:\n"
            "`/deleteticket`"
        ),
        color=discord.Color.red(),
    )
    embed.add_field(name="Closed By", value="🖥️ Dashboard", inline=True)
    embed.add_field(name="Status", value="🔴 CLOSED", inline=True)
    try:
        await ch.send(embed=embed, view=TicketControlView())
    except Exception as ex:
        print(f"[DASHBOARD] send error: {ex}")
    await log_ticket(ch.guild, f"🔴 `{ch.name}` closed via dashboard")
    _log(f"Closed ticket #{ch.name}")
    msg = f"🔴 #{ch.name} closed." + ("" if perm_ok else " ⚠️ Could not lock permissions.")
    raise redirect_with_flash(request, "/tickets", msg)


@require_login
async def ticket_reopen(request: web.Request):
    ch = _get_ticket_channel(request)
    if not is_ticket_closed(ch):
        raise redirect_with_flash(request, "/tickets", f"#{ch.name} is already open.")
    if await update_ticket_topic(ch, closed=False) is None:
        raise redirect_with_flash(request, "/tickets", "❌ Failed to update topic (Manage Channels?).")
    owner_id = get_ticket_owner_id(ch)
    perm_ok = await set_owner_send_permission(ch, owner_id, allow=True)
    embed = discord.Embed(
        title="🟢 Ticket Reopened",
        description=(
            "This ticket has been reopened.\n\n"
            "The ticket owner can **send messages again**.\n\n"
            "When finished, click **🔒 Close Ticket**."
        ),
        color=discord.Color.green(),
    )
    embed.add_field(name="Reopened By", value="🖥️ Dashboard", inline=True)
    embed.add_field(name="Status", value="🟢 OPEN", inline=True)
    try:
        await ch.send(embed=embed, view=TicketControlView())
    except Exception as ex:
        print(f"[DASHBOARD] send error: {ex}")
    await log_ticket(ch.guild, f"🟢 `{ch.name}` reopened via dashboard")
    _log(f"Reopened ticket #{ch.name}")
    msg = f"🟢 #{ch.name} reopened." + ("" if perm_ok else " ⚠️ Could not restore permissions.")
    raise redirect_with_flash(request, "/tickets", msg)


@require_login
async def ticket_delete(request: web.Request):
    ch = _get_ticket_channel(request)
    name = ch.name
    await log_ticket(ch.guild, f"🗑️ `{name}` permanently deleted via dashboard")
    try:
        await ch.delete(reason="Ticket deleted via dashboard")
        _log(f"Deleted ticket #{name}")
        raise redirect_with_flash(request, "/tickets", f"🗑️ #{name} deleted.")
    except discord.Forbidden:
        raise redirect_with_flash(request, "/tickets", "❌ Missing Manage Channels permission.")
    except discord.HTTPException as ex:
        raise redirect_with_flash(request, "/tickets", f"❌ Discord error: {ex}")


@require_login
async def send_panel(request: web.Request):
    channel = client.get_channel(PANEL_CHANNEL_ID)
    if channel is None:
        raise redirect_with_flash(request, "/tickets", "❌ Panel channel not found.")
    # Identical embed to send_panel.py
    embed = discord.Embed(
        title="🎫 Support Center",
        description=(
            "Need help? Select the category "
            "that best describes your request.\n\n"
            "A private ticket will be created "
            "for you and our staff team will "
            "be notified."
        ),
        color=discord.Color.blurple(),
    )
    embed.add_field(name="💰 Refunds", value="Refund-related requests", inline=True)
    embed.add_field(name="🐛 Bugs", value="Report technical issues", inline=True)
    embed.add_field(name="❓ Questions", value="Ask our support team", inline=True)
    embed.add_field(name="💬 General", value="General support", inline=True)
    embed.add_field(name="🤝 Partnership Requests", value="Business/partnership requests", inline=True)
    embed.add_field(name="🚨 Report User", value="Report a Discord user", inline=True)
    embed.add_field(name="🔨 Ban Appeals", value="Appeal a server ban", inline=True)
    embed.set_footer(text="Support Ticket System")
    try:
        await channel.send(embed=embed, view=TicketPanelView())
        _log("Sent ticket panel")
        raise redirect_with_flash(request, "/tickets", "📨 Ticket panel sent.")
    except discord.Forbidden:
        raise redirect_with_flash(request, "/tickets", "❌ Missing permission to send in panel channel.")


# ============================================================
# ROUTES – SCAM FILTER
# ============================================================

@require_login
async def security_page(request: web.Request):
    rows = "".join(f'<tr><td class="mono">{e(h)}</td></tr>' for h in sorted(bot_main.BAD_HASHES))
    body = f"""<h1>Scam Image Filter</h1>
<div class="grid g2">
<div class="card"><h2>How it works</h2><p class="muted">Every attachment posted in the server is hashed with SHA-256. If the hash matches a known scam image the message is deleted and a notice is posted in the log channel.</p>
<table><tr><td>Guild</td><td><code>{bot_main.GUILD_ID}</code></td></tr>
<tr><td>Log channel</td><td>{e(channel_name(bot_main.LOG_CHANNEL_ID))} <code>{bot_main.LOG_CHANNEL_ID}</code></td></tr>
<tr><td>Message content intent</td><td><span class="badge {'ok' if bot_main.intents.message_content else 'bad'}">{'enabled' if bot_main.intents.message_content else 'disabled'}</span></td></tr>
<tr><td>Known hashes</td><td><b>{len(bot_main.BAD_HASHES)}</b></td></tr></table></div>
<div class="card"><h2>Blocked SHA-256 hashes</h2><table>{rows}</table>
<p class="muted">To add a hash, edit <code>BAD_HASHES</code> in main.py.</p></div></div>"""
    return page("Scam Filter", body, "security", pop_flash(request))


# ============================================================
# ROUTES – SERVER
# ============================================================

async def load_guild_members(guild: discord.Guild) -> list[discord.Member]:
    """Refresh the member cache so role totals reflect the actual guild."""
    if not guild.chunked:
        try:
            await guild.chunk(cache=True)
        except (discord.Forbidden, discord.HTTPException) as ex:
            print(f"[DASHBOARD] Could not refresh members: {ex}")
    return list(guild.members)


@require_login
async def server_page(request: web.Request):
    guild = get_guild()
    if guild is None:
        return page("Server", "<h1>Server</h1><div class='card'>Guild not found.</div>", "server")
    members = await load_guild_members(guild)
    online = sum(1 for m in members if m.status != discord.Status.offline)
    bots = sum(1 for m in members if m.bot)

    chans = ""
    for cat, chs in guild.by_category():
        chans += f'<tr><td colspan="3"><b>{e(cat.name) if cat else "No category"}</b></td></tr>'
        for c in chs:
            kind = "🔊" if isinstance(c, discord.VoiceChannel) else "📢" if isinstance(c, discord.StageChannel) else "💬" if isinstance(c, discord.ForumChannel) else "#"
            chans += f'<tr><td>{kind} {e(c.name)}</td><td><code>{c.id}</code></td><td class="muted">{e(c.topic[:60]) if getattr(c, "topic", None) else ""}</td></tr>'

    role_counts = {role.id: 0 for role in guild.roles}
    for member in members:
        for role in member.roles:
            role_counts[role.id] = role_counts.get(role.id, 0) + 1
    roles = "".join(
        f'<tr><td><span style="color:{r.color if r.color.value else "#dbdee1"}">@{e(r.name)}</span></td><td>{role_counts.get(r.id, 0)}</td><td><code>{r.id}</code></td></tr>'
        for r in sorted(guild.roles, key=lambda r: -r.position)
    )
    body = f"""<h1>{e(guild.name)}</h1>
<div class="grid g4">
<div class="card stat"><div class="lbl">Members</div><div class="val">{len(members) or guild.member_count}</div><div class="sub">{bots} bots · {online} online</div></div>
<div class="card stat"><div class="lbl">Channels</div><div class="val">{len(guild.channels)}</div><div class="sub">{len(guild.text_channels)} text · {len(guild.voice_channels)} voice · {len(guild.categories)} categories</div></div>
<div class="card stat"><div class="lbl">Roles</div><div class="val">{len(guild.roles)}</div><div class="sub">boost level {guild.premium_tier}</div></div>
<div class="card stat"><div class="lbl">Created</div><div class="val" style="font-size:20px">{guild.created_at.strftime('%Y-%m-%d')}</div><div class="sub">owner {e(guild.owner)}</div></div>
</div><br>
<div class="grid g2">
<div class="card"><h2>Channels</h2><table>{chans}</table></div>
<div class="card"><h2>Roles</h2><table><thead><tr><th>Role</th><th>Members</th><th>ID</th></tr></thead>{roles}</table></div></div>"""
    return page("Server", body, "server", pop_flash(request))


# ============================================================
# ROUTES - MINECRAFT MAINTENANCE
# ============================================================

@require_login
async def minecraft_page(request: web.Request):
    loop = mc_status.status_loop
    message_id = mc_status.load_message_id()
    body = f"""<h1>Minecraft Maintenance</h1>
<div class="grid g2">
<div class="card"><h2>Status embed</h2>
<table><tr><td>Server</td><td><code>{e(mc_status.SERVER_ADDRESS)}</code></td></tr>
<tr><td>API</td><td><a href="{e(mc_status.API_URL)}" target="_blank">mcsrvstat.us</a></td></tr>
<tr><td>Channel</td><td><code>{mc_status.STATUS_CHANNEL_ID}</code></td></tr>
<tr><td>Saved message</td><td><code>{message_id or 'not created'}</code></td></tr>
<tr><td>Maintenance mode</td><td><span class="badge {'bad' if mc_status.is_maintenance() else 'ok'}">{'enabled' if mc_status.is_maintenance() else 'disabled'}</span></td></tr>
<tr><td>Automatic updater</td><td><span class="badge {'ok' if loop.is_running() else 'bad'}">{'running' if loop.is_running() else 'stopped'}</span></td></tr></table>
</div>
<div class="card"><h2>Maintenance actions</h2>
<p class="muted">Maintenance mode changes the embed immediately. Disable it to return to the normal live server status and MOTD.</p>
<form method="post" action="/minecraft/maintenance/on"><button class="btn red">🛠️ Mark under maintenance</button></form><br>
<form method="post" action="/minecraft/maintenance/off"><button class="btn green">✅ Remove maintenance mark</button></form><br>
<form method="post" action="/minecraft/force"><button class="btn">🔄 Force status update</button></form><br>
<form method="post" action="/minecraft/resend" onsubmit="return confirm('Delete the current status message and send a replacement?')"><button class="btn red">♻️ Resend and replace</button></form>
</div></div>"""
    return page("Minecraft", body, "minecraft", pop_flash(request))


@require_login
async def minecraft_force(request: web.Request):
    try:
        await mc_status.update_status_message(client)
        _log("Forced Minecraft status update")
        raise redirect_with_flash(request, "/minecraft", "Minecraft status embed updated.")
    except web.HTTPException:
        raise
    except Exception as error:
        raise redirect_with_flash(request, "/minecraft", f"Minecraft update failed: {error}")


@require_login
async def minecraft_resend(request: web.Request):
    try:
        await mc_status.resend_status_message(client)
        _log("Replaced Minecraft status message")
        raise redirect_with_flash(request, "/minecraft", "Minecraft status embed replaced.")
    except web.HTTPException:
        raise
    except Exception as error:
        raise redirect_with_flash(request, "/minecraft", f"Minecraft replacement failed: {error}")


async def _set_minecraft_maintenance(request: web.Request, enabled: bool):
    try:
        mc_status.set_maintenance(enabled)
        await mc_status.update_status_message(client)
        label = "enabled" if enabled else "removed"
        _log(f"Minecraft maintenance mode {label}")
        raise redirect_with_flash(request, "/minecraft", f"Minecraft maintenance mode {label}.")
    except web.HTTPException:
        raise
    except Exception as error:
        raise redirect_with_flash(request, "/minecraft", f"Maintenance update failed: {error}")


@require_login
async def minecraft_maintenance_on(request: web.Request):
    return await _set_minecraft_maintenance(request, True)


@require_login
async def minecraft_maintenance_off(request: web.Request):
    return await _set_minecraft_maintenance(request, False)


# ============================================================
# ROUTES – ACTIVITY LOG / JSON API
# ============================================================

@require_login
async def logs_page(request: web.Request):
    items = "".join(f'<li><span>{e(a["time"])}</span>{e(a["text"])}</li>' for a in _action_log) or '<li class="muted">No dashboard actions yet.</li>'
    body = f'<h1>Activity</h1><div class="card"><ul class="log">{items}</ul></div>'
    return page("Activity", body, "logs", pop_flash(request))


@require_login
async def api_status(request: web.Request):
    guild = get_guild()
    tickets = ticket_channels(guild) if guild else []
    return web.json_response({
        "ready": client.is_ready(),
        "user": str(client.user) if client.user else None,
        "latency_ms": round(client.latency * 1000) if client.is_ready() else None,
        "uptime": uptime_str(),
        "guild": {"id": guild.id, "name": guild.name, "members": guild.member_count} if guild else None,
        "tickets": tickets,
        "bad_hash_count": len(bot_main.BAD_HASHES),
    })


async def health(request: web.Request):
    return web.json_response({"ok": True, "ready": client.is_ready()})


# ============================================================
# APP
# ============================================================

def create_app() -> web.Application:
    app = web.Application()
    app.add_routes([
        web.get("/login", login_get),
        web.post("/login", login_post),
        web.get("/logout", logout),
        web.get("/", overview),
        web.get("/tickets", tickets_page),
        web.post("/tickets/send-panel", send_panel),
        web.post("/tickets/{id}/close", ticket_close),
        web.post("/tickets/{id}/reopen", ticket_reopen),
        web.post("/tickets/{id}/delete", ticket_delete),
        web.get("/minecraft", minecraft_page),
        web.post("/minecraft/force", minecraft_force),
        web.post("/minecraft/resend", minecraft_resend),
        web.post("/minecraft/maintenance/on", minecraft_maintenance_on),
        web.post("/minecraft/maintenance/off", minecraft_maintenance_off),
        web.get("/security", security_page),
        web.get("/server", server_page),
        web.get("/logs", logs_page),
        web.get("/api/status", api_status),
        web.get("/health", health),
    ])
    return app


async def start_dashboard(port: int = DASHBOARD_PORT) -> web.AppRunner:
    runner = web.AppRunner(create_app())
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"[DASHBOARD] Running on http://0.0.0.0:{port}")
    if DASHBOARD_PASSWORD == "admin":
        print("[DASHBOARD] WARNING: using default password 'admin' – set DASHBOARD_PASSWORD in .env")
    return runner
