import os
import discord
from discord.ext import commands, tasks
from datetime import time as dtime, datetime, timedelta
from zoneinfo import ZoneInfo  # Python 3.9+
from aiohttp import web

# ====== CONFIGURE THESE ======
TOKEN = os.getenv("DISCORD_BOT_TOKEN")  # set this in Render env vars
CHANNEL_ID = 1370117597416394774        # replace with the ID of the channel to send reminders in
USER_ID = 753101826920022126
# ==============================

# Discord intents
intents = discord.Intents.default()
intents.message_content = True  # needed for !nextmeds command

bot = commands.Bot(command_prefix="!", intents=intents)

# Timezone (SGT = UTC+8)
SGT = ZoneInfo("Asia/Singapore")

# For Render port binding (so health checks pass)
PORT = int(os.environ.get("PORT", "10000"))
_web_server_started = False


async def send_reminder(message: str):
    """Send a message to the configured channel."""
    channel = bot.get_channel(CHANNEL_ID)
    if channel is None:
        try:
            channel = await bot.fetch_channel(CHANNEL_ID)
        except Exception as e:
            print(f"Could not find channel {CHANNEL_ID}: {e}")
            return

    try:
        await channel.send(message)
        print(f"Sent reminder: {message}")
    except Exception as e:
        print(f"Failed to send reminder: {e}")


async def start_web_server():
    """
    Tiny HTTP server so Render detects an open port.
    This keeps the Web Service deployment happy on the free tier.
    """
    async def handle_root(request):
        return web.Response(text="Bot is running ✅")

    app = web.Application()
    app.router.add_get("/", handle_root)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=PORT)
    await site.start()
    print(f"Web server started on port {PORT}")


@bot.event
async def on_ready():
    global _web_server_started

    print(f"Logged in as {bot.user} (ID: {bot.user.id})")

    # Start all meds reminder loops
    if not mucopro_7am.is_running():
        mucopro_7am.start()
    if not mucopro_1230pm.is_running():
        mucopro_1230pm.start()
    if not pantec_6pm.is_running():
        pantec_6pm.start()
    if not mucopro_7pm.is_running():
        mucopro_7pm.start()
    if not zycast_9pm.is_running():
        zycast_9pm.start()

    print("All med reminder loops started.")

    # Start tiny web server once (for Render health check)
    if not _web_server_started:
        bot.loop.create_task(start_web_server())
        _web_server_started = True

    # Startup message in your channel
    await send_reminder("✅ Bot is online! Med reminder schedule loaded. 💊")


# =============== SCHEDULED REMINDERS ===============

# 7:00 AM – Mucopro
@tasks.loop(time=dtime(hour=7, minute=0, tzinfo=SGT))
async def mucopro_7am():
    msg = f"⏰ <@{USER_ID}> 7:00 AM Mucopro time! 💊"
    await send_reminder(msg)


# 12:30 PM – Mucopro
@tasks.loop(time=dtime(hour=12, minute=30, tzinfo=SGT))
async def mucopro_1230pm():
    msg = f"⏰ <@{USER_ID}> 12:30 PM Mucopro time! 💊"
    await send_reminder(msg)


# 6:00 PM – Pantec-DSR
@tasks.loop(time=dtime(hour=18, minute=0, tzinfo=SGT))
async def pantec_6pm():
    msg = f"⏰ <@{USER_ID}> 6:00 PM Pantec-DSR time! Pantec-DSR 💊"
    await send_reminder(msg)


# 7:00 PM – Mucopro
@tasks.loop(time=dtime(hour=19, minute=0, tzinfo=SGT))
async def mucopro_7pm():
    msg = f"⏰ <@{USER_ID}> 7:00 PM Mucopro time! 💊"
    await send_reminder(msg)


# 9:00 PM – Zycast
@tasks.loop(time=dtime(hour=21, minute=0, tzinfo=SGT))
async def zycast_9pm():
    msg = f"⏰ <@{USER_ID}> 9:00 PM Zycast time! 💊"
    await send_reminder(msg)


# =============== !nextmeds COMMAND ===============

@bot.command()
async def nextmeds(ctx):
    """Shows the next upcoming meds reminder."""
    now = datetime.now(SGT)

    # Label, time, medicine text
    schedule = [
        ("7:00 AM",  dtime(hour=7, minute=0, tzinfo=SGT),   "Mucopro 💊"),
        ("12:30 PM", dtime(hour=12, minute=30, tzinfo=SGT), "Mucopro 💊"),
        ("6:00 PM",  dtime(hour=18, minute=0, tzinfo=SGT),  "Pantec-DSR 💊"),
        ("7:00 PM",  dtime(hour=19, minute=0, tzinfo=SGT),  "Mucopro 💊"),
        ("9:00 PM",  dtime(hour=21, minute=0, tzinfo=SGT),  "Zycast 💊"),
    ]

    upcoming = None
    shortest_delta = timedelta(days=999)

    for label, t, med in schedule:
        scheduled_dt = datetime(
            now.year, now.month, now.day,
            t.hour, t.minute, tzinfo=SGT
        )

        # If the time already passed today, use tomorrow
        if scheduled_dt < now:
            scheduled_dt += timedelta(days=1)

        delta = scheduled_dt - now

        if delta < shortest_delta:
            shortest_delta = delta
            upcoming = (label, med, scheduled_dt)

    if upcoming:
        label, med, when_dt = upcoming
        total_secs = int(shortest_delta.total_seconds())
        hours = total_secs // 3600
        mins = (total_secs % 3600) // 60

        await ctx.send(
            f"📅 **Next meds:** {med}\n"
            f"⏰ **Time:** {label} SGT\n"
            f"⏳ In **{hours}h {mins}m**"
        )
    else:
        await ctx.send("No meds scheduled — this should never happen 😅")


# =============== MAIN ===============

if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError(
            "DISCORD_BOT_TOKEN environment variable not set. "
            "Set it to your bot token before running."
        )
    bot.run(TOKEN)
