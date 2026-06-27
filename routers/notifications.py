from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from services.templates import render
from services.auth_service import require_session
from services.supabase_client import get_supabase_admin

router = APIRouter()


@router.get("/notifications")
async def list_notifications(request: Request):
    user = require_session(request)
    admin = get_supabase_admin()
    notifications = (
        admin.table("notifications").select("*").eq("user_id", user["user_id"])
        .order("created_at", desc=True).limit(50).execute()
    ).data or []
    return render(request, "notifications.html", {"notifications": notifications, "user": user})


@router.post("/notifications/{notification_id}/read")
async def mark_read(request: Request, notification_id: str):
    user = require_session(request)
    admin = get_supabase_admin()
    admin.table("notifications").update({"is_read": True}).eq("id", notification_id).eq(
        "user_id", user["user_id"]
    ).execute()
    return RedirectResponse(url="/notifications", status_code=303)
