import os
import math
from dotenv import load_dotenv

import discord
from discord import app_commands
from discord.ext import commands

from database.models import Command, Log
from database.connect import session
from sqlalchemy import select, delete, insert, update
from helpers import get_or_create_user

load_dotenv()
COMMAND_PREFIX = os.getenv("COMMAND_PREFIX", "!")


def read_db() -> dict:
    """Reads all commands from the DB and returns them as a dictionary."""
    with session() as sess:
        command_list = sess.execute(select(Command).order_by(Command.command)).all()

    formatted_dict = {}
    for command_obj in command_list:
        command = command_obj[0]
        formatted_dict[command.command] = command.command_content

    return formatted_dict


def truncate(text: str, max_length: int = 25) -> str:
    """Shortens text to a max length and adds '...' if it was cut."""
    if len(text) > max_length:
        return text[:max_length].strip() + "..."
    return text


class CommandPaginator(discord.ui.View):
    """A view to handle pagination for the command list."""

    def __init__(self, commands_dict: dict, author: discord.User, prefix: str):
        super().__init__(timeout=180)
        self.commands = list(commands_dict.items())
        self.author = author
        self.prefix = prefix
        self.current_page = 0
        self.commands_per_page = 15
        self.total_pages = math.ceil(len(self.commands) / self.commands_per_page)
        self.update_buttons()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author.id:
            await interaction.response.send_message(
                "You can't interact with another user's command", ephemeral=True
            )
            return False
        return True

    def create_embed(self) -> discord.Embed:
        """Creates the embed for the current page."""
        start_index = self.current_page * self.commands_per_page
        end_index = start_index + self.commands_per_page
        page_commands = self.commands[start_index:end_index]

        description_list = []
        for name, content in page_commands:
            truncated_content = truncate(content)
            description_list.append(f"`{self.prefix}{name}` - {truncated_content}")

        embed = discord.Embed(
            title="Text Commands",
            description="\n".join(description_list),
            color=discord.Color.from_str("#c583ff"),
        )
        embed.set_footer(text=f"Page {self.current_page + 1} of {self.total_pages}")
        return embed

    def update_buttons(self):
        """Disables buttons when on the first or last page."""
        self.previous_page.disabled = self.current_page == 0
        self.next_page.disabled = self.current_page >= self.total_pages - 1

    @discord.ui.button(label="◀ Previous", style=discord.ButtonStyle.grey)
    async def previous_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.grey)
    async def next_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)


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
        if command.lower() not in self.added_commands:
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
        """Sends a paginated list of all available commands."""
        if not self.added_commands:
            await ctx.send("There are no text commands yet.")
            return

        paginator = CommandPaginator(self.added_commands, ctx.author, COMMAND_PREFIX)
        initial_embed = paginator.create_embed()

        await ctx.send(embed=initial_embed, view=paginator)

    @commands.command(aliases=list(read_db().keys()))
    async def my_commands(self, ctx):
        """Sends a specific command"""
        await ctx.send(self.added_commands[ctx.invoked_with])

    def update_aliases(self):
        """Method to reload the bot's prefix commands."""
        self.my_commands.update(aliases=list(self.added_commands.keys()))
        self.bot.remove_command("my_commands")
        self.bot.add_command(self.my_commands)


async def setup(bot):
    await bot.add_cog(TextCommandsHandler(bot, read_db()))
