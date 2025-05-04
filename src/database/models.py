from typing import Any, Dict, Optional
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped


class Base(DeclarativeBase):
    pass

class Ticket(Base):
    __tablename__ = 'tickets'

    id: Mapped[int] = mapped_column(primary_key=True)
    gid: Mapped[Optional[str]]
    worker_fullname: Mapped[str]
    k7_id: Mapped[str]
    office: Mapped[str]
    manager: Mapped[Optional[str]]
    client: Mapped[str]
    tasks: Mapped[str]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        mapping = {'ФИО Внедренца': 'worker_fullname',
                   'Номер наряда из К7': 'k7_id',
                   'Офис': 'office',
                   'Менеджер по наряду': 'manager',
                   'Клиент:': 'client',
                   'Задачи:': 'tasks'}
        kwargs = {mapping.get(k, k): v for k, v in data.items()}
        return cls(**kwargs)
