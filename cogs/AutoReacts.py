import time
import sqlite3
import discord
from discord.ext import commands
from discord import app_commands

def load_to_db(reaction, user_id, user_name, added_by):
    connection = sqlite3.connect("data.db")
    cursor = connection.cursor()

    cursor.execute("""INSERT INTO auto_reacts VALUES (?, ?, ?, ?, ?)""", (reaction, user_id, user_name, added_by, int(time.time())))
    connection.commit()

    cursor.close()
    connection.close()


def delete_from_db(reaction, user_id):
    connection = sqlite3.connect("data.db")
    cursor = connection.cursor()

    cursor.execute("""DELETE FROM auto_reacts WHERE reaction = ? AND user_id = ?""", (reaction, user_id))
    connection.commit()

    cursor.close()
    connection.close()


def read_all() -> str:
    connection = sqlite3.connect("data.db")
    cursor = connection.cursor()

    cursor.execute("""SELECT reaction, user_name FROM auto_reacts""")
    rows = cursor.fetchall()

    formatted_reacts = []
    for row in rows:
        formatted_reacts.append(f"reaction: {row[0]}, username: {row[1].replace("_", "\\_")}")
    
    formatted_response = ""
    for row in formatted_reacts:
        formatted_response += f"{row}\n"

    cursor.close()
    connection.close()

    return formatted_response


def read_reactions() -> list:
    connection = sqlite3.connect("data.db")
    cursor = connection.cursor()

    cursor.execute("""SELECT reaction, user_id FROM auto_reacts""")
    rows = cursor.fetchall()

    formatted_reacts = []
    for row in rows:
        formatted_reacts.append((row[1], row[0]))

    cursor.close()
    connection.close()

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
            load_to_db(reaction, user.id, user.name, interaction.user.name)
            await interaction.followup.send(f"Successfully added reaction to {user.mention}", ephemeral=True)

    @app_commands.command(name="remove_reaction", description="Removes a reaction from a message")
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_reaction(self, interaction: discord.Interaction, user: discord.Member, reaction: str):
        global auto_reacts
        await interaction.response.defer(ephemeral=True)
        try:
            auto_reacts.remove((user.id, reaction))
            delete_from_db(reaction, user.id)
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
