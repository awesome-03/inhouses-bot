from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()
FALCON_USER_ID = str(os.getenv('FALCON_USER_ID'))


class FunStuff(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last_reaction = 0

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{__name__} is ready!")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Makes Falcon not be able to x react"""
        if payload.user_id == FALCON_USER_ID and payload.emoji.name == "❌":
            message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
            await message.remove_reaction(payload.emoji, payload.member)


async def setup(bot):
    await bot.add_cog(FunStuff(bot))
