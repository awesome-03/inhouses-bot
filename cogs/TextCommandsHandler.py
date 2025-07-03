import discord
from discord import app_commands
from discord.ext import commands

from database.models import Command, Log
from database.connect import session
from sqlalchemy import select, delete, insert, update
from helpers import get_or_create_user


def read_db() -> dict:
    with session() as sess:
        command_list = sess.execute(select(Command)).all()
        print(command_list)

    formatted_dict = {}
    for command_obj in command_list:
        command = command_obj[0]
        formatted_dict[command.command] = command.command_content

    return formatted_dict


added_commands = read_db()


class TextCommandsHandler(commands.Cog):
    def __init__(self, bot, added_cmds):
        self.bot = bot
        self.added_commands = added_cmds

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{__name__} is ready!")

    @app_commands.command(
        name="add_command", description="Adds or updates a prefix command"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def add_cmd(
        self, interaction: discord.Interaction, new_command: str, command_message: str
    ):
        cmd_exists = new_command.lower() in self.added_commands

        with session() as sess:
            log_action = "CMD_upd" if cmd_exists else "CMD_add"

            new_log = Log(action=log_action, user_id=str(interaction.user.id))
            sess.add(new_log)
            sess.flush()

            if cmd_exists:
                sess.execute(
                    update(Command)
                    .where(Command.command == new_command)
                    .values(command_content=command_message, log_id=new_log.log_id)
                )
            else:
                sess.execute(
                    insert(Command).values(
                        command=new_command,
                        command_content=command_message,
                        log_id=new_log.log_id,
                    )
                )
            sess.commit()

        self.added_commands[new_command.lower()] = command_message
        self.update_aliases()
        response_message = (
            "Command has been updated." if cmd_exists else "Command has been added."
        )
        await interaction.response.send_message(response_message, ephemeral=True)

    @app_commands.command(
        name="remove_command", description="Removes an existing prefix command"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_cmd(self, interaction: discord.Interaction, command: str):
        if command not in self.added_commands:
            await interaction.response.send_message(
                "That command does not exist.", ephemeral=True
            )
            return

        self.added_commands.pop(command.lower())
        self.update_aliases()

        with session() as sess:
            get_or_create_user(sess, interaction.user)
            new_log = Log(action="CMD_rmv", user_id=str(interaction.user.id))
            sess.add(new_log)
            sess.execute(delete(Command).where(Command.command == command))
            sess.commit()

        await interaction.response.send_message(
            "Command has been removed.", ephemeral=True
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
        self.my_commands.update(aliases=list(self.added_commands.keys()))
        self.bot.remove_command("my_commands")
        self.bot.add_command(self.my_commands)


async def setup(bot):
    await bot.add_cog(TextCommandsHandler(bot, added_commands))
