import datetime
from sqlalchemy import (
    ForeignKey,
    String,
    Text,
    DateTime,
    func,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    type_annotation_map = {
        datetime.datetime: DateTime(timezone=True),
        dict: JSONB,
    }


class User(Base):
    __tablename__ = "users"

    discord_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str] = mapped_column(Text, nullable=False)

    valorant_account: Mapped["ValorantAccount"] = relationship(back_populates="user")
    auto_reacts: Mapped[list["AutoReact"]] = relationship(back_populates="user")


class ValorantAccount(Base):
    __tablename__ = "valorant_accounts"

    puuid: Mapped[str] = mapped_column(Text, primary_key=True)
    discord_id: Mapped[str] = mapped_column(
        ForeignKey("users.discord_id"), unique=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tag: Mapped[str] = mapped_column(String(255), nullable=False)
    region: Mapped[str] = mapped_column(String(10), nullable=False)
    platform: Mapped[str] = mapped_column(
        String(10), server_default="pc", nullable=False
    )
    current_rank: Mapped[str] = mapped_column(String(255), nullable=False)
    last_updated: Mapped[datetime.datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="valorant_account")
    performances: Mapped[list["PlayerPerformance"]] = relationship(
        back_populates="player"
    )

    __table_args__ = (
        UniqueConstraint("name", "tag", name="uq_valorant_account_name_tag"),
    )


class Match(Base):
    __tablename__ = "matches"

    match_id: Mapped[str] = mapped_column(Text, primary_key=True)
    queue_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    map_name: Mapped[str] = mapped_column(String(255), nullable=False)
    game_length_ms: Mapped[int] = mapped_column(nullable=False)
    game_start_time: Mapped[datetime.datetime] = mapped_column(nullable=False)
    region: Mapped[str] = mapped_column(String(10), nullable=False)
    platform: Mapped[str] = mapped_column(
        String(10), server_default="pc", nullable=False
    )
    winning_team: Mapped[str] = mapped_column(String(10), nullable=False)

    teams: Mapped[list["Team"]] = relationship(back_populates="match")
    performances: Mapped[list["PlayerPerformance"]] = relationship(
        back_populates="match"
    )


class Team(Base):
    __tablename__ = "teams"

    match_id: Mapped[str] = mapped_column(
        ForeignKey("matches.match_id"), primary_key=True
    )
    team_name: Mapped[str] = mapped_column(String(10), primary_key=True)

    rounds_won: Mapped[int] = mapped_column(nullable=False)
    rounds_lost: Mapped[int] = mapped_column(nullable=False)
    won_match: Mapped[bool] = mapped_column(nullable=False)

    match: Mapped["Match"] = relationship(back_populates="teams")


class PlayerPerformance(Base):
    __tablename__ = "player_performances"

    match_id: Mapped[str] = mapped_column(
        ForeignKey("matches.match_id"), primary_key=True
    )
    puuid: Mapped[str] = mapped_column(
        ForeignKey("valorant_accounts.puuid"), primary_key=True
    )

    team_name: Mapped[str] = mapped_column(String(10), nullable=False)
    agent_name: Mapped[str] = mapped_column(String(255), nullable=False)
    rank_at_match: Mapped[str] = mapped_column(String(255), nullable=False)
    score: Mapped[int] = mapped_column(nullable=False)
    kills: Mapped[int] = mapped_column(nullable=False)
    deaths: Mapped[int] = mapped_column(nullable=False)
    assists: Mapped[int] = mapped_column(nullable=False)
    headshots: Mapped[int] = mapped_column(nullable=False)
    bodyshots: Mapped[int] = mapped_column(nullable=False)
    legshots: Mapped[int] = mapped_column(nullable=False)
    damage_dealt: Mapped[int] = mapped_column(nullable=False)
    damage_received: Mapped[int] = mapped_column(nullable=False)
    ability_casts: Mapped[dict | None] = mapped_column(JSONB)
    economy: Mapped[dict | None] = mapped_column(JSONB)

    match: Mapped["Match"] = relationship(back_populates="performances")
    player: Mapped["ValorantAccount"] = relationship(back_populates="performances")


class Log(Base):
    __tablename__ = "logs"

    log_id: Mapped[int] = mapped_column(primary_key=True)
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    time: Mapped[datetime.datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )

    command: Mapped["Command"] = relationship(back_populates="log")
    auto_reacts: Mapped[list["AutoReact"]] = relationship(back_populates="log")


class Command(Base):
    __tablename__ = "commands"

    command: Mapped[str] = mapped_column(Text, primary_key=True)
    command_content: Mapped[str | None] = mapped_column(Text)
    log_id: Mapped[int] = mapped_column(ForeignKey("logs.log_id"), nullable=False)

    log: Mapped["Log"] = relationship(back_populates="command")


class AutoReact(Base):
    __tablename__ = "auto_reacts"

    reaction: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.discord_id"), primary_key=True
    )
    log_id: Mapped[int] = mapped_column(ForeignKey("logs.log_id"), nullable=False)

    user: Mapped["User"] = relationship(back_populates="auto_reacts")
    log: Mapped["Log"] = relationship(back_populates="auto_reacts")
