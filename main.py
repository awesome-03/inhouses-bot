import asyncio
import discord
import os
from dotenv import load_dotenv
from discord.ext import commands
from database.models import Base
from database.connect import engine

if not os.path.isfile("database/database.db"):
    try:
        print("Creating tables...")
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print("An error occurred while creating tables: ", e)
    else:
        print("Tables created successfully.")


load_dotenv()
DISCORD_TOKEN = str(os.getenv('DISCORD_TEST_TOKEN')) 

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())

@bot.event
async def on_ready():
    print("Bot is online!")
    # try:
    #     synced_commands = await bot.tree.sync()
    #     print(f"Synced {len(synced_commands)} commands.")
    # except Exception as e:
    #     print("An error with syncing application commands has occurred: ", e)

    # Uncomment the following line to sync commands on startup

async def load():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            await bot.load_extension(f"cogs.{filename[:-3]}")


async def main():
    async with bot:
        await load()
        await bot.start(token=DISCORD_TOKEN)


asyncio.run(main())
