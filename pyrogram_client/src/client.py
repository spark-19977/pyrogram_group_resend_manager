import asyncio
import logging
import os
import re
from datetime import datetime, timedelta

from pyrogram import Client, raw
from apscheduler.schedulers.asyncio import AsyncIOScheduler as Scheduler
from pyrogram.errors import PhoneNumberInvalid
from sqlalchemy import select, update

from settings import settings
from src.redis import redis, RedisKeys
from .db.models import Base, Keyword, Chat
from .filters import chats_filter
from .scheduler_task import answer_in


class Application:
    def __init__(self):
        self.client = Client(name='main', api_id=settings.api_id, api_hash=settings.api_hash)
        self.scheduler = Scheduler()
        self.scheduler.start()

    async def initialize_pyrogram(self):
        if not self.client.is_connected:
            await self.client.connect()

        await self.on_message_handler()
        await self.client.invoke(raw.functions.updates.GetState())
        await self.client.initialize()
        await self.client.send_message('me', 'started')

        await redis.set(RedisKeys.ready_to_connect, 1)
        await redis.set(RedisKeys.authed, 1)

    async def on_message_handler(self):
        @self.client.on_message(chats_filter)
        async def read_message(client, message):
            logging.info('callback receive')
            async with Base.session() as session:
                keywords = await session.scalars(select(Keyword).filter_by(chat_id=message.chat.id))
            for keyword in keywords:
                if re.search(fr'\b{keyword.keyword}\b', message.text.lower()):
                    self.scheduler.add_job(answer_in, trigger='date',
                                           run_date=datetime.now() + timedelta(seconds=keyword.answer_in_seconds),
                                           kwargs=dict(client=self.client, answer=keyword.answer,
                                                       chat_id=message.chat.id, mess_id=message.id))
                    if keyword.chat.one_time_answer:
                        async with Base.session() as session:
                            await session.execute(update(Chat).filter_by(id=message.chat.id).values(is_active=False))
                            await session.commit()
                    break
            logging.info('callback processed')

    async def start_loop(self):
        while True:
            if await redis.get(RedisKeys.send_key):
                logging.info('receive send code signal')
                if not self.client.is_connected:
                    await self.client.connect()
                phone = await redis.get(RedisKeys.phone)
                try:
                    code_hash = await self.client.send_code(phone.decode())
                    await redis.set(RedisKeys.code_hash, code_hash.phone_code_hash)
                except PhoneNumberInvalid:
                    pass
                await redis.delete(RedisKeys.send_key)
            elif code := (await redis.get(RedisKeys.sended_code)):
                logging.info('receive sign in signal')
                code = code.decode()
                code_hash = await redis.get(RedisKeys.code_hash)
                code_hash = code_hash.decode()
                await self.client.sign_in(settings.phone, code_hash, code)

                await self.on_message_handler()
                await redis.delete(RedisKeys.sended_code)
                await self.initialize_pyrogram()
            elif await redis.get(RedisKeys.logout):
                logging.info('receive logout signal')
                try:
                    await self.client.stop()
                except Exception:
                    ...
                if os.path.exists('main.session'):
                    os.remove('main.session')
                await redis.delete(RedisKeys.authed)
                await redis.delete(RedisKeys.logout)

            await asyncio.sleep(2)
