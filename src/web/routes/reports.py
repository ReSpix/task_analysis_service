from fastapi import APIRouter, Request
from web.templates import reports_template
from database import Database
from database.models import AdditionalTicketInfo
from sqlalchemy import select, distinct, and_
from datetime import datetime, timedelta


reports_router = APIRouter(prefix='/reports')


@reports_router.get("/manager")
async def manager_report(request: Request, manager: str = "", date_start: str = "", date_end: str = ""):
    async with Database.make_session() as session:
        query = select(distinct(AdditionalTicketInfo.worker_fullname))
        res = await session.execute(query)
        managers = res.scalars().all()

    report = []
    if manager != "" and date_start != "" and date_end != "":
        datetime_start = datetime.strptime(date_start, "%Y-%m-%d")
        datetime_end = datetime.strptime(date_end, "%Y-%m-%d")

        async with Database.make_session() as session:
            query = select(AdditionalTicketInfo).where(
                and_(
                    AdditionalTicketInfo.created_at >= datetime_start,
                    AdditionalTicketInfo.created_at < datetime_end  + timedelta(days=1),
                    AdditionalTicketInfo.worker_fullname == manager
                )
            )
            res = await session.execute(query)
            report = res.scalars().all()

    return reports_template("index.html", 
                            {"request": request, 
                             "managers": managers, 
                             "selected_manager": manager, 
                             "date_start": date_start, 
                             "date_end": date_end, 
                             "report": report})
