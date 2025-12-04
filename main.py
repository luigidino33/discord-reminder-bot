import os
import discord
from discord.ext import commands, tasks
from datetime import time as dtime
from zoneinfo import ZoneInfo  # Python 3.9+

# ====== CONFIGURE THESE ======
TOKEN = os.getenv("DISCORD_BOT_TOKEN")  # environment variable
CHANNEL_ID = 1370117597416394774        # replace with the ID of the channel to send reminders in
USER_ID = 753101826920022126
# ==============================

intents = discord.Intents.default()
intents.message_content = False  # set to True only if you add commands later
bot = commands.Bot(command_prefix="!", intents=intents)

SGT = ZoneInfo("Asia/Singapore")


async def send_reminder(message: str):
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


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")

    # Start all loops
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

    # 🔥 SEND STARTUP MESSAGE
    await send_reminder("✅ Bot is online! Med reminder schedule loaded. 💊")


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
    msg = f"⏰ <@{USER_ID}> 6:00 PM Pantec-DSR time! 💊"
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


if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError(
            "DISCORD_BOT_TOKEN environment variable not set. "
            "Set it to your bot token before running."
        )
    bot.run(TOKEN)
