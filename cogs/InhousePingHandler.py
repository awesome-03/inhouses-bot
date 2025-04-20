import time
import sqlite3
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()
INHOUSE_PING_ROLE_ID = str(os.getenv('INHOUSE_PING_ROLE_ID'))


def log_pings(pinged_by, ping_time):
    connection = sqlite3.connect("data.db")
    cursor = connection.cursor()

    cursor.execute("""INSERT INTO ping_logs VALUES (?, ?)""", (pinged_by, ping_time))
    connection.commit()

    cursor.close()
    connection.close()

# Here I should implement an actual timer instead of listening to messages 
class InhousePingHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last_mention = 0
    
    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{__name__} is ready!")

    @commands.Cog.listener()
    async def on_message(self, message):
        """Adds a 1 hour cooldown on the inhouse ping role"""
        if time.time() - self.last_mention >= 3600:
            role = discord.utils.get(message.guild.roles, name="Inhouse Ping")
            await role.edit(mentionable=True)
        if f"<@&{INHOUSE_PING_ROLE_ID}>" in message.content:
            self.last_mention = time.time()
            log_pings(message.author.name, int(time.time()))
            role = discord.utils.get(message.guild.roles, name="Inhouse Ping")
            await role.edit(mentionable=False)


async def setup(bot):
    await bot.add_cog(InhousePingHandler(bot))
