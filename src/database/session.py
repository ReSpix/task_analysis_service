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


class AsyncDatabase:
    db_url = f'sqlite+aiosqlite:///./database/db.sqlite'

    def __init__(self, echo=False):
        self.engine = create_async_engine(
            __class__.db_url,
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
