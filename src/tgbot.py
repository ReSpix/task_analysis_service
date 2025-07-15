import aiohttp
from sqlalchemy import select
from config_manager import get
from database import Database
from database.models import TelegramConfig
import logging
import asyncio
from typing import ClassVar, Sequence
from collections import deque
import certifi
import ssl
from aiohttp.client_exceptions import ClientConnectionError, ClientConnectorCertificateError


class TgBot:
    _message_queue: ClassVar[deque] = deque()
    _queue_worker_started: ClassVar[bool] = False

    @classmethod
    async def get_url(cls, token=None) -> str:
        if token is None:
            token = await get("telegram_token")
        return f'https://api.telegram.org/bot{token}/'
    
    @classmethod
    async def bot_available(cls) -> bool:
        token = await get("telegram_token")
        return token is not None

    @classmethod
    async def check_token(cls, token):
        try:
            async with aiohttp.ClientSession() as session:
                url = await cls.get_url(token)
                ssl_context = ssl.create_default_context(
                    cafile=certifi.where())
                async with session.get(url + "getMe", ssl=ssl_context) as response:
                    data = await response.json()
        except (ClientConnectionError, ClientConnectorCertificateError) as e:
            logging.critical(f"Не удалось связаться с Telegram. Ошибка: {e}")
            return (False, "Не удалось связаться с Telegram")

        if data['ok']:
            return (True, "Успешно")
        else:
            return (False, "Неверный токен")
        
    @classmethod
    async def get_chat_title(cls, chat_id: str):
        if not (await cls.bot_available()):
            return (False, "Сначала введите токен бота")
        if chat_id[0] != "-":
            return (False, "Введите верный ID чата, включая \"-\"")
        try:
            async with aiohttp.ClientSession() as session:
                url = await cls.get_url()
                ssl_context = ssl.create_default_context(
                    cafile=certifi.where())
                async with session.get(url + f"getChat?chat_id={chat_id}", ssl=ssl_context) as response:
                    data = await response.json()
        except (ClientConnectionError, ClientConnectorCertificateError) as e:
            logging.critical(f"Не удалось связаться с Telegram. Ошибка: {e}")
            return (False, "Не удалось связаться с Telegram для получения названия чата")

        if data['ok']:
            return (True, data["result"]["title"])
        else:
            return (False, "Неверный ID чата. Проверьте ID и убедитесь что бот добавлен в чат")
    

    @classmethod
    async def get_chats(cls, text: str = "") -> list[str]:
        if not (await cls.bot_available()):
            return []
        async with Database.make_session() as session:
            query = select(TelegramConfig).where(
                TelegramConfig.destination_type == "chat")
            res = await session.execute(query)
            chats = [c.destination_id for c in res.scalars().all()]
        return chats

    @classmethod
    async def send_message_to_chat(cls, chat_id: str, text: str):
        if not (await cls.bot_available()):
            return None
        async with aiohttp.ClientSession() as session:
            url = await cls.get_url()
            body = {"chat_id": chat_id, "text": text}
            try:
                ssl_context = ssl.create_default_context(
                    cafile=certifi.where())
                async with session.get(url + "sendMessage", data=body, ssl=ssl_context) as response:
                    data = await response.json()
                    return data
            except (ClientConnectionError, ClientConnectorCertificateError) as e:
                logging.critical(
                    f"Не удалось связаться с Telegram для отправки сообщения. Ошибка: {e}")
                return None

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

    @classmethod
    async def get_chats_titles(cls, chat_ids: list[str]) -> Sequence[tuple[bool, str]]:
        """
        Получить названия чатов для списка chat_id параллельно.
        Возвращает список кортежей (True/False, title/ошибка) в том же порядке, что и chat_ids.
        """
        tasks = [cls.get_chat_title(chat_id) for chat_id in chat_ids]
        results = await asyncio.gather(*tasks)
        return results
