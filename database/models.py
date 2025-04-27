from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Command(Base):
    __tablename__ = "text_commands"
    command: Mapped[str] = mapped_column(primary_key=True)
    command_content: Mapped[str]
    adder_username: Mapped[str]
    added_date: Mapped[int]


class Rank(Base):
    __tablename__ = "ranks"
    username: Mapped[str] = mapped_column(primary_key=True)
    ign: Mapped[str]
    rank: Mapped[str]
    last_update: Mapped[int]


class PingLog(Base):
    __tablename__ = "ping_logs"
    pinged_by: Mapped[str] = mapped_column(primary_key=True)
    ping_time: Mapped[int] = mapped_column(primary_key=True)


class AutoReact(Base):
    __tablename__ = "auto_reacts"
    reaction: Mapped[str] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(primary_key=True)
    user_name: Mapped[str]
    added_by: Mapped[str]
    added_date: Mapped[int]
