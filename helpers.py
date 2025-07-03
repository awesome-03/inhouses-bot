import discord
from database.models import User
from sqlalchemy.orm import Session


def get_or_create_user(sess: Session, user: discord.Member | discord.User) -> User:
    """
    Checks if a user exists in the database. If so, returns them.
    If not, creates them and returns the new record.
    """
    db_user = sess.get(User, str(user.id))
    if db_user:
        db_user.username = user.name
        db_user.avatar_url = str(
            user.avatar.url if user.avatar else user.default_avatar.url
        )
        return db_user
    else:
        new_user = User(
            discord_id=str(user.id),
            username=user.name,
            avatar_url=str(user.avatar.url if user.avatar else user.default_avatar.url),
        )
        sess.add(new_user)
        return new_user