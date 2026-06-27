import uuid
from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse

from services.auth_service import require_role, set_flash
from services.supabase_client import get_supabase_admin
from services.pdf_service import generate_prescription_pdf

router = APIRouter()


@router.post("/doctor/appointments/{appointment_id}/prescription")
async def create_prescription(
    request: Request,
    appointment_id: str,
    notes: str = Form(""),
    medicine_names: list[str] = Form([]),
    medicine_dosages: list[str] = Form([]),
    medicine_frequencies: list[str] = Form([]),
    medicine_durations: list[str] = Form([]),
    medicine_instructions: list[str] = Form([]),
):
    user = require_role(request, ["doctor"])
    admin = get_supabase_admin()

    doctor = admin.table("doctors").select("*, profiles(full_name)").eq(
        "profile_id", user["user_id"]
    ).single().execute().data

    appt = admin.table("appointments").select(
        "*, patients(id, profile_id, date_of_birth, blood_group, profiles(full_name))"
    ).eq("id", appointment_id).single().execute().data
    if not appt or appt["doctor_id"] != doctor["id"]:
        return RedirectResponse(url="/doctor/dashboard", status_code=303)

    patient = appt["patients"]

    medicines = []
    for i in range(len(medicine_names)):
        if not medicine_names[i].strip():
            continue
        medicines.append({
            "name": medicine_names[i],
            "dosage": medicine_dosages[i] if i < len(medicine_dosages) else "",
            "frequency": medicine_frequencies[i] if i < len(medicine_frequencies) else "",
            "duration_days": int(medicine_durations[i]) if i < len(medicine_durations) and medicine_durations[i] else None,
            "instructions": medicine_instructions[i] if i < len(medicine_instructions) else "",
        })

    doctor_info = {
        "full_name": doctor["profiles"]["full_name"],
        "registration_number": doctor["registration_number"],
        "specialization": doctor["specialization"],
        "clinic_name": doctor.get("clinic_name", ""),
    }
    patient_info = {
        "full_name": patient["profiles"]["full_name"],
        "date_of_birth": patient.get("date_of_birth", ""),
        "blood_group": patient.get("blood_group", ""),
    }

    pdf_bytes = generate_prescription_pdf(doctor_info, patient_info, medicines, notes)

    storage_path = f"{patient['id']}/{appointment_id}/prescription_{uuid.uuid4().hex[:8]}.pdf"
    admin.storage.from_("prescriptions").upload(
        storage_path, pdf_bytes, {"content-type": "application/pdf", "upsert": "true"}
    )
    signed = admin.storage.from_("prescriptions").create_signed_url(storage_path, 60 * 60 * 24 * 7)
    pdf_url = signed.get("signedURL") or signed.get("signed_url") or ""

    prescription = admin.table("prescriptions").insert({
        "appointment_id": appointment_id,
        "doctor_id": doctor["id"],
        "patient_id": patient["id"],
        "notes": notes,
        "pdf_url": pdf_url,
    }).execute().data[0]

    for m in medicines:
        admin.table("medicines").insert({**m, "prescription_id": prescription["id"]}).execute()

    admin.table("notifications").insert({
        "user_id": patient["profile_id"] if "profile_id" in patient else None,
        "type": "prescription",
        "title": "New prescription available",
        "message": f"Dr. {doctor['profiles']['full_name']} has issued a new prescription.",
    }).execute()

    response = RedirectResponse(url=f"/doctor/appointments/{appointment_id}", status_code=303)
    set_flash(response, "Prescription created and sent to patient.", "success")
    return response
