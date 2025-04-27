import os
import time
import sqlite3
import discord
import requests
from dotenv import load_dotenv
from discord import app_commands
from discord.ext import commands

from database.models import Rank
from database.connect import session
from sqlalchemy import insert, update

load_dotenv()
VAL_API_KEY = os.getenv("VAL_API_KEY")
VAL_API_ENDPOINT = "https://api.henrikdev.xyz/valorant"
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


def load_to_db(username, ign, rank):
    with session() as sess:
        if sess.query(Rank).first() is None:
            sess.execute(insert(Rank).values(
                    username="",
                    ign="",
                    rank="",
                    last_update=int(time.time())
                )
            )
            return
        else:
            sess.execute(update(Rank).where(Rank.username == username).values(
                    ign=ign,
                    rank=rank,
                    last_update=int(time.time())
                )
            )
    

# def load_to_db(username, ign, rank):
#     connection = sqlite3.connect("data.db")
#     cursor = connection.cursor()

#     cursor.execute(f"SELECT * FROM ranks WHERE username = '{username}'")
#     connection.commit()

#     if cursor.fetchall() == []:
#         cursor.execute(
#             """INSERT INTO ranks VALUES (?, ?, ?, ?)""",
#             (username, ign, rank, int(time.time())),
#         )
#     else:
#         cursor.execute(
#             """UPDATE ranks SET ign = ?, rank = ?, last_update = ? WHERE username = ?""",
#             (ign, rank, int(time.time()), username),
#         )

#     connection.commit()

#     cursor.close()
#     connection.close()


class RankSetter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{__name__} is ready!")

    @app_commands.command(
        name="set_rank",
        description="Sets your roles according to the rank of your account.",
    )
    async def set_rank(self, interaction: discord.Interaction, ign: str):
        await interaction.response.defer(ephemeral=True)
        user_rank = get_rank(ign)

        for rank_role in RANK_ROLES:
            rank_id = discord.utils.get(interaction.guild.roles, name=rank_role)
            if rank_id is not None:
                await interaction.user.remove_roles(rank_id)
        await interaction.user.remove_roles(
            discord.utils.get(interaction.guild.roles, name="Linked Rank Role")
        )

        try:
            await interaction.user.add_roles(
                discord.utils.get(interaction.guild.roles, name=user_rank)
            )
            await interaction.user.add_roles(
                discord.utils.get(interaction.guild.roles, name="Linked Rank Role")
            )
            await interaction.followup.send(
                "Your rank has been updated!", ephemeral=True
            )
            load_to_db(interaction.user.name, ign, user_rank)
        except AttributeError as error:
            print(error)
            await interaction.followup.send("This rank does not exist", ephemeral=True)
        except Exception as e:
            print(e)
            await interaction.followup.send(e, ephemeral=True)


def get_rank(ign: str):
    """Returns the current rank of ign"""
    username = ign.split("#")
    header = {"accept": "application/json", "Authorization": VAL_API_KEY}
    acc_endpoint = f"{VAL_API_ENDPOINT}/v1/account/{username[0]}/{username[1]}"

    user_region: str
    user_puuid: str
    with requests.get(
        url=acc_endpoint, json={"force": True}, headers=header
    ) as response:
        response.raise_for_status()
        data = response.json()
        user_region = data["data"]["region"]
        user_puuid = data["data"]["puuid"]

    mmr_endpoint = f"{VAL_API_ENDPOINT}/v2/by-puuid/mmr/{user_region}/{user_puuid}"

    with requests.get(url=mmr_endpoint, headers=header) as response:
        response.raise_for_status()
        data = response.json()
        current_rank = data["data"]["current_data"]["currenttierpatched"]
        return current_rank


async def setup(bot):
    await bot.add_cog(RankSetter(bot))
