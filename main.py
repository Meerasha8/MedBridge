from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import PlainTextResponse

from services import mcp_client
from services.auth_service import RedirectException, get_session
from services.templates import render
from routers import auth, chat, doctors, appointments, documents, prescriptions, sub_accounts, notifications, admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        app.state.mcp_tools = await mcp_client.fetch_tool_schemas()
    except Exception:
        app.state.mcp_tools = []
    yield


app = FastAPI(title="MedBridge", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(doctors.router)
app.include_router(appointments.router)
app.include_router(documents.router)
app.include_router(prescriptions.router)
app.include_router(sub_accounts.router)
app.include_router(notifications.router)
app.include_router(admin.router)


@app.get("/")
async def landing(request: Request):
    mcp_client.fire_and_forget_ping()
    elapsed = await mcp_client.ping_mcp()
    mcp_slow = elapsed > 5.0
    return render(request, "landing.html", {"mcp_slow": mcp_slow, "user": get_session(request)})


@app.exception_handler(RedirectException)
async def redirect_exception_handler(request, exc: RedirectException):
    return exc.response


@app.get("/health", response_class=PlainTextResponse)
async def health():
    return "ok"
