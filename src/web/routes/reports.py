from fastapi import APIRouter, Request
from web.templates import reports_template


reports_router = APIRouter(prefix='/reports')


@reports_router.get("/manager")
async def manager_report(request: Request):
    return reports_template("index.html", {"request": request, "managers": ['1', '2', '3']})
