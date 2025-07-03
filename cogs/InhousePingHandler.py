# So here is some AI slop for ya... Test extensively.
# TODO: Check if the ping is an actual ping and not just the id in ``` like this ```
# TODO: Did not make sure that the role is in the guild before adding it to the logs
# TODO: Didn't test if the timer works, or how it behaves whenever there is a ping while the cooldown is on.
import os
import time
from dotenv import load_dotenv
import asyncio

import discord
from discord.ext import commands

from database.models import Log
from database.connect import session

load_dotenv()
INHOUSE_PING_ROLE_ID = str(os.getenv("INHOUSE_PING_ROLE_ID"))

PING_COOLDOWN = 60 # in seconds


class InhousePingHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._ping_lock = asyncio.Lock()
        self.last_mention = 0

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{__name__} is ready!")

    async def ping_cooldown_task(self, role: discord.Role):
        await asyncio.sleep(PING_COOLDOWN)
        async with self._ping_lock:
            if time.time() - self.last_mention >= PING_COOLDOWN:
                await role.edit(mentionable=True)
                print(f"Re-enabled mentions for role '{role.name}'")

    @commands.Cog.listener()
    async def on_message(self, message):
        """Disables the inhouse ping role for 1 hour after it's used."""
        if not message.guild or message.author.bot:
            return

        if f"<@&{INHOUSE_PING_ROLE_ID}>" in message.content:
            if self._ping_lock.locked():
                return

            async with self._ping_lock:
                self.last_mention = time.time()

                with session() as sess:
                    new_log = Log(action="PNG", user_id=str(message.author.id))
                    sess.add(new_log)
                    sess.commit()

                role = message.guild.get_role(int(INHOUSE_PING_ROLE_ID))
                if not role:
                    print(f"Error: Role with ID {INHOUSE_PING_ROLE_ID} not found.")
                    return

                await role.edit(mentionable=False)
                print(f"Disabled mentions for role '{role.name}'")

                self.bot.loop.create_task(self.ping_cooldown_task(role))


async def setup(bot):
    await bot.add_cog(InhousePingHandler(bot))
