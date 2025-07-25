import os
import asyncio
import logging
import logging.handlers
from dotenv import load_dotenv

import discord
from discord.ext import commands

load_dotenv()
DISCORD_TOKEN = str(os.getenv("DISCORD_TOKEN"))

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

logger = logging.getLogger("discord")
logger.setLevel(logging.DEBUG)
logging.getLogger("discord.http").setLevel(logging.INFO)

handler = logging.handlers.RotatingFileHandler(
    filename="logs/discord.log",
    encoding="utf-8",
    maxBytes=32 * 1024 * 1024,  # 32 MiB
    backupCount=5,
)
dt_fmt = "%Y-%m-%d %H:%M:%S"
formatter = logging.Formatter(
    "[{asctime}] [{levelname:<8}] {name}: {message}", dt_fmt, style="{"
)
handler.setFormatter(formatter)
logger.addHandler(handler)


@bot.event
async def on_ready():
    print("Bot is online!")
    # Uncomment these lines to sync commands on startup:

    # try:
    #     synced_commands = await bot.tree.sync()
    #     print(f"Synced {len(synced_commands)} commands.")
    # except Exception as e:
    #     print("An error with syncing application commands has occurred: ", e)


async def load():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            await bot.load_extension(f"cogs.{filename[:-3]}")


async def main():
    async with bot:
        await load()
        await bot.start(token=DISCORD_TOKEN)


asyncio.run(main())
