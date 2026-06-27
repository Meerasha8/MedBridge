from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse

from services.templates import render
from services.auth_service import require_role, set_flash
from services.supabase_client import get_supabase_admin
from services import mcp_client

router = APIRouter()


def _patient_id(user) -> str:
    admin = get_supabase_admin()
    r = admin.table("patients").select("id").eq("profile_id", user["user_id"]).single().execute()
    return r.data["id"]


def _doctor_id(user) -> str:
    admin = get_supabase_admin()
    r = admin.table("doctors").select("id").eq("profile_id", user["user_id"]).single().execute()
    return r.data["id"]


# --------------------------------------------------------------- patient --
@router.get("/patient/dashboard")
async def patient_dashboard(request: Request):
    user = require_role(request, ["patient"])
    admin = get_supabase_admin()
    patient_id = _patient_id(user)

    appts = (
        admin.table("appointments")
        .select("*, doctors(id, specialization, clinic_name, profiles(full_name))")
        .eq("patient_id", patient_id)
        .neq("status", "cancelled")
        .gte("scheduled_at", "now()")
        .order("scheduled_at")
        .limit(3)
        .execute()
    )
    unread = (
        admin.table("notifications")
        .select("id", count="exact")
        .eq("user_id", user["user_id"])
        .eq("is_read", False)
        .execute()
    )
    prescriptions = (
        admin.table("prescriptions")
        .select("*, doctors(specialization, profiles(full_name))")
        .eq("patient_id", patient_id)
        .order("created_at", desc=True)
        .limit(2)
        .execute()
    )

    return render(request, "patient/dashboard.html", {
        "user": user,
        "appointments": appts.data or [],
        "notifications_count": unread.count or 0,
        "prescriptions": prescriptions.data or [],
    })


@router.get("/patient/appointments")
async def patient_appointments(request: Request, filter: str = "upcoming"):
    user = require_role(request, ["patient"])
    admin = get_supabase_admin()
    patient_id = _patient_id(user)

    query = (
        admin.table("appointments")
        .select("*, doctors(id, specialization, clinic_name, profiles(full_name))")
        .eq("patient_id", patient_id)
    )
    if filter == "upcoming":
        query = query.gte("scheduled_at", "now()").order("scheduled_at")
    elif filter == "past":
        query = query.lt("scheduled_at", "now()").order("scheduled_at", desc=True)
    else:
        query = query.order("scheduled_at", desc=True)

    result = query.execute()
    return render(request, "patient/appointments.html", {
        "appointments": result.data or [], "filter": filter, "user": user,
    })


@router.get("/patient/appointments/{appointment_id}")
async def patient_appointment_detail(request: Request, appointment_id: str):
    user = require_role(request, ["patient"])
    admin = get_supabase_admin()
    patient_id = _patient_id(user)

    appt_resp = (
        admin.table("appointments")
        .select("*, doctors(id, specialization, clinic_name, clinic_address, profiles(full_name))")
        .eq("id", appointment_id).eq("patient_id", patient_id).single().execute()
    )
    appointment = appt_resp.data
    if not appointment:
        return RedirectResponse(url="/patient/appointments", status_code=303)

    docs = admin.table("documents").select("*").eq("appointment_id", appointment_id).execute()
    prescription = (
        admin.table("prescriptions").select("*, medicines(*)")
        .eq("appointment_id", appointment_id).maybe_single().execute()
    )
    review = admin.table("reviews").select("*").eq("appointment_id", appointment_id).maybe_single().execute()

    return render(request, "patient/appointment_detail.html", {
        "appointment": appointment,
        "doctor": appointment.get("doctors"),
        "documents": docs.data or [],
        "prescription": prescription.data if prescription else None,
        "review": review.data if review else None,
        "user": user,
    })


@router.post("/patient/appointments/{appointment_id}/review")
async def submit_review(
    request: Request, appointment_id: str,
    rating: int = Form(...), feedback_text: str = Form(""), feedback_language: str = Form("en"),
):
    user = require_role(request, ["patient"])
    patient_id = _patient_id(user)

    await mcp_client.call_tool("submit_review", {
        "appointment_id": appointment_id,
        "patient_id": patient_id,
        "rating": rating,
        "feedback_text": feedback_text,
        "feedback_language": feedback_language,
    })

    response = RedirectResponse(url=f"/patient/appointments/{appointment_id}", status_code=303)
    set_flash(response, "Thanks for your feedback!", "success")
    return response


@router.get("/patient/profile")
async def patient_profile(request: Request):
    user = require_role(request, ["patient"])
    admin = get_supabase_admin()
    profile = admin.table("profiles").select("*").eq("id", user["user_id"]).single().execute().data
    patient = admin.table("patients").select("*").eq("profile_id", user["user_id"]).single().execute().data
    return render(request, "patient/profile.html", {"profile": profile, "patient": patient, "user": user})


@router.post("/patient/profile")
async def patient_profile_update(
    request: Request,
    full_name: str = Form(...), phone: str = Form(""), language_preference: str = Form("en"),
    blood_group: str = Form(""), emergency_contact_name: str = Form(""),
    emergency_contact_phone: str = Form(""), allergies: str = Form(""),
):
    user = require_role(request, ["patient"])
    admin = get_supabase_admin()
    admin.table("profiles").update({
        "full_name": full_name, "phone": phone, "language_preference": language_preference,
    }).eq("id", user["user_id"]).execute()
    admin.table("patients").update({
        "blood_group": blood_group or None,
        "emergency_contact_name": emergency_contact_name,
        "emergency_contact_phone": emergency_contact_phone,
        "allergies": [a.strip() for a in allergies.split(",") if a.strip()] if allergies else [],
    }).eq("profile_id", user["user_id"]).execute()

    response = RedirectResponse(url="/patient/profile", status_code=303)
    set_flash(response, "Profile updated.", "success")
    return response


# ---------------------------------------------------------------- doctor --
@router.get("/doctor/dashboard")
async def doctor_dashboard(request: Request):
    user = require_role(request, ["doctor"])
    admin = get_supabase_admin()
    doctor = admin.table("doctors").select("*").eq("profile_id", user["user_id"]).single().execute().data

    today_appts = (
        admin.table("appointments")
        .select("*, patients(id, profiles(full_name))")
        .eq("doctor_id", doctor["id"])
        .gte("scheduled_at", "now()")
        .order("scheduled_at")
        .limit(20)
        .execute()
    )
    unread = (
        admin.table("notifications").select("id", count="exact")
        .eq("user_id", user["user_id"]).eq("is_read", False).execute()
    )

    return render(request, "doctor/dashboard.html", {
        "user": user, "doctor": doctor,
        "appointments_today": today_appts.data or [],
        "notifications_count": unread.count or 0,
    })


@router.get("/doctor/appointments/{appointment_id}")
async def doctor_appointment_detail(request: Request, appointment_id: str):
    user = require_role(request, ["doctor", "nurse", "receptionist"])
    admin = get_supabase_admin()

    appt_resp = (
        admin.table("appointments")
        .select("*, patients(id, profile_id, blood_group, date_of_birth, profiles(full_name, phone))")
        .eq("id", appointment_id).single().execute()
    )
    appointment = appt_resp.data
    if not appointment:
        return RedirectResponse(url="/doctor/dashboard", status_code=303)

    patient = appointment.get("patients")

    if user["role"] == "doctor":
        doctor_id = _doctor_id(user)
    else:
        sub = admin.table("sub_accounts").select("doctor_id").eq("profile_id", user["user_id"]).single().execute()
        doctor_id = sub.data["doctor_id"]

    if appointment.get("doctor_id") != doctor_id:
        return RedirectResponse(url="/", status_code=303)

    documents = await mcp_client.call_tool("get_patient_reports", {
        "patient_id": patient["id"], "requesting_doctor_id": doctor_id,
    })
    prescription = (
        admin.table("prescriptions").select("*, medicines(*)")
        .eq("appointment_id", appointment_id).maybe_single().execute()
    )

    return render(request, "doctor/appointment_detail.html", {
        "appointment": appointment, "patient": patient,
        "documents": documents if isinstance(documents, list) else [],
        "prescription": prescription.data if prescription else None,
        "user": user,
    })


@router.post("/doctor/appointments/{appointment_id}/status")
async def doctor_update_status(
    request: Request, appointment_id: str, status: str = Form(...), notes: str = Form(""),
):
    user = require_role(request, ["doctor", "nurse"])
    admin = get_supabase_admin()

    if status == "completed":
        if user["role"] == "doctor":
            doctor_id = _doctor_id(user)
        else:
            sub = admin.table("sub_accounts").select("doctor_id").eq("profile_id", user["user_id"]).single().execute()
            doctor_id = sub.data["doctor_id"]
        await mcp_client.call_tool("complete_appointment", {
            "appointment_id": appointment_id, "doctor_id": doctor_id, "notes": notes,
        })
    else:
        admin.table("appointments").update({"status": status, "notes": notes}).eq("id", appointment_id).execute()

    response = RedirectResponse(url=f"/doctor/appointments/{appointment_id}", status_code=303)
    set_flash(response, "Appointment updated.", "success")
    return response


@router.get("/doctor/profile")
async def doctor_profile(request: Request):
    user = require_role(request, ["doctor"])
    admin = get_supabase_admin()
    profile = admin.table("profiles").select("*").eq("id", user["user_id"]).single().execute().data
    doctor = admin.table("doctors").select("*").eq("profile_id", user["user_id"]).single().execute().data
    return render(request, "doctor/profile.html", {"profile": profile, "doctor": doctor, "user": user})


@router.post("/doctor/profile")
async def doctor_profile_update(
    request: Request,
    clinic_name: str = Form(""), clinic_address: str = Form(""), specialization: str = Form(""),
    lat: str = Form(""), lng: str = Form(""), languages_spoken: list[str] = Form([]),
    consultation_fee: str = Form(""), experience_years: str = Form(""),
):
    user = require_role(request, ["doctor"])
    admin = get_supabase_admin()
    admin.table("doctors").update({
        "clinic_name": clinic_name, "clinic_address": clinic_address, "specialization": specialization,
        "lat": float(lat) if lat else None, "lng": float(lng) if lng else None,
        "languages_spoken": languages_spoken,
        "consultation_fee": float(consultation_fee) if consultation_fee else None,
        "experience_years": int(experience_years) if experience_years else None,
    }).eq("profile_id", user["user_id"]).execute()

    response = RedirectResponse(url="/doctor/profile", status_code=303)
    set_flash(response, "Profile updated.", "success")
    return response


# ----------------------------------------------------------------- nurse --
@router.get("/nurse/dashboard")
async def nurse_dashboard(request: Request):
    user = require_role(request, ["nurse", "receptionist"])
    admin = get_supabase_admin()
    sub = admin.table("sub_accounts").select("doctor_id").eq("profile_id", user["user_id"]).single().execute()
    doctor_id = sub.data["doctor_id"]

    appts = (
        admin.table("appointments")
        .select("*, patients(id, profiles(full_name))")
        .eq("doctor_id", doctor_id)
        .gte("scheduled_at", "now()")
        .order("scheduled_at")
        .limit(20)
        .execute()
    )
    return render(request, "nurse/dashboard.html", {"appointments": appts.data or [], "user": user})
