from datetime import datetime
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from starlette.status import HTTP_303_SEE_OTHER
from database import Database
from sqlalchemy import and_, desc, distinct, select
from database.models import Ticket, Status
from ..templates import tickets_template
from utils import format_timedelta_pretty
import logging


ticket_router = APIRouter(prefix='/tickets')


@ticket_router.get("/")
async def tickets(request: Request):
    async with Database.make_session() as session:
        query = select(Ticket).where((Ticket.deleted == False)
                                     & (Ticket.sub_contract == False))

        result = await session.execute(query)
        tickets = result.scalars().all()

        return tickets_template('index.html', {"request": request, "tickets": tickets, "all": False})


@ticket_router.get("/all")
async def tickets_all(request: Request):
    async with Database.make_session() as session:
        query = select(Ticket)

        result = await session.execute(query)
        tickets = result.scalars().all()

        return tickets_template('index.html', {"request": request, "tickets": tickets, "all": True})


@ticket_router.get("/challenge")
async def challenge(request: Request):
    async with Database.make_session() as session:
        query = select(
            Ticket
        ).where(
            and_(
                Ticket.additional_info != None,
                Ticket.deleted == False
            )
        ).order_by(
            desc(
                Ticket.created_at
            )
        )

        result = await session.execute(query)
        tickets = result.scalars().all()

        return tickets_template('challenge.html',
                                {"request": request,
                                 "tickets": tickets
                                 })


@ticket_router.get("/challenge/all")
async def challengea_all(request: Request, status: str = ""):
    async with Database.make_session() as session:
        query = select(
            Ticket
        ).where(
            Ticket.additional_info != None
        ).order_by(
            desc(
                Ticket.created_at
            )
        )

        result = await session.execute(query)
        tickets = result.scalars().all()
        tickets = list(tickets)

        statuses = []
        for ticket in tickets:
            if ticket.last_status == None:
                continue
            statuses.append(ticket.last_status.text)

        filtered_tickets = []
        if status != "":
            for ticket in tickets:
                if ticket.last_status is None:
                    logging.info("ПУСТО!!!")
                    continue
                if ticket.last_status.text == status:
                    filtered_tickets.append(ticket)
            tickets = filtered_tickets

        return tickets_template('challenge.html',
                                {"request": request,
                                 "tickets": tickets,
                                 "all": True,
                                 "statuses": set(statuses),
                                 "selected_status": status
                                 })


@ticket_router.get("/sub_contract")
async def sub_contract(request: Request):
    async with Database.make_session() as session:
        query = select(
            Ticket
        ).where(
            and_(
                Ticket.sub_contract == True,
                Ticket.deleted == False

            )
        ).order_by(
            desc(
                Ticket.created_at
            )
        )

        result = await session.execute(query)
        tickets = result.scalars().all()

        return tickets_template('sub_contract.html', {"request": request, "tickets": tickets})


@ticket_router.get("/full-info/{ticket_id}")
async def full_ticket_info(request: Request, ticket_id: int):
    async with Database.make_session() as session:
        query = select(Ticket).where(Ticket.id == ticket_id)

        result = await session.execute(query)
        ticket = result.scalars().one_or_none()
    if ticket is not None:
        ticket.statuses.sort(key=lambda x: x.datetime)
        for i in range(len(ticket.statuses) - 1):
            ticket.statuses[i].time_to_next = ticket.statuses[i +
                                                              1].datetime - ticket.statuses[i].datetime

        ticket.statuses[-1].time_to_next = datetime.now() - \
            ticket.statuses[-1].datetime
        ticket.statuses.sort(key=lambda x: x.datetime, reverse=True)

    return tickets_template('full_info.html', {"request": request, "ticket": ticket})


@ticket_router.post("/delete/{ticket_id}")
async def delete_ticket(request: Request, ticket_id: int):
    async with Database.make_session() as session:
        query = select(Ticket).where(Ticket.id == ticket_id)

        result = await session.execute(query)
        ticket = result.scalars().one_or_none()

        if ticket is not None:
            ticket.deleted_at = datetime.now()
            ticket.deleted = True
            session.add(ticket)
            status = Status(text='Удалено вручную', ticket=ticket)
            session.add(status)
            status = Status(text='Удалено', ticket=ticket)
            session.add(status)

    return RedirectResponse(ticket_router.prefix+f"/full-info/{ticket_id}", status_code=HTTP_303_SEE_OTHER)
