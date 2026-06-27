import asyncio
from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse

from services.templates import render
from services.auth_service import require_role, set_flash
from services.supabase_client import get_supabase_admin
from services import mcp_client

router = APIRouter()


@router.get("/doctors")
async def search_doctors_page(
    request: Request,
    symptoms: str = "",
    lat: str = "",
    lng: str = "",
    radius_km: str = "10",
    specialization: str = "",
):
    mcp_client.fire_and_forget_ping()
    doctors_list = []
    mcp_slow = False
    if symptoms and lat and lng:
        elapsed = await mcp_client.ping_mcp()
        mcp_slow = elapsed > 5.0
        payload = {
            "symptoms": symptoms,
            "language": "en",
            "lat": float(lat),
            "lng": float(lng),
            "radius_km": float(radius_km) if radius_km else 10,
        }
        if specialization:
            payload["specialization"] = specialization
        try:
            doctors_list = await mcp_client.call_tool("search_doctors", payload)
        except Exception:
            doctors_list = []

    return render(request, "doctors/search.html", {
        "doctors": doctors_list,
        "symptoms": symptoms,
        "query_params": {"lat": lat, "lng": lng, "radius_km": radius_km, "specialization": specialization},
        "mcp_slow": mcp_slow,
    })


@router.get("/doctors/{doctor_id}")
async def doctor_profile_page(request: Request, doctor_id: str):
    profile_result, ratings_result = await asyncio.gather(
        mcp_client.call_tool("get_doctor_profile", {"doctor_id": doctor_id}),
        mcp_client.call_tool("get_doctor_ratings", {"doctor_id": doctor_id}),
    )
    return render(request, "doctors/profile.html", {
        "doctor": profile_result,
        "ratings": ratings_result,
        "reviews": ratings_result.get("recent_reviews", []) if isinstance(ratings_result, dict) else [],
    })


@router.get("/doctors/{doctor_id}/book")
async def book_doctor_page(request: Request, doctor_id: str, date: str = ""):
    user = require_role(request, ["patient"])
    doctor = await mcp_client.call_tool("get_doctor_profile", {"doctor_id": doctor_id})
    available_slots = []
    if date:
        avail = await mcp_client.call_tool("check_availability", {"doctor_id": doctor_id, "date": date})
        available_slots = avail.get("available_slots", []) if isinstance(avail, dict) else []
    return render(request, "doctors/book.html", {
        "doctor": doctor, "date": date, "available_slots": available_slots, "user": user,
    })


@router.post("/doctors/{doctor_id}/book")
async def book_doctor_submit(
    request: Request,
    doctor_id: str,
    scheduled_at: str = Form(...),
    symptoms_text: str = Form(""),
    symptoms_language: str = Form("en"),
    is_urgent: str = Form(""),
):
    user = require_role(request, ["patient"])
    admin = get_supabase_admin()
    patient_resp = admin.table("patients").select("id").eq("profile_id", user["user_id"]).single().execute()
    patient_id = patient_resp.data["id"]

    result = await mcp_client.call_tool("book_appointment", {
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "scheduled_at": scheduled_at,
        "symptoms_text": symptoms_text,
        "symptoms_language": symptoms_language,
        "is_urgent": bool(is_urgent),
    })

    response = RedirectResponse(url="/patient/appointments", status_code=303)
    doctor_name = result.get("doctor_name", "your doctor") if isinstance(result, dict) else "your doctor"
    set_flash(response, f"Appointment booked with {doctor_name}!", "success")
    return response
