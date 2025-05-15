import os
from database import Database
from database.models import Config
from sqlalchemy import select
import logging

# TODO: переделать для получения из БД
TOKEN: str = os.getenv("TOKEN")  # type: ignore
MAIN_PROJECT_GID: str = os.getenv("MAIN_PROJECT_GID")  # type: ignore
SUB_PROJECT_GID: str = os.getenv("SUB_PROJECT_GID") # type: ignore

_sync_token_key = 'sync_token'


async def _get_sync_from_db(session) -> Config | None:
    query = select(Config).where(Config.key == _sync_token_key)
    result = await session.execute(query)
    config = result.scalars().first()
    return config


async def save_sync_token(sync_token: str):
    async with Database.make_session() as session:
        config = await _get_sync_from_db(session)

        if config is None:
            config = Config(key=_sync_token_key, value=sync_token)

        config.value = sync_token
        session.add(config)
        # logging.info(f"Сохранен sync {sync_token}")


async def get_sync_token() -> str:
    async with Database.make_session() as session:
        config = await _get_sync_from_db(session)

        if config is None:
            logging.info(f"Sync не обнаружен")
            return ""
        
        # logging.info(f"Извлечен sync {config.value}")
        return config.value