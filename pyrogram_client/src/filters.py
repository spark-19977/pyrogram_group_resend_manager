from pyrogram import filters
from sqlalchemy import select

from src.db.models import Base, Chat


async def _chats_filter(_, __, m):
    async with Base.session() as session:
        chats = await session.scalars(select(Chat))
        chats = chats.all()
        for chat in chats:
            if m.chat.id == chat.id:
                return True
        return False


chats_filter = filters.create(_chats_filter)
