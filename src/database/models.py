from __future__ import annotations
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped, relationship
from sqlalchemy import ForeignKey
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import select, desc
import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession


class Base(DeclarativeBase):
    pass


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True)
    gid: Mapped[Optional[str]] = mapped_column(unique=True)
    title: Mapped[str]
    text: Mapped[str]
    completed: Mapped[bool] = mapped_column(default=False)
    deleted: Mapped[bool] = mapped_column(default=False)
    sub_contract: Mapped[bool] = mapped_column(default=False)
    additional_info: Mapped[Optional["AdditionalTicketInfo"]] = relationship(
        back_populates="ticket", uselist=False, lazy='selectin')
    statuses: Mapped[List["Status"]] = relationship(
        back_populates="ticket", lazy='selectin')
    
    @hybrid_property
    def last_status(self) -> Optional["Status"]:
        """Возвращает последний статус тикета (с наибольшим datetime)"""
        if not self.statuses:  # Если статусов нет
            return None
        return max(self.statuses, key=lambda s: s.datetime)
    
    @last_status.expression
    def last_status_exp(cls):
        """SQL-выражение для запросов, возвращающее последний статус"""
        return (
            select(Status)
            .where(Status.ticket_id == cls.id)
            .order_by(desc(Status.datetime))
            .limit(1)
            .correlate(cls)
            .scalar_subquery()
        )

    def __init__(self, title, text, gid=None, **kwargs):
        self.text = text
        self.title = title
        if gid is not None:
            self.gid = gid

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Ticket:
        mapping = {'Задачи:': 'text'}
        kwargs = {mapping.get(k, k): v for k, v in data.items()}
        return cls(**kwargs)

    @classmethod
    def full_ticket_from_dict(cls, data: Dict[str, Any]) -> Ticket:
        info = AdditionalTicketInfo.from_dict(data)
        data['title'] = f"Челлендж {info.k7_id}"
        logging.info(data)
        ticket = cls.from_dict(data)
        logging.info(ticket.title)
        ticket.additional_info = info
        return ticket
    
    @classmethod
    async def get_by_gid(cls, session: AsyncSession, gid: str) -> Optional[Ticket]:
        query = select(Ticket).where(Ticket.gid == gid)
        result = await session.execute(query)
        ticket = result.scalars().first()
        return ticket


class AdditionalTicketInfo(Base):
    __tablename__ = 'additional_ticket_info'

    id: Mapped[int] = mapped_column(primary_key=True)
    worker_fullname: Mapped[str]
    k7_id: Mapped[str]
    office: Mapped[str]
    manager: Mapped[Optional[str]]
    client: Mapped[str]

    ticket_id: Mapped["Ticket"] = mapped_column(
        ForeignKey("tickets.id"), unique=True, nullable=False)
    ticket: Mapped["Ticket"] = relationship(back_populates="additional_info")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        mapping = {'ФИО Внедренца': 'worker_fullname',
                   'Номер наряда из К7': 'k7_id',
                   'Офис': 'office',
                   'Менеджер по наряду': 'manager',
                   'Клиент:': 'client'}
        data = {key: value for key,
                value in data.items() if key in mapping.keys()}
        kwargs = {mapping.get(k, k): v for k, v in data.items()}
        return cls(**kwargs)


class Status(Base):
    __tablename__ = "statuses"

    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str]
    datetime: Mapped[datetime] = mapped_column(default=datetime.now)    
    ticket_id: Mapped["Ticket"] = mapped_column(ForeignKey("tickets.id"))
    ticket: Mapped["Ticket"] = relationship(back_populates="statuses")


class Config(Base):
    __tablename__ = "config"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(unique=True)
    value: Mapped[str]