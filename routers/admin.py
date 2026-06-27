from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from services.templates import render
from services.auth_service import require_role, set_flash
from services.supabase_client import get_supabase_admin

router = APIRouter()


@router.get("/admin/dashboard")
async def admin_dashboard(request: Request):
    user = require_role(request, ["admin"])
    admin = get_supabase_admin()
    pending_doctors = (
        admin.table("doctors").select("*, profiles(full_name, email, phone)")
        .eq("is_verified", False).order("created_at", desc=True).execute()
    ).data or []
    return render(request, "admin/dashboard.html", {"pending_doctors": pending_doctors, "user": user})


@router.post("/admin/doctors/{doctor_id}/verify")
async def verify_doctor(request: Request, doctor_id: str):
    require_role(request, ["admin"])
    admin = get_supabase_admin()
    admin.table("doctors").update({"is_verified": True}).eq("id", doctor_id).execute()
    doctor = admin.table("doctors").select("profile_id").eq("id", doctor_id).single().execute().data
    admin.table("notifications").insert({
        "user_id": doctor["profile_id"], "type": "verification",
        "title": "Profile verified", "message": "Your profile has been verified!",
    }).execute()

    response = RedirectResponse(url="/admin/dashboard", status_code=303)
    set_flash(response, "Doctor verified.", "success")
    return response


@router.get("/admin/audit-logs")
async def audit_logs(request: Request):
    user = require_role(request, ["admin"])
    admin = get_supabase_admin()
    logs = (
        admin.table("audit_logs").select("*, profiles(full_name, email)")
        .order("created_at", desc=True).limit(100).execute()
    ).data or []
    return render(request, "admin/audit_logs.html", {"logs": logs, "user": user})
