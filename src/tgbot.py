import aiohttp
from sqlalchemy import select
from config_manager import get
from database import Database
from database.models import TelegramConfig
import logging
import asyncio
from typing import ClassVar
from collections import deque


class TgBot:
    _message_queue: ClassVar[deque] = deque()
    _queue_worker_started: ClassVar[bool] = False

    @classmethod
    async def get_url(cls, token=None) -> str:
        if token is None:
            token = await get("telegram_token")
        return f'https://api.telegram.org/bot{token}/'

    @classmethod
    async def check_token(cls, token):
        async with aiohttp.ClientSession() as session:
            url = await cls.get_url(token)
            async with session.get(url + "getMe") as response:
                data = await response.json()
        return data['ok']

    @classmethod
    async def get_chats(cls, text: str = "") -> list[str]:
        async with Database.make_session() as session:
            query = select(TelegramConfig).where(
                TelegramConfig.destination_type == "chat")
            res = await session.execute(query)
            chats = [c.destination_id for c in res.scalars().all()]
        return chats

    @classmethod
    async def send_message_to_chat(cls, chat_id: str, text: str):
        async with aiohttp.ClientSession() as session:
            url = await cls.get_url()
            body = {"chat_id": chat_id, "text": text}
            async with session.get(url + "sendMessage", data=body) as response:
                data = await response.json()
                return data

    @classmethod
    async def send_message(cls, text: str):
        """Добавить сообщение в очередь."""
        cls._message_queue.append(text)
        if not cls._queue_worker_started:
            asyncio.create_task(cls._start_queue_worker())
            cls._queue_worker_started = True

    @classmethod
    async def _start_queue_worker(cls):
        """Фоновая задача обработки очереди."""
        while True:
            try:
                token = await get("telegram_token")
                if token is not None and cls._message_queue:
                    text = cls._message_queue.popleft()
                    chats = await cls.get_chats()
                    for chat_id in chats:
                        await cls.send_message_to_chat(chat_id, text)
                await asyncio.sleep(1)
            except Exception as e:
                logging.critical(e)
