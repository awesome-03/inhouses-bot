import os
import aiohttp
from dotenv import load_dotenv

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database.models import ValorantAccount, Log
from database.connect import session
from helpers import get_or_create_user

load_dotenv()
VAL_API_KEY = os.getenv("VAL_API_KEY")
VAL_API_ENDPOINT = "https://api.henrikdev.xyz/valorant/v3/mmr"
RANK_ROLES = [
    "Unrated",
    "Iron 1",
    "Iron 2",
    "Iron 3",
    "Bronze 1",
    "Bronze 2",
    "Bronze 3",
    "Silver 1",
    "Silver 2",
    "Silver 3",
    "Gold 1",
    "Gold 2",
    "Gold 3",
    "Platinum 1",
    "Platinum 2",
    "Platinum 3",
    "Diamond 1",
    "Diamond 2",
    "Diamond 3",
    "Ascendant 1",
    "Ascendant 2",
    "Ascendant 3",
    "Immortal 1",
    "Immortal 2",
    "Immortal 3",
    "Radiant",
]


async def fetch_valorant_data(name: str, tag: str, region: str) -> dict | None:
    """Fetches account and rank data from the Valorant API asynchronously."""
    headers = {"Authorization": VAL_API_KEY}
    url = f"{VAL_API_ENDPOINT}/{region}/pc/{name}/{tag}"

    try:
        async with aiohttp.ClientSession() as sess:
            async with sess.get(url=url, headers=headers) as response:
                response.raise_for_status()
                data = (await response.json()).get("data")

                if not data or not data.get("current"):
                    print("API response missing 'data' or 'current' section.")
                    return None

                return {
                    "puuid": data.get("account", {}).get("puuid"),
                    "name": data.get("account", {}).get("name"),
                    "tag": data.get("account", {}).get("tag"),
                    "rank": data.get("current", {}).get("tier", {}).get("name"),
                }
    except aiohttp.ClientError as e:
        print(f"API request failed: {e}")
        return None


def upsert_valorant_account(
    sess: Session, discord_user: discord.User, val_data: dict, region: str
):
    """Creates or updates a user's linked Valorant account and logs the action."""
    get_or_create_user(sess, discord_user)

    db_account = sess.get(ValorantAccount, val_data["puuid"])

    if db_account:
        log = Log(action="LNK_upd", user_id=str(discord_user.id))
        sess.add(log)

        db_account.discord_id = str(discord_user.id)
        db_account.name = val_data["name"]
        db_account.tag = val_data["tag"]
        db_account.region = region
        db_account.current_rank = val_data["rank"]
        db_account.last_updated = func.now()
    else:
        log = Log(action="LNK_new", user_id=str(discord_user.id))
        sess.add(log)

        new_account = ValorantAccount(
            puuid=val_data["puuid"],
            discord_id=str(discord_user.id),
            name=val_data["name"],
            tag=val_data["tag"],
            region=region,
            current_rank=val_data["rank"],
        )
        sess.add(new_account)


class RankSetter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{__name__} is ready!")

    @app_commands.command(
        name="link_account",
        description="Links your Valorant account and sets your rank role.",
    )
    @app_commands.choices(
        region=[
            app_commands.Choice(name="Europe", value="eu"),
            app_commands.Choice(name="North America", value="na"),
            app_commands.Choice(name="Asia-Pacific", value="ap"),
            app_commands.Choice(name="Korea", value="kr"),
            app_commands.Choice(name="Brazil", value="br"),
            app_commands.Choice(name="Latin America", value="latam"),
        ]
    )
    async def link_account(
        self, interaction: discord.Interaction, ign: str, region: str
    ):
        await interaction.response.defer(ephemeral=True)

        try:
            name, tag = ign.split("#")
        except ValueError:
            await interaction.followup.send(
                "Invalid IGN format. Please use `Name#Tag`.", ephemeral=True
            )
            return

        valorant_data = await fetch_valorant_data(name, tag, region)

        if not valorant_data or not valorant_data.get("rank"):
            await interaction.followup.send(
                "Could not find your Valorant rank. Please check your IGN and region, or if your profile is private.",
                ephemeral=True,
            )
            return

        user_rank = valorant_data["rank"]
        member = interaction.user

        for rank_role_name in RANK_ROLES:
            role = discord.utils.get(interaction.guild.roles, name=rank_role_name)
            if role and role in member.roles:
                await member.remove_roles(role)

        try:
            new_rank_role = discord.utils.get(interaction.guild.roles, name=user_rank)
            linked_role = discord.utils.get(
                interaction.guild.roles, name="Linked Rank Role"
            )

            if new_rank_role:
                await member.add_roles(new_rank_role)
            if linked_role:
                await member.add_roles(linked_role)

            with session() as sess:
                upsert_valorant_account(sess, interaction.user, valorant_data, region)
                sess.commit()

            await interaction.followup.send(
                f"Your rank has been updated to **{user_rank}**!", ephemeral=True
            )
        except Exception as e:
            print(f"An error occurred: {e}")
            await interaction.followup.send(
                "An error occurred while assigning roles or saving data.",
                ephemeral=True,
            )

    @app_commands.command(
        name="unlink_account",
        description="Removes your rank roles and unlinks your Valorant account.",
    )
    async def unlink_account(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        with session() as sess:
            stmt = select(ValorantAccount).where(
                ValorantAccount.discord_id == str(interaction.user.id)
            )
            account_to_delete = sess.execute(stmt).scalar_one_or_none()

            if account_to_delete:
                log = Log(action="LNK_rmv", user_id=str(interaction.user.id))
                sess.add(log)

                sess.delete(account_to_delete)
                sess.commit()

        member = interaction.user
        for rank_role_name in RANK_ROLES:
            role = discord.utils.get(interaction.guild.roles, name=rank_role_name)
            if role and role in member.roles:
                await member.remove_roles(role)

        linked_role = discord.utils.get(
            interaction.guild.roles, name="Linked Rank Role"
        )
        if linked_role and linked_role in member.roles:
            await member.remove_roles(linked_role)

        await interaction.followup.send(
            "Your rank roles have been removed and your account has been unlinked.",
            ephemeral=True,
        )


async def setup(bot):
    await bot.add_cog(RankSetter(bot))
