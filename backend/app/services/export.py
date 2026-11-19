"""
Service d'exports (sections 77-79, 95). Chaque fonction est pure (prend des
dicts en entrée, renvoie des bytes) pour rester testable sans base de données.

Bibliothèques utilisées, toutes gratuites/Open Source : `csv` (stdlib),
`openpyxl` (déjà utilisé Phase 16), `reportlab` (PDF).
"""
from __future__ import annotations

import csv
import io

from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet


def sites_to_csv(rows: list[dict], columns: list[str]) -> bytes:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({c: (row.get(c) if row.get(c) is not None else "") for c in columns})
    return buffer.getvalue().encode("utf-8-sig")  # BOM pour Excel FR


def sites_to_xlsx(rows: list[dict], columns: list[str], headers: dict[str, str] | None = None) -> bytes:
    headers = headers or {}
    wb = Workbook()
    ws = wb.active
    ws.title = "Sites"
    ws.append([headers.get(c, c) for c in columns])
    for row in rows:
        ws.append([row.get(c) if row.get(c) is not None else "" for c in columns])

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def site_fiche_pdf(
    site: dict,
    contacts: list[dict],
    documents: list[dict],
    contracts: list[dict],
    actions: list[dict],
    logo_mz_path: str | None = None,
    logo_ooredoo_path: str | None = None,
) -> bytes:
    """Fiche PDF d'un site (section 78) : logos, infos, contacts, documents,
    contrats, actions. Aucune section n'affiche de valeur inventée — un
    champ manquant est rendu "À COMPLÉTER", jamais vide silencieusement ni
    remplacé par une estimation."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=15 * mm, bottomMargin=15 * mm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("MzTitle", parent=styles["Title"], textColor=colors.HexColor("#AE2858"))
    heading_style = ParagraphStyle("MzHeading", parent=styles["Heading2"], textColor=colors.HexColor("#3D2140"))

    elements = []

    # En-tête avec logos
    if logo_mz_path or logo_ooredoo_path:
        header_cells = []
        if logo_mz_path:
            header_cells.append(Image(logo_mz_path, width=30 * mm, height=30 * mm, kind="proportional"))
        else:
            header_cells.append("")
        if logo_ooredoo_path:
            header_cells.append(Image(logo_ooredoo_path, width=40 * mm, height=15 * mm, kind="proportional"))
        else:
            header_cells.append("")
        header_table = Table([header_cells], colWidths=[90 * mm, 90 * mm])
        header_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
        elements.append(header_table)
        elements.append(Spacer(1, 8 * mm))

    elements.append(Paragraph("<b>MZ BUILDING</b> — Acquisition &amp; Project Management", styles["Normal"]))
    elements.append(Spacer(1, 3 * mm))
    elements.append(Paragraph(f"Fiche site — {site.get('code', 'À COMPLÉTER')}", title_style))
    elements.append(Spacer(1, 4 * mm))

    def _field(label: str, value) -> str:
        return f"<b>{label} :</b> {value if value not in (None, '') else 'À COMPLÉTER'}"

    info_lines = [
        _field("Nom", site.get("name")),
        _field("Wilaya", site.get("wilaya")),
        _field("Commune", site.get("commune")),
        _field("Adresse", site.get("address")),
        _field(
            "GPS",
            f"{site['latitude']}, {site['longitude']}"
            if site.get("latitude") is not None and site.get("longitude") is not None
            else None,
        ),
        _field("Propriétaire", site.get("owner_name")),
        _field("Organisme", site.get("organisme")),
        _field("Statut", site.get("status_label")),
    ]
    for line in info_lines:
        elements.append(Paragraph(line, styles["Normal"]))
    elements.append(Spacer(1, 6 * mm))

    def _section_table(title: str, headers_row: list[str], data_rows: list[list[str]]):
        elements.append(Paragraph(title, heading_style))
        if not data_rows:
            elements.append(Paragraph("Aucune donnée enregistrée.", styles["Normal"]))
        else:
            table_data = [headers_row] + data_rows
            t = Table(table_data, hAlign="LEFT")
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3D2140")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            elements.append(t)
        elements.append(Spacer(1, 5 * mm))

    _section_table(
        "Contacts",
        ["Nom", "Fonction", "Téléphone"],
        [[f"{c.get('first_name', '')} {c.get('last_name', '')}".strip() or "À COMPLÉTER",
          c.get("role_label") or "—", c.get("phone") or "À COMPLÉTER"] for c in contacts],
    )
    _section_table(
        "Documents",
        ["Fichier", "Catégorie", "Version"],
        [[d.get("filename", ""), d.get("category", ""), str(d.get("version", 1))] for d in documents],
    )
    _section_table(
        "Contrats",
        ["Référence", "Statut", "Montant"],
        [[c.get("reference") or "À COMPLÉTER", c.get("status") or "—",
          f"{c['amount']} DA" if c.get("amount") is not None else "À COMPLÉTER"] for c in contracts],
    )
    _section_table(
        "Actions",
        ["Action", "Échéance", "Statut"],
        [[a.get("title", ""), a.get("due_date") or "—", a.get("status", "")] for a in actions],
    )

    doc.build(elements)
    return buffer.getvalue()
