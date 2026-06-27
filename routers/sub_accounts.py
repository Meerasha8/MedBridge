from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse

from services.templates import render
from services.auth_service import require_role, set_flash
from services.supabase_client import get_supabase_admin

router = APIRouter()


@router.get("/doctor/sub-accounts")
async def list_sub_accounts(request: Request):
    user = require_role(request, ["doctor"])
    admin = get_supabase_admin()
    doctor = admin.table("doctors").select("id").eq("profile_id", user["user_id"]).single().execute().data

    sub_accounts = (
        admin.table("sub_accounts").select("*, profiles(full_name, email, phone)")
        .eq("doctor_id", doctor["id"]).order("created_at", desc=True).execute()
    ).data or []

    return render(request, "doctor/sub_accounts.html", {"sub_accounts": sub_accounts, "user": user})


@router.post("/doctor/sub-accounts")
async def create_sub_account(
    request: Request,
    email: str = Form(...), full_name: str = Form(...), phone: str = Form(""), role: str = Form(...),
):
    user = require_role(request, ["doctor"])
    admin = get_supabase_admin()
    doctor = admin.table("doctors").select("id").eq("profile_id", user["user_id"]).single().execute().data

    try:
        created = admin.auth.admin.create_user({
            "email": email,
            "email_confirm": True,
            "user_metadata": {"full_name": full_name},
        })
        new_user_id = created.user.id

        admin.table("profiles").insert({
            "id": new_user_id, "email": email, "full_name": full_name, "phone": phone, "role": role,
        }).execute()

        admin.table("sub_accounts").insert({
            "doctor_id": doctor["id"], "profile_id": new_user_id, "role": role, "is_active": True,
        }).execute()

        response = RedirectResponse(url="/doctor/sub-accounts", status_code=303)
        set_flash(response, f"{role.title()} account created for {full_name}.", "success")
    except Exception as e:
        response = RedirectResponse(url="/doctor/sub-accounts", status_code=303)
        set_flash(response, f"Could not create account: {e}", "error")
    return response


@router.post("/doctor/sub-accounts/{sub_account_id}/deactivate")
async def deactivate_sub_account(request: Request, sub_account_id: str):
    require_role(request, ["doctor"])
    admin = get_supabase_admin()
    admin.table("sub_accounts").update({"is_active": False}).eq("id", sub_account_id).execute()

    response = RedirectResponse(url="/doctor/sub-accounts", status_code=303)
    set_flash(response, "Account deactivated.", "success")
    return response
