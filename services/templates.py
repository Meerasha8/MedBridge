from fastapi import Request
from fastapi.templating import Jinja2Templates

from services.auth_service import peek_flash

templates = Jinja2Templates(directory="templates")


def render(request: Request, name: str, context: dict, status_code: int = 200):
    """TemplateResponse wrapper that auto-injects + clears the flash cookie."""
    flash = peek_flash(request)
    context = {**context, "request": request, "flash": flash}
    response = templates.TemplateResponse(request, name, context, status_code=status_code)
    if flash:
        response.delete_cookie("medbridge_flash")
    return response
