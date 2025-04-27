import time
import sqlite3
import discord
from discord import app_commands
from discord.ext import commands

from database.models import Command
from database.connect import session
from sqlalchemy import select, delete, insert, update

# def load_to_db(command, command_content, adder_username):
#     connection = sqlite3.connect("data.db")
#     cursor = connection.cursor()

#     cursor.execute("""INSERT INTO text_commands VALUES (?, ?, ?, ?)""", (command, command_content, adder_username, int(time.time())))
#     connection.commit()

#     cursor.close()
#     connection.close()



# def delete_from_db(command):
#     connection = sqlite3.connect("data.db")
#     cursor = connection.cursor()

#     cursor.execute("""DELETE FROM text_commands WHERE command = ?""", (command, ))
#     connection.commit()

#     cursor.close()
#     connection.close()

# def edit_db(command, command_content, adder_username):
#     connection = sqlite3.connect("data.db")
#     cursor = connection.cursor()

#     cursor.execute("""UPDATE text_commands SET command_content = ?, adder_username = ?, added_date = ? WHERE command = ?""", (command_content, adder_username, int(time.time()), command))
#     connection.commit()

#     cursor.close()
#     connection.close()


def read_db() -> dict:
    with session() as sess:
        rows = sess.execute(select(Command)).all() #TODO: This needs to be tested, might not work.

    formatted_dict = {}
    for row in rows:
        formatted_dict[row[0]] = row[1]
    
    return formatted_dict
    # connection = sqlite3.connect("data.db")
    # cursor = connection.cursor()

    # cursor.execute("""SELECT * FROM text_commands""")
    # rows = cursor.fetchall()

    # formatted_dict = {}
    # for row in rows:
    #     formatted_dict[row[0]] = row[1]

    # cursor.close()
    # connection.close()

    # return formatted_dict

added_commands = read_db()


class TextCommandsHandler(commands.Cog):
    def __init__(self, bot, added_cmds):
        self.bot = bot 
        self.added_commands = added_cmds
    
    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{__name__} is ready!")

    @app_commands.command(name="add_command", description="Adds a new prefix command")
    @app_commands.checks.has_permissions(administrator=True)
    async def add_cmd(self, interaction: discord.Interaction, new_command: str, command_message: str):
        cmd_exists: bool
        if new_command.lower() in self.added_commands:
            cmd_exists = True
        else:
            cmd_exists = False
        if cmd_exists:
            with session() as sess:
                sess.execute(update(Command).where(Command.command == new_command).values(
                    command_content=command_message,
                    adder_username=interaction.user.name,
                    added_date=int(time.time())
                ))
        else:
            with session() as sess:
                sess.execute(insert(Command).values(
                    command=new_command,
                    command_content=command_message,
                    adder_username=interaction.user.name,
                    added_date=int(time.time())
                ))

        self.added_commands[new_command.lower()] = command_message
        self.update_aliases()
        await interaction.response.send_message("Command has been added.", ephemeral=True)


    @app_commands.command(name="remove_command", description="Removes an existing prefix command")
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_cmd(self, interaction: discord.Interaction, command: str):
        try:
            self.added_commands.pop(command)
            self.update_aliases()
            await interaction.response.send_message("Command has been removed.", ephemeral=True)
            with session() as sess:
                sess.execute(delete(Command).where(Command.command == command))
        except KeyError:
            await interaction.response.send_message("That command does not exist.", ephemeral=True)

    @commands.command(name="commands")
    async def all_commands(self, ctx):
        """Sends all available commands"""
        await ctx.send(f"`{[key for key in self.added_commands]}`")

    @commands.command(aliases=list(added_commands.keys()))
    async def my_commands(self, ctx):
        """Sends a specific command"""
        await ctx.send(self.added_commands[ctx.invoked_with])
    
    def update_aliases(self):
        self.my_commands.update(aliases=[key for key, value in self.added_commands.items()])
        self.bot.remove_command("my_commands")
        self.bot.add_command(self.my_commands)


async def setup(bot):
    await bot.add_cog(TextCommandsHandler(bot, added_commands))
