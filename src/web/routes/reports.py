import logging
from fastapi import APIRouter, Request
from web.templates import reports_template
from database import Database
from database.models import AdditionalTicketInfo, Ticket
from sqlalchemy import func, not_, select, distinct, and_
from datetime import datetime, timedelta
from utils import create_date_period, TimePeroid


reports_router = APIRouter(prefix='/reports')


@reports_router.get("/manager")
async def manager_report(request: Request, manager: str = "", date_start: str = "", date_end: str = ""):
    async with Database.make_session() as session:
        query = select(distinct(AdditionalTicketInfo.worker_fullname))
        res = await session.execute(query)
        managers = res.scalars().all()

    date_period = extract_date_peroid(date_start, date_end)

    report = None
    if manager != "":
        report = []

        async with Database.make_session() as session:
            query = select(AdditionalTicketInfo).join(AdditionalTicketInfo.ticket).where(
                and_(
                    Ticket.created_at >= date_period.start,
                    Ticket.created_at < date_period.end + timedelta(days=1),
                    AdditionalTicketInfo.worker_fullname == manager,
                    not_(Ticket.deleted)
                )
            )
            res = await session.execute(query)
            report = res.scalars().all()

    return reports_template("manager_report.html",
                            {"request": request,
                             "managers": managers,
                             "selected_manager": manager,
                             "date_start": date_period.start.strftime("%Y-%m-%d"),
                             "date_end": date_period.end.strftime("%Y-%m-%d"),
                             "report": report})


def extract_date_peroid(date_start: str, date_end: str) -> TimePeroid:
    period = create_date_period()

    if date_start != "":
        datetime_start = datetime.strptime(date_start, "%Y-%m-%d")
        period.start = datetime_start

    if date_end != "":
        datetime_end = datetime.strptime(date_end, "%Y-%m-%d")
        period.end = datetime_end

    return period


@reports_router.get("/all-managers")
async def all_managers_report(request: Request, date_start: str = "", date_end: str = ""):
    period = extract_date_peroid(date_start, date_end)
    async with Database.make_session() as session:
        query = select(AdditionalTicketInfo.worker_fullname, func.count()).join(AdditionalTicketInfo.ticket).where(and_(
            Ticket.created_at >= period.start,
            Ticket.created_at < period.end + timedelta(days=1),
            not_(Ticket.deleted)
        )).group_by(
            AdditionalTicketInfo.worker_fullname)
        res = await session.execute(query)
        info = res.all()


    return reports_template("all_managers_report.html",
                            {"request": request,
                             "info": info,
                             "date_start": period.start.strftime("%Y-%m-%d"),
                             "date_end": period.end.strftime("%Y-%m-%d")})
