from __future__ import annotations
from typing import Any, Dict, Optional
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped, relationship
from sqlalchemy import ForeignKey
import logging


class Base(DeclarativeBase):
    pass


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True)
    gid: Mapped[Optional[str]]
    text: Mapped[str]
    additional_info: Mapped[Optional["AdditionalTicketInfo"]] = relationship(back_populates="ticket", uselist=False, lazy='selectin')

    def __init__(self, text, **kwargs):
        self.text = text

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Ticket:
        mapping = {'Задачи:': 'text'}
        kwargs = {mapping.get(k, k): v for k, v in data.items()}
        return cls(**kwargs)
    
    @classmethod
    def full_ticket_from_dict(cls, data: Dict[str, Any]) -> Ticket:
        ticket = cls.from_dict(data)
        info = AdditionalTicketInfo.from_dict(data)
        ticket.additional_info = info
        return ticket


class AdditionalTicketInfo(Base):
    __tablename__ = 'additional_ticket_info'

    id: Mapped[int] = mapped_column(primary_key=True)
    worker_fullname: Mapped[str]
    k7_id: Mapped[str]
    office: Mapped[str]
    manager: Mapped[Optional[str]]
    client: Mapped[str]

    ticket_id: Mapped["Ticket"] = mapped_column(ForeignKey("tickets.id"), unique=True, nullable=False)
    ticket: Mapped["Ticket"] = relationship(back_populates="additional_info")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        mapping = {'ФИО Внедренца': 'worker_fullname',
                   'Номер наряда из К7': 'k7_id',
                   'Офис': 'office',
                   'Менеджер по наряду': 'manager',
                   'Клиент:': 'client'}
        data = {key: value for key, value in data.items() if key in mapping.keys()}
        kwargs = {mapping.get(k, k): v for k, v in data.items()}
        return cls(**kwargs)
