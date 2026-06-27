import json
from itsdangerous import TimestampSigner, BadSignature, SignatureExpired
from fastapi import Request, Response
from fastapi.responses import RedirectResponse

import config

_signer = TimestampSigner(config.SESSION_SECRET_KEY)

SESSION_MAX_AGE = 60 * 60 * 24 * 7  # 7 days


class RedirectException(Exception):
    """Raised by require_session/require_role to short-circuit a route."""
    def __init__(self, response: RedirectResponse):
        self.response = response


def set_session(response: Response, user_data: dict) -> None:
    payload = json.dumps(user_data)
    signed = _signer.sign(payload.encode()).decode()
    response.set_cookie(
        key=config.SESSION_COOKIE_NAME,
        value=signed,
        httponly=True,
        samesite="lax",
        max_age=SESSION_MAX_AGE,
    )


def clear_session(response: Response) -> None:
    response.delete_cookie(config.SESSION_COOKIE_NAME)


def get_session(request: Request) -> dict | None:
    raw = request.cookies.get(config.SESSION_COOKIE_NAME)
    if not raw:
        return None
    try:
        unsigned = _signer.unsign(raw, max_age=SESSION_MAX_AGE)
        return json.loads(unsigned.decode())
    except (BadSignature, SignatureExpired, ValueError):
        return None


def require_session(request: Request) -> dict:
    user = get_session(request)
    if user is None:
        raise RedirectException(RedirectResponse(url="/login", status_code=303))
    return user


def require_role(request: Request, allowed_roles: list[str]) -> dict:
    user = require_session(request)
    if user.get("role") not in allowed_roles:
        raise RedirectException(RedirectResponse(url="/", status_code=303))
    return user


def dashboard_path_for_role(role: str) -> str:
    return {
        "patient": "/patient/dashboard",
        "doctor": "/doctor/dashboard",
        "nurse": "/nurse/dashboard",
        "receptionist": "/nurse/dashboard",
        "admin": "/admin/dashboard",
    }.get(role, "/")


# ---------------------------------------------------------------- flash --
def set_flash(response: Response, message: str, category: str = "success") -> None:
    payload = json.dumps({"message": message, "category": category})
    signed = _signer.sign(payload.encode()).decode()
    response.set_cookie(key=config.FLASH_COOKIE_NAME, value=signed, httponly=True, samesite="lax", max_age=300)


def peek_flash(request: Request) -> dict | None:
    """Read the flash cookie without clearing it (call before building the response)."""
    raw = request.cookies.get(config.FLASH_COOKIE_NAME)
    if not raw:
        return None
    try:
        unsigned = _signer.unsign(raw, max_age=300)
        return json.loads(unsigned.decode())
    except (BadSignature, SignatureExpired, ValueError):
        return None


def get_flash(request: Request, response: Response) -> dict | None:
    """Read the flash cookie and clear it on the given response."""
    flash = peek_flash(request)
    if flash is not None:
        response.delete_cookie(config.FLASH_COOKIE_NAME)
    return flash
