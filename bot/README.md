# Discord Bot + Dashboard (Python)

## Files
| File | What it is |
|---|---|
| `main.py` | Your bot (scam image filter and ticket system) |
| `ticket.py` | Your ticket system – **unchanged** |
| `send_panel.py` | Your one‑shot panel sender – **unchanged** |
| `dashboard.py` | **NEW** – web dashboard (aiohttp) on port **7131** |
| `run.py` | **NEW** – starts bot + dashboard together |

## Setup
```bash
pip install -r requirements.txt
cp .env.example .env      # put your token + a dashboard password in .env
python run.py             # bot + dashboard
```
Open http://localhost:7131 and log in with `DASHBOARD_PASSWORD`.

`python main.py` still works exactly as before (bot only, no dashboard).

## Dashboard features
- **Overview** – bot online/latency/uptime, module status, server stats
- **Tickets** – list all tickets (open/closed, type, owner), close / reopen / delete from the browser, send the 🎫 Support Center panel
- **Scam Filter** – config + list of blocked SHA‑256 hashes
- **Server** – members, channels (with IDs), roles
- **Activity** – log of dashboard actions
- `GET /api/status` JSON, `GET /health`

Dashboard actions reuse the same functions as the bot (`update_ticket_topic`,
`set_owner_send_permission`, `log_ticket`, `update_status_message`), so they behave
identically to the Discord buttons and are logged to your ticket log channel.

> ⚠️ Enable **Server Members Intent** in the Developer Portal if you want accurate
> member/role counts on the Server page. The bot now requests this intent and refreshes
> the member cache before calculating role totals.
