from fastapi.templating import Jinja2Templates

ticket_templates = Jinja2Templates(directory="web/templates/tickets")
settings_templates = Jinja2Templates(directory="web/templates/settings")