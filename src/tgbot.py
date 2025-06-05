import aiohttp
from sqlalchemy import select
from config_manager import get
from database import Database
from database.models import TelegramConfig
import logging


class TgBot:
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
    async def get_chats(cls, text: str) -> dict:
        async with Database.make_session() as session:
            query = select(TelegramConfig).where(
                TelegramConfig.destination_type == "chat")
            res = await session.execute(query)
            chats = res.scalars().all()

        return {"chat_id": "-4698292891", "text": text}

    @classmethod
    async def send_message(cls, text: str):

        async with aiohttp.ClientSession() as session:
            url = await cls.get_url()
            async with session.get(url + "sendMessage", data=cls.get_body(text)) as response:
                data = await response.json()
                return data
