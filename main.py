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

# Med schedule (all times in SGT)
# Each id must be unique and stable
MED_SCHEDULE = [
    {"id": "mucopro_7am",   "label": "7:00 AM",   "hour": 7,  "minute": 0,  "med": "Mucopro 💊"},
    {"id": "mucopro_1230",  "label": "12:30 PM",  "hour": 12, "minute": 30, "med": "Mucopro 💊"},
    {"id": "pantec_6pm",    "label": "6:00 PM",   "hour": 18, "minute": 0,  "med": "Pantec-DSR 💊"},
    {"id": "mucopro_7pm",   "label": "7:00 PM",   "hour": 19, "minute": 0,  "med": "Mucopro 💊"},
    {"id": "zycast_9pm",    "label": "9:00 PM",   "hour": 21, "minute": 0,  "med": "Zycast 💊"},
]

# Track when each med was last sent (by date)
last_sent_date = {}  # { "mucopro_7am": date, ... }

# How late we still allow sending a missed reminder (in minutes)
GRACE_MINUTES = 120  # 2 hours


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

    # Start meds loop
    if not meds_loop.is_running():
        meds_loop.start()
        print("Meds loop started.")

    # Start tiny web server once (for Render health check)
    if not _web_server_started:
        bot.loop.create_task(start_web_server())
        _web_server_started = True

    # Startup message in your channel
    await send_reminder("✅ Bot is online! Med reminder schedule loaded. 💊")


@bot.event
async def on_disconnect():
    print("⚠️ Bot disconnected from Discord gateway.")


@bot.event
async def on_resumed():
    print("✅ Bot resumed Discord session.")


# =============== SCHEDULED REMINDERS (RESILIENT LOOP) ===============

@tasks.loop(minutes=1)
async def meds_loop():
    """Check every minute which meds should be sent, and send any due ones once per day."""
    now = datetime.now(SGT)
    today = now.date()

    for item in MED_SCHEDULE:
        sched_dt = datetime(
            year=today.year,
            month=today.month,
            day=today.day,
            hour=item["hour"],
            minute=item["minute"],
            tzinfo=SGT,
        )

        # If scheduled time is in the future, skip
        if now < sched_dt:
            continue

        # How late are we compared to the scheduled time?
        delay_minutes = (now - sched_dt).total_seconds() / 60.0

        # Skip if we're way too late (past the grace window)
        if delay_minutes > GRACE_MINUTES:
            continue

        last_date = last_sent_date.get(item["id"])

        # Only send once per day
        if last_date == today:
            continue

        # Send the reminder
        msg = f"⏰ <@{USER_ID}> {item['label']} {item['med']} time!"
        await send_reminder(msg)
        last_sent_date[item["id"]] = today
        print(f"Marked {item['id']} as sent for {today}")


# =============== !nextmeds COMMAND ===============

@bot.command()
async def nextmeds(ctx):
    """Shows the next upcoming meds reminder."""
    now = datetime.now(SGT)

    schedule = [
        (item["label"], dtime(hour=item["hour"], minute=item["minute"], tzinfo=SGT), item["med"])
        for item in MED_SCHEDULE
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


@bot.event
async def on_command_error(ctx, error):
    print(f"Command error: {error}")
    try:
        await ctx.send(f"⚠️ There was an error: `{error}`")
    except Exception:
        pass


# =============== MAIN ===============

if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError(
            "DISCORD_BOT_TOKEN environment variable not set. "
            "Set it to your bot token before running."
        )
    bot.run(TOKEN)
