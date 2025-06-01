from fastapi import APIRouter, Request
from database import Database
from sqlalchemy import select
from database.models import Ticket
from ..templates import tickets_template


ticket_router = APIRouter(prefix='/tickets')


@ticket_router.get("/")
async def tickets(request: Request):
    async with Database.make_session() as session:
        query = select(Ticket).where((Ticket.deleted == False) & (Ticket.sub_contract == False))

        result = await session.execute(query)
        tickets = result.scalars().all()

        return tickets_template('index.html', {"request": request, "tickets": tickets})
    
@ticket_router.get("/all")
async def tickets_all(request: Request):
    async with Database.make_session() as session:
        query = select(Ticket)

        result = await session.execute(query)
        tickets = result.scalars().all()

        return tickets_template('index.html', {"request": request, "tickets": tickets})


@ticket_router.get("/challenge")
async def challenge(request: Request):
    async with Database.make_session() as session:
        query = select(Ticket).where(Ticket.additional_info != None)

        result = await session.execute(query)
        tickets = result.scalars().all()

        return tickets_template('challenge.html', {"request": request, "tickets": tickets})
    


@ticket_router.get("/sub_contract")
async def sub_contract(request: Request):
    async with Database.make_session() as session:
        query = select(Ticket).where((Ticket.sub_contract == True) & (Ticket.deleted == False))

        result = await session.execute(query)
        tickets = result.scalars().all()

        return tickets_template('sub_contract.html', {"request": request, "tickets": tickets})
