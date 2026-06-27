from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse

from services.templates import render
from services.auth_service import require_role, set_flash
from services.supabase_client import get_supabase_admin
from services import mcp_client

router = APIRouter()


@router.get("/patient/documents")
async def patient_documents(request: Request):
    user = require_role(request, ["patient"])
    admin = get_supabase_admin()
    patient = admin.table("patients").select("id").eq("profile_id", user["user_id"]).single().execute().data
    patient_id = patient["id"]

    documents = (
        admin.table("documents").select("*").eq("patient_id", patient_id)
        .order("created_at", desc=True).execute()
    )
    doc_ids = [d["id"] for d in (documents.data or [])]
    access_rows = []
    if doc_ids:
        access_rows = (
            admin.table("document_access")
            .select("*, doctors(id, specialization, profiles(full_name))")
            .in_("document_id", doc_ids).is_("revoked_at", "null").execute()
        ).data or []
    access_by_doc: dict[str, list] = {}
    for a in access_rows:
        access_by_doc.setdefault(a["document_id"], []).append(a)

    doctors_list = (
        admin.table("doctors").select("id, specialization, clinic_name, profiles(full_name)")
        .eq("is_verified", True).execute()
    ).data or []

    return render(request, "patient/documents.html", {
        "documents": documents.data or [],
        "access_by_doc": access_by_doc,
        "doctors_list": doctors_list,
        "user": user,
    })


@router.post("/patient/documents/upload")
async def patient_upload_document(
    request: Request,
    doc_type: str = Form("other"), file_url: str = Form(...), file_name: str = Form(...),
    description: str = Form(""), appointment_id: str = Form(""),
):
    user = require_role(request, ["patient"])
    admin = get_supabase_admin()
    patient = admin.table("patients").select("id").eq("profile_id", user["user_id"]).single().execute().data

    await mcp_client.call_tool("upload_document_meta", {
        "patient_id": patient["id"],
        "uploaded_by": user["user_id"],
        "appointment_id": appointment_id or None,
        "doc_type": doc_type,
        "file_url": file_url,
        "file_name": file_name,
        "description": description,
    })

    response = RedirectResponse(url="/patient/documents", status_code=303)
    set_flash(response, "Document uploaded.", "success")
    return response


@router.post("/patient/documents/{document_id}/grant")
async def grant_document_access(request: Request, document_id: str, doctor_id: str = Form(...)):
    require_role(request, ["patient"])
    admin = get_supabase_admin()
    admin.table("document_access").upsert({
        "document_id": document_id, "granted_to_doctor_id": doctor_id, "revoked_at": None,
    }, on_conflict="document_id,granted_to_doctor_id").execute()

    response = RedirectResponse(url="/patient/documents", status_code=303)
    set_flash(response, "Access granted.", "success")
    return response


@router.post("/patient/documents/{document_id}/revoke/{doctor_id}")
async def revoke_document_access(request: Request, document_id: str, doctor_id: str):
    require_role(request, ["patient"])
    admin = get_supabase_admin()
    admin.table("document_access").update({"revoked_at": "now()"}).eq(
        "document_id", document_id
    ).eq("granted_to_doctor_id", doctor_id).execute()

    response = RedirectResponse(url="/patient/documents", status_code=303)
    set_flash(response, "Access revoked.", "success")
    return response


# ----------------------------------------------------------------- nurse --
@router.get("/nurse/appointments/{appointment_id}/upload")
async def nurse_upload_page(request: Request, appointment_id: str):
    user = require_role(request, ["nurse", "receptionist"])
    admin = get_supabase_admin()
    appt = admin.table("appointments").select("patient_id, patients(profiles(full_name))").eq(
        "id", appointment_id
    ).single().execute().data
    return render(request, "nurse/upload.html", {
        "appointment_id": appointment_id,
        "patient_id": appt["patient_id"] if appt else "",
        "patient_name": appt["patients"]["profiles"]["full_name"] if appt else "",
        "user": user,
    })


@router.post("/nurse/appointments/{appointment_id}/upload")
async def nurse_upload_submit(
    request: Request, appointment_id: str,
    doc_type: str = Form("other"), file_url: str = Form(...), file_name: str = Form(...),
    description: str = Form(""), patient_id: str = Form(...),
):
    user = require_role(request, ["nurse", "receptionist"])

    await mcp_client.call_tool("upload_document_meta", {
        "patient_id": patient_id,
        "uploaded_by": user["user_id"],
        "appointment_id": appointment_id,
        "doc_type": doc_type,
        "file_url": file_url,
        "file_name": file_name,
        "description": description,
    })

    response = RedirectResponse(url="/nurse/dashboard", status_code=303)
    set_flash(response, "Document uploaded.", "success")
    return response
