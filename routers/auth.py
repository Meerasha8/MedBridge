from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from supabase import create_client

import config
from services.templates import render
from services.supabase_client import get_supabase_admin
from services.auth_service import set_session, clear_session, get_session, set_flash, dashboard_path_for_role

router = APIRouter()


@router.get("/login")
async def login_page(request: Request):
    user = get_session(request)
    if user:
        return RedirectResponse(url=dashboard_path_for_role(user["role"]), status_code=303)
    return render(request, "login.html", {"error": None})


@router.post("/login")
async def login_submit(request: Request, email: str = Form(...), password: str = Form(...)):
    admin = get_supabase_admin()

    # IMPORTANT: use a fresh client per request for sign_in_with_password.
    # supabase-py stores the auth session *inside the client object*, so reusing
    # one shared/global client across concurrent requests means different users'
    # logins can overwrite each other's session state. A short-lived client
    # avoids that entirely (we only need it to verify the password here).
    auth_client = create_client(config.SUPABASE_URL, config.SUPABASE_ANON_KEY)

    try:
        auth_resp = auth_client.auth.sign_in_with_password({"email": email, "password": password})
    except Exception as e:
        msg = str(e)
        if "Email not confirmed" in msg:
            error = "Please confirm your email address before logging in. Check your inbox for the confirmation link."
        elif "Invalid login credentials" in msg:
            error = "Invalid email or password."
        else:
            error = f"Login failed: {msg}"
        return render(request, "login.html", {"error": error}, status_code=401)

    if not auth_resp.user:
        return render(request, "login.html", {"error": "Invalid email or password."}, status_code=401)

    user_id = auth_resp.user.id
    try:
        profile = admin.table("profiles").select("*").eq("id", user_id).single().execute().data
    except Exception:
        profile = None

    if not profile:
        return render(
            request, "login.html",
            {"error": "Your account exists but has no profile record. Contact support."},
            status_code=401,
        )

    response = RedirectResponse(url=dashboard_path_for_role(profile["role"]), status_code=303)
    set_session(response, {
        "user_id": profile["id"], "role": profile["role"],
        "full_name": profile["full_name"], "email": profile["email"],
    })
    return response


@router.get("/register")
async def register_page(request: Request):
    return render(request, "register.html", {"error": None})


@router.post("/register")
async def register_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(...),
    phone: str = Form(""),
    role: str = Form(...),
    language_preference: str = Form("en"),
    registration_number: str = Form(""),
    specialization: str = Form(""),
    clinic_name: str = Form(""),
    clinic_address: str = Form(""),
    lat: str = Form(""),
    lng: str = Form(""),
    languages_spoken: list[str] = Form([]),
    experience_years: str = Form(""),
    consultation_fee: str = Form(""),
    date_of_birth: str = Form(""),
    blood_group: str = Form(""),
    emergency_contact_name: str = Form(""),
    emergency_contact_phone: str = Form(""),
    allergies: str = Form(""),
):
    auth_client = create_client(config.SUPABASE_URL, config.SUPABASE_ANON_KEY)
    admin = get_supabase_admin()

    try:
        auth_resp = auth_client.auth.sign_up({"email": email, "password": password})
        user = auth_resp.user
        if user is None:
            raise ValueError("Could not create account. The email may already be registered.")
        user_id = user.id

        admin.table("profiles").insert({
            "id": user_id, "email": email, "full_name": full_name, "phone": phone,
            "language_preference": language_preference, "role": role,
        }).execute()

        if role == "doctor":
            admin.table("doctors").insert({
                "profile_id": user_id,
                "registration_number": registration_number,
                "specialization": specialization,
                "clinic_name": clinic_name,
                "clinic_address": clinic_address,
                "lat": float(lat) if lat else None,
                "lng": float(lng) if lng else None,
                "languages_spoken": languages_spoken,
                "experience_years": int(experience_years) if experience_years else None,
                "consultation_fee": float(consultation_fee) if consultation_fee else None,
                "is_verified": False,
            }).execute()
        elif role == "patient":
            admin.table("patients").insert({
                "profile_id": user_id,
                "date_of_birth": date_of_birth or None,
                "blood_group": blood_group or None,
                "emergency_contact_name": emergency_contact_name,
                "emergency_contact_phone": emergency_contact_phone,
                "allergies": [a.strip() for a in allergies.split(",") if a.strip()] if allergies else [],
            }).execute()

    except Exception as e:
        return render(request, "register.html", {"error": str(e)}, status_code=400)

    response = RedirectResponse(url="/login", status_code=303)
    set_flash(response, "Account created successfully. Please log in.", "success")
    return response


@router.post("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=303)
    clear_session(response)
    return response
