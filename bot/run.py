# run.py
# Starts the Discord bot (main.py, untouched) AND the web dashboard (port 7131)
# in the same process / event loop.
#
#   python run.py
#
# main.py still works on its own exactly as before (python main.py) –
# it just won't have the dashboard.

import asyncio

import main as bot_main
from dashboard import start_dashboard, DASHBOARD_PORT


async def runner() -> None:
    if not bot_main.TOKEN:
        raise ValueError("DISCORD_BOT_TOKEN missing from .env")

    dash = await start_dashboard(DASHBOARD_PORT)

    try:
        async with bot_main.client:
            await bot_main.client.start(bot_main.TOKEN)
    finally:
        await dash.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(runner())
    except KeyboardInterrupt:
        print("Shutting down.")
