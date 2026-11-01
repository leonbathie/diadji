"""
Module de Génération de Factures et Tickets PDF - DIADJI FAMILY
Utilise ReportLab pour produire des documents PDF haute résolution,
élégants et parfaitement mis en page.
"""

import io
import os
import html
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm


def format_fcfa(val):
    try:
        n = int(round(float(val or 0)))
        return f"{n:,}".replace(",", " ") + " FCFA"
    except Exception:
        return f"{val} FCFA"


def generate_invoice_pdf(sale_data, output_path=None):
    """
    Génère une facture A4 professionnelle au format PDF pour une vente donnée.
    Si output_path est fourni, enregistre sur le disque.
    Sinon, retourne les octets (bytes) du PDF généré.
    """
    buffer = io.BytesIO() if output_path is None else output_path

    # Dimensions et marges A4 (210 x 297 mm)
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )

    story = []

    # Palette de couleurs DIADJI FAMILY
    primary = colors.HexColor("#0F172A")    # Bleu nuit profond
    accent = colors.HexColor("#0D9488")     # Émeraude / Sarcelle noble
    accent_dark = colors.HexColor("#047857")
    gold = colors.HexColor("#D97706")
    bg_light = colors.HexColor("#F8FAFC")
    bg_subtle = colors.HexColor("#F1F5F9")
    text_dark = colors.HexColor("#1E293B")
    text_muted = colors.HexColor("#64748B")
    border_color = colors.HexColor("#CBD5E1")

    # Feuilles de styles
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "CompanyTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=primary,
    )

    subtitle_style = ParagraphStyle(
        "CompanySubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=accent_dark,
    )

    contact_style = ParagraphStyle(
        "CompanyContact",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=text_muted,
    )

    doc_badge_style = ParagraphStyle(
        "DocBadge",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=16,
        textColor=accent_dark,
        alignment=2,  # Aligné à droite
    )

    doc_meta_style = ParagraphStyle(
        "DocMeta",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=text_dark,
        alignment=2,
    )

    client_header_style = ParagraphStyle(
        "ClientHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=primary,
    )

    client_text_style = ParagraphStyle(
        "ClientText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=text_dark,
    )

    table_th = ParagraphStyle(
        "TableTH",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=colors.white,
    )

    table_th_right = ParagraphStyle(
        "TableTHRight",
        parent=table_th,
        alignment=2,
    )

    table_td = ParagraphStyle(
        "TableTD",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=text_dark,
    )

    table_td_bold = ParagraphStyle(
        "TableTDBold",
        parent=table_td,
        fontName="Helvetica-Bold",
    )

    table_td_right = ParagraphStyle(
        "TableTDRight",
        parent=table_td,
        alignment=2,
    )

    table_td_right_bold = ParagraphStyle(
        "TableTDRightBold",
        parent=table_td,
        fontName="Helvetica-Bold",
        alignment=2,
    )

    # 1. BANDEAU SUPÉRIEUR COLORE
    # Tableau d'en-tête (Logo / Nom à gauche, Badge Facture à droite)
    ticket_num = html.escape(str(sale_data.get("numero_ticket") or "TK-00000000-0000"))
    date_vente = html.escape(str(sale_data.get("date_vente") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    nom_client = html.escape(str(sale_data.get("nom_client") or "Client Comptant"))
    tel_client = html.escape(str(sale_data.get("telephone_client") or "—"))
    mode_paiement = html.escape(str(sale_data.get("mode_paiement") or "Espèces"))

    left_header = [
        Paragraph("DIADJI FAMILY", title_style),
        Paragraph("Commerce Général • Matériaux de Construction • Électricité • Outillage", subtitle_style),
        Spacer(1, 2 * mm),
        Paragraph("<b>Siège :</b> Dakar, Sénégal &nbsp;|&nbsp; <b>Tél :</b> +221 77 000 00 00 / +221 78 000 00 00", contact_style),
        Paragraph("<b>Service Client :</b> contact@diadjifamily.sn &nbsp;|&nbsp; <b>Boutique & Caisse Principale</b>", contact_style),
    ]

    right_header = [
        Paragraph("FACTURE / REÇU DE CAISSE", doc_badge_style),
        Spacer(1, 2 * mm),
        Paragraph(f"<b>N° Pièce :</b> <font color='#0F172A'>{ticket_num}</font>", doc_meta_style),
        Paragraph(f"<b>Date :</b> {date_vente}", doc_meta_style),
        Paragraph(f"<b>Règlement :</b> {mode_paiement}", doc_meta_style),
        Paragraph("<b>Statut :</b> <font color='#047857'><b>PAYÉ / ACQUITTÉ</b></font>", doc_meta_style),
    ]

    header_table = Table([[left_header, right_header]], colWidths=[110 * mm, 72 * mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 4 * mm))

    # Ligne de séparation élégante
    story.append(HRFlowable(width="100%", thickness=1.5, color=accent, spaceBefore=1, spaceAfter=4 * mm))

    # 2. ENCADRÉ CLIENT & INFORMATIONS DE VENTE
    client_box_content = [
        [
            Paragraph("<b>CLIENT / FACTURÉ À :</b>", client_header_style),
            Paragraph("<b>DÉTAILS DU PAIEMENT :</b>", client_header_style)
        ],
        [
            Paragraph(f"<b>Nom :</b> {nom_client}<br/><b>Téléphone :</b> {tel_client}", client_text_style),
            Paragraph(f"<b>Mode :</b> {mode_paiement}<br/><b>Caisse :</b> Principale (Dakar)", client_text_style)
        ]
    ]
    client_table = Table(client_box_content, colWidths=[91 * mm, 91 * mm])
    client_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), bg_light),
        ('BOX', (0, 0), (-1, -1), 0.5, border_color),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(client_table)
    story.append(Spacer(1, 4 * mm))

    # 3. TABLE DES ARTICLES VENDUS
    lignes = sale_data.get("lignes", [])
    
    table_data = [
        [
            Paragraph("Réf.", table_th),
            Paragraph("Désignation de l'Article", table_th),
            Paragraph("Quantité", table_th_right),
            Paragraph("Prix Unit. (FCFA)", table_th_right),
            Paragraph("Total Ligne (FCFA)", table_th_right),
        ]
    ]

    for idx, l in enumerate(lignes, 1):
        ref = html.escape(str(l.get("article_id") or f"ART-{idx:03d}"))
        nom = html.escape(str(l.get("nom_article") or "Article"))
        qty = float(l.get("quantite", 1))
        unit = str(l.get("unite") or "")
        qty_str = html.escape(f"{qty:g} {unit}".strip())
        pu_str = format_fcfa(l.get("prix_unitaire", 0)).replace(" FCFA", "")
        tot_str = format_fcfa(l.get("total_ligne", 0)).replace(" FCFA", "")

        table_data.append([
            Paragraph(ref, table_td),
            Paragraph(nom, table_td_bold),
            Paragraph(qty_str, table_td_right),
            Paragraph(pu_str, table_td_right),
            Paragraph(f"<b>{tot_str}</b>", table_td_right_bold),
        ])

    if not lignes:
        table_data.append([
            Paragraph("—", table_td),
            Paragraph("Aucun article répertorié", table_td),
            Paragraph("0", table_td_right),
            Paragraph("0", table_td_right),
            Paragraph("0", table_td_right),
        ])

    articles_table = Table(
        table_data,
        colWidths=[24 * mm, 80 * mm, 26 * mm, 26 * mm, 26 * mm]
    )

    t_style = [
        ('BACKGROUND', (0, 0), (-1, 0), primary),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('BOX', (0, 0), (-1, -1), 0.5, primary),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
    ]

    # Alternance de couleurs des lignes
    for r in range(1, len(table_data)):
        if r % 2 == 0:
            t_style.append(('BACKGROUND', (0, r), (-1, r), bg_light))
        else:
            t_style.append(('BACKGROUND', (0, r), (-1, r), colors.white))

    articles_table.setStyle(TableStyle(t_style))
    story.append(articles_table)
    story.append(Spacer(1, 4 * mm))

    # 4. BLOC DES TOTAUX ET CONDITIONS
    montant_total = float(sale_data.get("montant_total", 0))
    remise = float(sale_data.get("remise", 0))
    montant_net = float(sale_data.get("montant_net", montant_total - remise))
    montant_verse = float(sale_data.get("montant_verse", 0))
    monnaie_rendue = float(sale_data.get("monnaie_rendue", 0))

    # Encadré gauche : Conditions et Remerciements
    left_notes = [
        Paragraph("<b>CONDITIONS DE VENTE & REMERCIEMENTS :</b>", client_header_style),
        Spacer(1, 1 * mm),
        Paragraph("• Les marchandises vendues et livrées conformes ne sont ni reprises ni échangées.", contact_style),
        Paragraph("• Tout litige ou réclamation doit être signalé dans les 24 heures muni de la présente facture.", contact_style),
        Paragraph("• DIADJI FAMILY vous remercie chaleureusement pour votre fidélité et votre confiance !", subtitle_style),
        Spacer(1, 4 * mm),
        Paragraph("<b>Cachet & Visa de la Caisse :</b>", contact_style),
        Spacer(1, 8 * mm),
        Paragraph("<font color='#94A3B8'><i>[ Validé et Enregistré en Base Sécurisée ]</i></font>", contact_style),
    ]

    # Tableau droit : Décomposition financière
    totals_data = [
        [Paragraph("Total Brut :", table_td_bold), Paragraph(format_fcfa(montant_total), table_td_right)],
    ]

    if remise > 0:
        totals_data.append([
            Paragraph("Remise Commerciale :", table_td_bold),
            Paragraph(f"-{format_fcfa(remise)}", table_td_right)
        ])

    totals_data.append([
        Paragraph("<b>NET À PAYER :</b>", ParagraphStyle('NetLbl', parent=table_td_bold, fontSize=11, textColor=colors.white)),
        Paragraph(f"<b>{format_fcfa(montant_net)}</b>", ParagraphStyle('NetVal', parent=table_td_right_bold, fontSize=11, textColor=colors.white))
    ])

    if montant_verse > 0:
        totals_data.append([
            Paragraph("Montant Versé :", table_td),
            Paragraph(format_fcfa(montant_verse), table_td_right)
        ])
        totals_data.append([
            Paragraph("Monnaie Rendue :", table_td_bold),
            Paragraph(format_fcfa(monnaie_rendue), table_td_right_bold)
        ])

    totals_table = Table(totals_data, colWidths=[40 * mm, 42 * mm])
    tot_styles = [
        ('BOX', (0, 0), (-1, -1), 0.5, border_color),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#F1F5F9")),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('BACKGROUND', (0, 0), (-1, -1), colors.white),
    ]

    # Mettre en valeur la ligne NET À PAYER (fond émeraude)
    net_idx = 1 if remise > 0 else 1
    for i, row in enumerate(totals_data):
        if "NET À PAYER" in row[0].text:
            tot_styles.append(('BACKGROUND', (0, i), (-1, i), accent_dark))
            break

    totals_table.setStyle(TableStyle(tot_styles))

    summary_block = Table([[left_notes, totals_table]], colWidths=[96 * mm, 86 * mm])
    summary_block.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))

    story.append(KeepTogether(summary_block))

    # 5. PIED DE PAGE
    story.append(Spacer(1, 8 * mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E2E8F0"), spaceBefore=2, spaceAfter=2 * mm))
    footer_text = Paragraph(
        "<font color='#94A3B8'>DIADJI FAMILY — Logiciel de Caisse & Gestion de Stock Embarqué — Facture certifiée conforme</font>",
        ParagraphStyle("Footer", parent=contact_style, alignment=1)
    )
    story.append(footer_text)

    # Construction du PDF
    doc.build(story)

    if output_path is None:
        buffer.seek(0)
        return buffer.getvalue()
    return output_path
