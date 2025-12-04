import os
import discord
from discord.ext import commands, tasks
from datetime import time as dtime
from zoneinfo import ZoneInfo  # Python 3.9+

# ====== CONFIGURE THESE ======
TOKEN = os.getenv("DISCORD_BOT_TOKEN")  # put your token in an env variable
CHANNEL_ID = 1370117597416394774        # replace with the ID of the channel to send reminders in
USER_ID = 753101826920022126
REMINDER_MESSAGE = f"⏰ <@{USER_ID}> meds time! Please remember to take your medicine 💊"

# ==============================

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

SGT = ZoneInfo("Asia/Singapore")

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    if not med_reminder.is_running():
        med_reminder.start()
    print("Med reminder loop started.")

# This loop runs every day at 11:00 and 18:00 SGT
@tasks.loop(
    time=[
        dtime(hour=0, minute=40, tzinfo=SGT),  # 6:00 SGT
        dtime(hour=11, minute=0, tzinfo=SGT),  # 11:00 SGT
        dtime(hour=18, minute=0, tzinfo=SGT),  # 18:00 / 6 PM SGT
    ]
)
async def med_reminder():
    channel = bot.get_channel(CHANNEL_ID)
    if channel is None:
        # Fallback: try fetching the channel (e.g., if not in cache yet)
        try:
            channel = await bot.fetch_channel(CHANNEL_ID)
        except Exception as e:
            print(f"Could not find channel {CHANNEL_ID}: {e}")
            return

    try:
        await channel.send(REMINDER_MESSAGE)
        print("Sent med reminder.")
    except Exception as e:
        print(f"Failed to send reminder: {e}")


if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError(
            "DISCORD_BOT_TOKEN environment variable not set. "
            "Set it to your bot token before running."
        )
    bot.run(TOKEN)
