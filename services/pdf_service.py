import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

PRIMARY = colors.HexColor("#028090")
DARK = colors.HexColor("#1A2E35")


def generate_prescription_pdf(doctor: dict, patient: dict, medicines: list[dict], notes: str) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=20 * mm, bottomMargin=20 * mm,
                             leftMargin=20 * mm, rightMargin=20 * mm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("title", parent=styles["Title"], textColor=PRIMARY, fontSize=20)
    h_style = ParagraphStyle("h", parent=styles["Heading2"], textColor=DARK, fontSize=12)
    n_style = ParagraphStyle("n", parent=styles["Normal"], fontSize=10)
    footer_style = ParagraphStyle("f", parent=styles["Normal"], fontSize=8, textColor=colors.grey)

    elements = []
    elements.append(Paragraph("MedBridge", title_style))
    elements.append(Paragraph("Medical Prescription", h_style))
    elements.append(Spacer(1, 6))
    elements.append(HRFlowable(width="100%", color=PRIMARY, thickness=1))
    elements.append(Spacer(1, 10))

    doctor_info = (
        f"<b>{doctor.get('full_name', 'Doctor')}</b><br/>"
        f"Registration No: {doctor.get('registration_number', '-')}<br/>"
        f"Specialization: {doctor.get('specialization', '-')}<br/>"
        f"Clinic: {doctor.get('clinic_name', '-')}"
    )
    patient_info = (
        f"<b>{patient.get('full_name', 'Patient')}</b><br/>"
        f"DOB: {patient.get('date_of_birth', '-')}<br/>"
        f"Blood Group: {patient.get('blood_group', '-')}<br/>"
        f"Date: {datetime.now().strftime('%d %b %Y')}"
    )
    info_table = Table([[Paragraph(doctor_info, n_style), Paragraph(patient_info, n_style)]],
                        colWidths=[doc.width / 2.0] * 2)
    info_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    elements.append(info_table)
    elements.append(Spacer(1, 14))
    elements.append(HRFlowable(width="100%", color=colors.lightgrey, thickness=0.5))
    elements.append(Spacer(1, 14))

    elements.append(Paragraph("Medicines", h_style))
    elements.append(Spacer(1, 6))
    data = [["Name", "Dosage", "Frequency", "Duration", "Instructions"]]
    for m in medicines:
        data.append([
            m.get("name", ""), m.get("dosage", ""), m.get("frequency", ""),
            f"{m.get('duration_days', '')} days" if m.get("duration_days") else "",
            m.get("instructions", ""),
        ])
    med_table = Table(data, colWidths=[doc.width * w for w in (0.24, 0.16, 0.18, 0.14, 0.28)])
    med_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4FBFA")]),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(med_table)
    elements.append(Spacer(1, 16))

    if notes:
        elements.append(Paragraph("Notes", h_style))
        elements.append(Paragraph(notes.replace("\n", "<br/>"), n_style))
        elements.append(Spacer(1, 16))

    elements.append(HRFlowable(width="100%", color=colors.lightgrey, thickness=0.5))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph("This prescription was generated via MedBridge platform", footer_style))

    doc.build(elements)
    return buf.getvalue()
