import re
import aiohttp

import os
from dotenv import load_dotenv

import time
from datetime import datetime

import discord
from discord.ext import commands

from database.models import ValorantAccount, Match, Team, PlayerPerformance, Log
from database.connect import session
from sqlalchemy import select
from sqlalchemy.orm import Session

load_dotenv()
QUEUE_CHANNELS = [
    int(channel_id) for channel_id in os.getenv("QUEUE_CHANNELS").split("-")
]
NEATQUEUE_BOT_ID = int(os.getenv("NEATQUEUE_BOT_ID"))
VAL_API_KEY = os.getenv("VAL_API_KEY")
VAL_API_BASE_URL = "https://api.henrikdev.xyz/valorant"


def parse_match_embed(embed: discord.Embed) -> dict | None:
    queue_id_match = re.search(r"#(\d+)", embed.title)
    if not queue_id_match:
        return None
    queue_id = int(queue_id_match.group(1))
    pattern = re.compile(r"<@(\d+)>.*?([+-]?\d+\.\d+).*?(\d+\.\d+)")
    all_players = []
    for field in embed.fields:
        is_winner = field.name.startswith("_") and field.name.endswith("_")
        team_name = field.name.strip("_")
        for line in field.value.split("\n"):
            match = pattern.search(line)
            if match:
                player_data = {
                    "team": team_name,
                    "won": is_winner,
                    "player_id": int(match.group(1)),
                    "elo_change": float(match.group(2)),
                    "new_elo": float(match.group(3)),
                }
                all_players.append(player_data)
    return {"queue_id": queue_id, "players": all_players}


async def fetch_latest_custom_match(player: ValorantAccount) -> dict | None:
    url = f"{VAL_API_BASE_URL}/v4/by-puuid/matches/eu/pc/{player.puuid}?mode=custom&size=1"
    headers = {"Authorization": VAL_API_KEY}
    async with aiohttp.ClientSession() as sess:
        async with sess.get(url, headers=headers) as res:
            if res.status != 200:
                print(f"API Error: Status {res.status}")
                return None
            data = await res.json()
            return data.get("data", [])[0] if data.get("data") else None


async def find_and_validate_match(known_players: list[ValorantAccount]) -> dict | None:
    eu_players = [player for player in known_players if player.region == "eu"]
    if not eu_players:
        print("No known EU players from this queue found in the database.")
        return None
    for player in eu_players:
        print(f"Checking match history for player: {player.name}...")
        latest_match = await fetch_latest_custom_match(player)
        if not latest_match:
            continue
        metadata = latest_match.get("metadata", {})
        queue_name = metadata.get("queue", {}).get("name")
        if queue_name != "Custom Game":
            continue
        game_start_iso = metadata.get("started_at")
        game_length_ms = metadata.get("game_length_in_ms")
        if not all([game_start_iso, game_length_ms]):
            continue
        game_start_dt = datetime.fromisoformat(game_start_iso.replace("Z", "+00:00"))
        match_end_ms = (game_start_dt.timestamp() * 1000) + game_length_ms
        time_since_end = (time.time() * 1000) - match_end_ms
        if time_since_end > (15 * 60 * 1000):
            continue
        print(
            f"  -> Found and validated the correct match from {player.name}'s history!"
        )
        return latest_match
    print("Checked all known EU players, but no recent, valid custom match was found.")
    return None


def save_match_data(sess: Session, match_data: dict, queue_id: int, bot_user_id: int):
    """Saves all match, team, and player performance data in a single transaction."""
    metadata = match_data["metadata"]
    match_id = metadata["match_id"]

    if sess.get(Match, match_id):
        print(f"Match {match_id} already exists in the database.")
        return

    # Create the match record
    new_match = Match(
        match_id=match_id,
        queue_id=str(queue_id),
        map_name=metadata["map"]["name"],
        game_length_ms=metadata["game_length_in_ms"],
        game_start_time=datetime.fromisoformat(
            metadata["started_at"].replace("Z", "+00:00")
        ),
        # region=metadata["region"],
        # platform=metadata["platform"],
        region="eu",
        winning_team=(team["team_id"] for team in match_data["teams"] if team["won"]),
    )
    sess.add(new_match)

    # Create the team records
    for team_data in match_data["teams"]:
        new_team = Team(
            match_id=match_id,
            team_name=team_data["team_id"],
            rounds_won=team_data["rounds"]["won"],
            rounds_lost=team_data["rounds"]["lost"],
            won_match=team_data["won"], # TODO: Why the hell did I put this in 2 places?
        )
        sess.add(new_team)

    # Create all PlayerPerformance records
    for player_data in match_data["players"]:
        stats = player_data["stats"]
        new_performance = PlayerPerformance(
            match_id=match_id,
            puuid=player_data["puuid"],
            team_name=player_data["team_id"],
            agent_name=player_data["agent"]["name"],
            rank_at_match=player_data["tier"]["name"],
            score=stats["score"],
            kills=stats["kills"],
            deaths=stats["deaths"],
            assists=stats["assists"],
            headshots=stats["headshots"],
            bodyshots=stats["bodyshots"],
            legshots=stats["legshots"],
            damage_dealt=stats["damage"]["dealt"],
            damage_received=stats["damage"]["received"],
            ability_casts=player_data.get("ability_casts"),
            economy=player_data.get("economy"),
        )
        sess.add(new_performance)

    # Log the action
    log = Log(action="MCH_add", user_id=str(bot_user_id))
    sess.add(log)

    print(f"Successfully prepared match {match_id} for database insertion.")


class MatchDetectionHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{__name__} is ready!")

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload):
        if payload.channel_id not in QUEUE_CHANNELS:
            return

        try:
            embed_data = payload.data.get("embeds", [])[0]
            author_id = int(payload.data.get("author", {}).get("id", 0))
            if author_id != NEATQUEUE_BOT_ID:
                return
        except (IndexError, TypeError, ValueError):
            return

        embed = discord.Embed.from_dict(embed_data)

        if embed.title and "Winner For Queue" in embed.title:
            parsed_data = parse_match_embed(embed)
            if not parsed_data:
                return

            print(f"--- Match Detected (Queue ID: {parsed_data['queue_id']}) ---")

            player_discord_ids = [str(p["player_id"]) for p in parsed_data["players"]]
            with session() as sess:
                stmt = select(ValorantAccount).where(
                    ValorantAccount.discord_id.in_(player_discord_ids)
                )
                known_players = sess.execute(stmt).scalars().all()

            if not known_players:
                print("No known players found in the database.")
                return

            validated_match = await find_and_validate_match(known_players)

            if validated_match:
                print("✅ Match validated! Attempting to save data to database...")
                with session() as sess:
                    save_match_data(
                        sess, validated_match, parsed_data["queue_id"], self.bot.user.id
                    )
                    sess.commit()
            else:
                print("❌ Match validation failed.")


async def setup(bot):
    await bot.add_cog(MatchDetectionHandler(bot))
