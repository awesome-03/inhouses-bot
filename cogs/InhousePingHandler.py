import os
import time
from dotenv import load_dotenv

import discord
from discord.ext import commands

from database.models import PingLog
from database.connect import session
from sqlalchemy import insert

load_dotenv()
INHOUSE_PING_ROLE_ID = str(os.getenv('INHOUSE_PING_ROLE_ID'))

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
            with session() as sess:
                sess.execute(insert(PingLog).values(pinged_by=message.author.name, ping_time=int(time.time())))
                sess.commit()
            role = discord.utils.get(message.guild.roles, name="Inhouse Ping")
            await role.edit(mentionable=False)


async def setup(bot):
    await bot.add_cog(InhousePingHandler(bot))
