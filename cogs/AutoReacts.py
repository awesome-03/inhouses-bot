import time

import discord
from discord.ext import commands
from discord import app_commands

from database.models import AutoReact
from database.connect import session
from sqlalchemy import select, delete, insert

def read_all() -> str:
    with session() as sess:
        reaction_list = sess.execute(select(AutoReact.reaction, AutoReact.user_name)).all()
    formatted_reacts = []
    for reaction in reaction_list:
        formatted_reacts.append(f"reaction: {reaction[0]}, username: {reaction[1].replace("_", "\\_")}")
    
    formatted_response = ""
    for row in formatted_reacts:
        formatted_response += f"{row}\n"

    return formatted_response

def read_reactions() -> list:
    with session() as sess:
        reaction_list = sess.execute(select(AutoReact.reaction, AutoReact.user_id)).all()
    formatted_reacts = []
    for reaction in reaction_list:
        formatted_reacts.append((reaction[1], reaction[0]))

    return formatted_reacts

auto_reacts = read_reactions()


class AutoReacts(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last_reaction = 0

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{__name__} is ready!")

    @app_commands.command(name="add_reaction", description="Adds a reaction to a message")
    @app_commands.checks.has_permissions(administrator=True)
    async def add_reaction(self, interaction: discord.Interaction, user: discord.Member, reaction: str):
        global auto_reacts
        await interaction.response.defer(ephemeral=True)
        if (user.id, reaction) in auto_reacts:
            await interaction.followup.send(f"{user.mention} already has that reaction", ephemeral=True)
        else:
            auto_reacts.append((user.id, reaction))
            with session() as sess:
                sess.execute(insert(AutoReact).values(
                    reaction=reaction,
                    user_id=user.id,
                    user_name=user.name,
                    added_by=interaction.user.name,
                    added_date=int(time.time())
                    ))
                sess.commit()
            await interaction.followup.send(f"Successfully added reaction to {user.mention}", ephemeral=True)

    @app_commands.command(name="remove_reaction", description="Removes a reaction from a message")
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_reaction(self, interaction: discord.Interaction, user: discord.Member, reaction: str):
        global auto_reacts
        await interaction.response.defer(ephemeral=True)
        try:
            with session() as sess:
                sess.execute(delete(AutoReact).where(AutoReact.user_id==user.id, AutoReact.reaction==reaction))
                sess.commit()
            auto_reacts.remove((user.id, reaction))
            await interaction.followup.send(f"Successfully removed reaction from {user.mention}", ephemeral=True)
        except ValueError:
            await interaction.followup.send(f"{user.mention} does not have that reaction", ephemeral=True)

    @app_commands.command(name="list_reactions", description="Lists all reactions")
    @app_commands.checks.has_permissions(administrator=True)
    async def list_reactions(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send(f"{read_all()}", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message):
        if time.time() > self.last_reaction + 7:
            for user_id, reaction in auto_reacts:
                if message.author.id == user_id:
                    if ":" in reaction:
                        emoji = message.guild.get_emoji(int(reaction.split(":")[2][:-1]))
                    else: 
                        emoji = reaction
                    await message.add_reaction(emoji)
                    self.last_reaction = time.time()


async def setup(bot):
    await bot.add_cog(AutoReacts(bot))
