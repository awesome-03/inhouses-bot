import os
import time
from dotenv import load_dotenv

import discord
from discord.ext import commands
from discord import app_commands

from database.models import AutoReact, User, Log
from database.connect import session
from sqlalchemy import select, delete
from helpers import get_or_create_user

load_dotenv()
REACTION_COOLDOWN = int(os.getenv("REACTION_COOLDOWN", 7))

def read_all() -> str:
    with session() as sess:
        reaction_list = sess.execute(
            select(AutoReact.reaction, User.username)
            .join(User, AutoReact.user_id == User.discord_id)
            .order_by(User.username)
        ).all()
    formatted_reacts = []
    for reaction in reaction_list:
        formatted_reacts.append(
            f"reaction: {reaction[0]}, username: {reaction[1].replace('_', '\\_')}"
        )

    formatted_response = ""
    for row in formatted_reacts:
        formatted_response += f"{row}\n"

    return formatted_response


def read_reactions() -> list:
    with session() as sess:
        reaction_list = sess.execute(
            select(AutoReact.reaction, AutoReact.user_id)
        ).all()
    formatted_reacts = []
    for reaction in reaction_list:
        formatted_reacts.append((int(reaction[1]), reaction[0]))

    return formatted_reacts


auto_reacts = read_reactions()


class AutoReacts(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last_reaction = 0

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{__name__} is ready!")

    # TODO: Check if the reaction is valid before adding it
    # TODO: There was a bug with the last code, find and fix
    @app_commands.command(
        name="add_reaction", description="Adds a reaction to a message"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def add_reaction(
        self, interaction: discord.Interaction, user: discord.Member, reaction: str
    ):
        global auto_reacts
        await interaction.response.defer(ephemeral=True)
        if (user.id, reaction) in auto_reacts:
            await interaction.followup.send(
                f"{user.mention} already has that reaction", ephemeral=True
            )
        else:
            auto_reacts.append((user.id, reaction))
            with session() as sess:
                get_or_create_user(sess, user)

                new_log = Log(action="RCT_add", user_id=str(interaction.user.id))
                sess.add(new_log)
                sess.flush()

                new_react = AutoReact(
                    reaction=reaction, user_id=str(user.id), log_id=new_log.log_id
                )
                sess.add(new_react)
                sess.commit()
            await interaction.followup.send(
                f"Successfully added reaction to {user.mention}", ephemeral=True
            )

    @app_commands.command(
        name="remove_reaction", description="Removes a reaction from a message"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_reaction(
        self, interaction: discord.Interaction, user: discord.Member, reaction: str
    ):
        global auto_reacts
        await interaction.response.defer(ephemeral=True)
        try:
            with session() as sess:
                get_or_create_user(sess, interaction.user)

                new_log = Log(action="RCT_rmv", user_id=str(interaction.user.id))
                sess.add(new_log)
                sess.execute(
                    delete(AutoReact).where(
                        AutoReact.user_id == str(user.id),
                        AutoReact.reaction == reaction,
                    )
                )
                sess.commit()
            auto_reacts.remove((user.id, reaction))
            await interaction.followup.send(
                f"Successfully removed reaction from {user.mention}", ephemeral=True
            )
        except ValueError:
            await interaction.followup.send(
                f"{user.mention} does not have that reaction", ephemeral=True
            )

    @app_commands.command(name="list_reactions", description="Lists all reactions")
    @app_commands.checks.has_permissions(administrator=True)
    async def list_reactions(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send(f"{read_all()}", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        if time.time() > self.last_reaction + REACTION_COOLDOWN:
            for user_id, reaction in auto_reacts:
                if message.author.id == user_id:
                    if ":" in reaction:
                        try:
                            emoji = message.guild.get_emoji(
                                int(reaction.split(":")[2][:-1])
                            )
                        except (IndexError, ValueError):
                            emoji = None
                            print(f"Something went wrong with reaction: {reaction}")
                    else:
                        emoji = reaction

                    if emoji:
                        await message.add_reaction(emoji)
                    self.last_reaction = time.time()


async def setup(bot):
    await bot.add_cog(AutoReacts(bot))
