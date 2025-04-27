import time

import discord
from discord import app_commands
from discord.ext import commands

from database.models import Command
from database.connect import session
from sqlalchemy import select, delete, insert, update


def read_db() -> dict:
    with session() as sess:
        command_list = sess.execute(select(Command)).all()

    formatted_dict = {}
    for command in command_list:
        formatted_dict[command[0].command] = command[0].command_content

    return formatted_dict


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
    async def add_cmd(
        self, interaction: discord.Interaction, new_command: str, command_message: str
    ):
        cmd_exists: bool
        if new_command.lower() in self.added_commands:
            cmd_exists = True
        else:
            cmd_exists = False
        if cmd_exists:
            with session() as sess:
                sess.execute(
                    update(Command)
                    .where(Command.command == new_command)
                    .values(
                        command_content=command_message,
                        adder_username=interaction.user.name,
                        added_date=int(time.time()),
                    )
                )
                sess.commit()
        else:
            with session() as sess:
                sess.execute(
                    insert(Command).values(
                        command=new_command,
                        command_content=command_message,
                        adder_username=interaction.user.name,
                        added_date=int(time.time()),
                    )
                )
                sess.commit()

        self.added_commands[new_command.lower()] = command_message
        self.update_aliases()
        await interaction.response.send_message(
            "Command has been added.", ephemeral=True
        )

    @app_commands.command(
        name="remove_command", description="Removes an existing prefix command"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_cmd(self, interaction: discord.Interaction, command: str):
        try:
            self.added_commands.pop(command)
            self.update_aliases()
            await interaction.response.send_message(
                "Command has been removed.", ephemeral=True
            )
            with session() as sess:
                sess.execute(delete(Command).where(Command.command == command))
                sess.commit()
        except KeyError:
            await interaction.response.send_message(
                "That command does not exist.", ephemeral=True
            )

    @commands.command(name="commands")
    async def all_commands(self, ctx):
        """Sends all available commands"""
        await ctx.send(f"`{[key for key in self.added_commands]}`")

    @commands.command(aliases=list(added_commands.keys()))
    async def my_commands(self, ctx):
        """Sends a specific command"""
        await ctx.send(self.added_commands[ctx.invoked_with])

    def update_aliases(self):
        self.my_commands.update(
            aliases=[key for key, value in self.added_commands.items()]
        )
        self.bot.remove_command("my_commands")
        self.bot.add_command(self.my_commands)


async def setup(bot):
    await bot.add_cog(TextCommandsHandler(bot, added_commands))
