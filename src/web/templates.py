from fastapi.templating import Jinja2Templates
from utils import format_timedelta_pretty

templates = Jinja2Templates(directory="web/templates")

templates.env.filters['timedelta_human'] = format_timedelta_pretty


def settings_template(path: str, context: dict):
    return templates.TemplateResponse("settings/"+path, context)

def tickets_template(path: str, context: dict):
    return templates.TemplateResponse("tickets/"+path, context)

def reports_template(path: str, context: dict):
    return templates.TemplateResponse("reports/"+path, context)

# # Указываем список путей: сначала локальная папка, затем общий корень
# ticket_env = Environment(loader=FileSystemLoader(["web/templates/tickets", "web/templates"]))
# settings_env = Environment(loader=FileSystemLoader(["web/templates/settings", "web/templates"]))

# # Оборачиваем вручную в Jinja2Templates
# from starlette.templating import _TemplateResponse

# class CustomTemplates:
#     def __init__(self, env):
#         self.env = env

#     def TemplateResponse(self, name, context, status_code=200):
#         template = self.env.get_template(name)
#         return _TemplateResponse(template, context, status_code=status_code)

# # Теперь ты можешь:
# ticket_templates = CustomTemplates(ticket_env)
# settings_templates = CustomTemplates(settings_env)
