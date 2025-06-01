import asyncio
import os
from typing import Optional
from database import Database
from database.models import Config
from sqlalchemy import select
import logging
from sqlalchemy.exc import SQLAlchemyError

# TOKEN: str = os.getenv("TOKEN")  # type: ignore
# MAIN_PROJECT_GID: str = os.getenv("MAIN_PROJECT_GID")  # type: ignore
# SUB_PROJECT_GID: str = os.getenv("SUB_PROJECT_GID")  # type: ignore

# _sync_token_key = 'sync_token'

_config_cache = {}
_config_lock = asyncio.Lock()


async def _get(key: str, session) -> Optional[Config]:
    query = select(Config).where(Config.key == key)
    result = await session.execute(query)
    config = result.scalars().one_or_none()
    return config


async def get(key: str) -> Optional[str]:
    async with _config_lock:
        if key in _config_cache:
            return _config_cache[key]
    
    async with Database.make_session() as session:
        res = await _get(key, session)
    if res is not None:
        async with _config_lock:
            _config_cache[res.key] = res.value
        return res.value
    return None


async def set(key: str, value: str) -> None:
    async with Database.make_session() as session:
        config = await _get(key, session)

        if config is None:
            config = Config(key=key, value=value)
        else:
            config.value = value
        
        try:
            session.add(config)
        except SQLAlchemyError as e:
            logging.error(f"Ошибка при сохранении config key='{key}': {e}")
            raise
        except Exception as e:
            logging.critical(f"Непредвиденная ошибка при сохранении config key='{key}': {e}")
            raise

        # logging.info(f"Успешно сохранен config key='{key}'")
        async with _config_lock:
            _config_cache[config.key] = config.value


# async def _get_sync_from_db(session) -> Config | None:
#     query = select(Config).where(Config.key == _sync_token_key)
#     result = await session.execute(query)
#     config = result.scalars().first()
#     return config


# async def save_sync_token(sync_token: str):
#     async with Database.make_session() as session:
#         config = await _get_sync_from_db(session)

#         if config is None:
#             config = Config(key=_sync_token_key, value=sync_token)

#         config.value = sync_token
#         session.add(config)
#         # logging.info(f"Сохранен sync {sync_token}")


# async def get_sync_token() -> str:
#     async with Database.make_session() as session:
#         config = await _get_sync_from_db(session)

#         if config is None:
#             logging.info(f"Sync не обнаружен")
#             return ""

#         # logging.info(f"Извлечен sync {config.value}")
#         return config.value
