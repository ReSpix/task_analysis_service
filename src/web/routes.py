from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from database import Database
from sqlalchemy import select
from database.models import Ticket, Status


web_router = APIRouter()
templates = Jinja2Templates(directory="web/templates")


@web_router.get("/tickets")
async def tickets(request: Request):
    async with Database.make_session() as session:
        query = select(Ticket)

        result = await session.execute(query)
        tickets = result.scalars().all()

        return templates.TemplateResponse('tickets.html', {"request": request, "tickets": tickets})


@web_router.get("/statuses")
async def statuses(request: Request):
    async with Database.make_session() as session:
        query = select(Status)

        result = await session.execute(query)
        tickets = result.scalars().all()

        return tickets
