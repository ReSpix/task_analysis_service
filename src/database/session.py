import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.pool import NullPool
from .models import Base
import logging
import os


class AsyncDatabase:
    db_url_local = f'sqlite+aiosqlite:///./database/db.sqlite'

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    RELATIVE_DB_PATH = os.path.join(BASE_DIR, '..', '..', 'data', 'db.sqlite')
    ABSOLUTE_DB_PATH = os.path.abspath(RELATIVE_DB_PATH)

    db_url_external = f"sqlite+aiosqlite:///{ABSOLUTE_DB_PATH}"

    def __init__(self, echo=False):
        os.makedirs(os.path.dirname(__class__.ABSOLUTE_DB_PATH), exist_ok=True)

        self.engine = create_async_engine(
            __class__.db_url_external,
            echo=echo,
            poolclass=NullPool,
        )
        self.async_session = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    async def create_all(self):
        """Создание всех таблиц в базе данных"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logging.info("Модели БД синхронизированы")

    @asynccontextmanager
    async def make_session(self) -> AsyncGenerator[AsyncSession, None]:
        async with self.async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                raise e
            finally:
                await session.close()
