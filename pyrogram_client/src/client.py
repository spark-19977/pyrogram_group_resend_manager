import asyncio
import logging
import os
import re
from datetime import datetime, timedelta

from pyrogram import Client, raw, filters
from apscheduler.schedulers.asyncio import AsyncIOScheduler as Scheduler
from pyrogram.errors import PhoneNumberInvalid
from pyrogram.types import Message
from sqlalchemy import select, update

from settings import settings
from src.redis import redis, RedisKeys

from src.db.models import MinusKeyword, Manager
from .db.models import Base, Keyword


class StopError(Exception): pass


def parse_keywords(keyword: str):
    trans_table = {'.': '\\.', '^': '\\^', '$': '\\$', '*': '\\*', '+': '\\+', '?': '\\?',
                   '{': '\\{', '}': '\\}', '[': '\\[',
                   ']': '\\]', '\\': '\\\\', '|': '\\|', '(': '\\(', ')': '\\)'}
    keyword = keyword.translate(keyword.maketrans(trans_table))
    try:
        keyword = keyword.lower()
    except Exception as err:
        logging.exception(err)
        pass
    keywords = keyword.split(',')
    for keyword in keywords:
        if keyword:
            if keyword[0].isalnum():
                keyword = r'\b' + keyword
            if keyword[-1].isalnum():
                keyword += r'\b'
        yield keyword


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
        @self.client.on_message(filters.incoming)
        async def read_message(client: Client, message: Message):
            logging.info('callback receive')
            async with Base.session() as session:
                keywords = await session.scalars(select(Keyword))

            text = message.text.lower()
            for keyword in keywords:
                try:
                    for _keyword in parse_keywords(keyword.keyword):
                        if re.search(_keyword, text):
                            async with Base.session() as session:
                                minus_keywords = await session.scalars(
                                    select(MinusKeyword))
                            for minus_keyword in minus_keywords:
                                for _minus_keyword in parse_keywords(minus_keyword.minus_keyword):
                                    if re.search(_minus_keyword, text):
                                        raise StopError
                            async with Base.session() as session:
                                managers = await session.scalars(select(Manager))
                            for manager in managers:
                                try:
                                    await message.forward(manager.id)
                                    await asyncio.sleep(1)
                                except Exception as err:
                                    logging.exception(err)

                            raise StopError
                except StopError:
                    logging.info('callback stoped')
                    break

                except Exception as err:
                    logging.exception(err)
                    pass

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
                try:
                    logging.info('receive sign in signal')
                    code = code.decode()
                    code_hash = await redis.get(RedisKeys.code_hash)
                    code_hash = code_hash.decode()
                    phone = await redis.get(RedisKeys.phone)
                    await self.client.sign_in(phone.decode(), code_hash, code)

                    await self.on_message_handler()
                    await self.initialize_pyrogram()
                finally:
                    await redis.delete(RedisKeys.sended_code)
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
