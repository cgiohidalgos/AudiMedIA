"""Generador de reportes PDF."""
from typing import Dict, Any
from io import BytesIO
from datetime import datetime

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


def generate_pdf_report(audit_data: Dict[str, Any]) -> BytesIO:
    """
    Genera un reporte de auditoría en formato PDF.
    
    Args:
        audit_data: Diccionario con datos de la auditoría
            - paciente: Datos del paciente
            - riesgo_global: Nivel de riesgo (alto/medio/bajo)
            - total_hallazgos: Total de hallazgos
            - exposicion_glosas: Exposición económica en COP
            - hallazgos: Lista de hallazgos
            - hallazgos_por_riesgo: Conteo por riesgo
            - hallazgos_por_modulo: Conteo por módulo
            - recomendacion_general: Recomendación general
    
    Returns:
        BytesIO con contenido del archivo PDF
    """
    if not REPORTLAB_AVAILABLE:
        raise ImportError("reportlab no está instalado. Instalar con: pip install reportlab")
    
    # Crear buffer
    buffer = BytesIO()
    
    # Crear documento
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72,
    )
    
    # Estilos
    styles = getSampleStyleSheet()
    
    # Estilo título principal
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1E40AF'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # Estilo subtítulo
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#1F2937'),
        spaceAfter=12,
        fontName='Helvetica-Bold'
    )
    
    # Estilo para texto normal
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#374151'),
        spaceAfter=6,
        alignment=TA_JUSTIFY
    )
    
    # Contenido del documento
    story = []
    
    # Datos del paciente
    paciente = audit_data.get("paciente", {})
    riesgo = audit_data.get("riesgo_global", "bajo")
    hallazgos = audit_data.get("hallazgos", [])
    
    # Colores según riesgo
    risk_colors = {
        "alto": colors.HexColor('#FEF2F2'),
        "medio": colors.HexColor('#FFFBEB'),
        "bajo": colors.HexColor('#F0FDF4'),
        "pending": colors.HexColor('#F3F4F6')
    }
    
    risk_text_colors = {
        "alto": colors.HexColor('#DC2626'),
        "medio": colors.HexColor('#F59E0B'),
        "bajo": colors.HexColor('#16A34A'),
        "pending": colors.HexColor('#6B7280')
    }
    
    # ===== ENCABEZADO =====
    story.append(Paragraph("🏥 REPORTE DE AUDITORÍA MÉDICA", title_style))
    story.append(Paragraph(
        f"Sistema AudiMedIA - Auditoría Concurrente con IA<br/>"
        f"Generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}",
        ParagraphStyle('Subtitle', parent=normal_style, alignment=TA_CENTER, fontSize=9, textColor=colors.HexColor('#6B7280'))
    ))
    story.append(Spacer(1, 0.3*inch))
    
    # ===== INFORMACIÓN DEL PACIENTE =====
    story.append(Paragraph("📋 Información del Paciente", subtitle_style))
    
    info_data = [
        ['<b>Identificador:</b>', paciente.get('label', 'N/A')],
        ['<b>Diagnóstico Principal:</b>', paciente.get('diagnostico_principal', 'N/A')],
        ['<b>Código CIE-10:</b>', paciente.get('codigo_cie10', 'N/A')],
        ['<b>Días Hospitalización:</b>', str(paciente.get('dias_hospitalizacion', 'N/A'))],
        ['<b>Nivel de Riesgo:</b>', f'<b>{riesgo.upper()}</b>'],
        ['<b>Total Hallazgos:</b>', str(audit_data.get('total_hallazgos', 0))],
        ['<b>Exposición a Glosas:</b>', f"${audit_data.get('exposicion_glosas', 0):,.0f} COP"],
    ]
    
    info_table = Table(info_data, colWidths=[2.5*inch, 3.5*inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F3F4F6')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#1F2937')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
        # Color especial para riesgo
        ('BACKGROUND', (1, 4), (1, 4), risk_colors.get(riesgo, colors.white)),
        ('TEXTCOLOR', (1, 4), (1, 4), risk_text_colors.get(riesgo, colors.black)),
    ]))
    
    story.append(info_table)
    story.append(Spacer(1, 0.3*inch))
    
    # ===== HALLAZGOS =====
    story.append(Paragraph("🔍 Hallazgos de Auditoría", subtitle_style))
    
    if hallazgos:
        # Agrupar por módulo
        hallazgos_por_modulo = {}
        for h in hallazgos:
            modulo = h.modulo if hasattr(h, 'modulo') else h.get('modulo', 'General')
            if modulo not in hallazgos_por_modulo:
                hallazgos_por_modulo[modulo] = []
            hallazgos_por_modulo[modulo].append(h)
        
        for modulo, findings in hallazgos_por_modulo.items():
            # Título del módulo
            modulo_style = ParagraphStyle(
                'Modulo',
                parent=normal_style,
                fontSize=12,
                textColor=colors.HexColor('#1E40AF'),
                fontName='Helvetica-Bold',
                spaceAfter=8
            )
            story.append(Paragraph(modulo.replace('_', ' ').title(), modulo_style))
            
            # Tabla de hallazgos del módulo
            findings_data = [['Riesgo', 'Descripción', 'Valor Glosa']]
            
            for finding in findings:
                riesgo_f = finding.riesgo if hasattr(finding, 'riesgo') else finding.get('riesgo', 'bajo')
                desc = finding.descripcion if hasattr(finding, 'descripcion') else finding.get('descripcion', '')
                valor = finding.valor_glosa_estimado if hasattr(finding, 'valor_glosa_estimado') else finding.get('valor_glosa_estimado', 0)
                rec = finding.recomendacion if hasattr(finding, 'recomendacion') else finding.get('recomendacion', '')
                
                valor_fmt = f"${valor:,.0f}" if valor else "N/A"
                
                # Agregar fila con descripción y recomendación
                findings_data.append([
                    Paragraph(f"<b>{riesgo_f.upper()}</b>", normal_style),
                    Paragraph(f"{desc}<br/><br/><i>💡 Recomendación: {rec}</i>", normal_style),
                    Paragraph(valor_fmt, normal_style)
                ])
            
            findings_table = Table(findings_data, colWidths=[0.8*inch, 3.7*inch, 1.5*inch])
            
            # Estilos de la tabla
            table_style = [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3B82F6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 8),
                ('ALIGN', (0, 1), (0, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')]),
            ]
            
            # Colores por riesgo
            for idx, finding in enumerate(findings, start=1):
                riesgo_f = finding.riesgo if hasattr(finding, 'riesgo') else finding.get('riesgo', 'bajo')
                table_style.append(('BACKGROUND', (0, idx), (0, idx), risk_colors.get(riesgo_f, colors.white)))
                table_style.append(('TEXTCOLOR', (0, idx), (0, idx), risk_text_colors.get(riesgo_f, colors.black)))
            
            findings_table.setStyle(TableStyle(table_style))
            story.append(findings_table)
            story.append(Spacer(1, 0.2*inch))
    else:
        story.append(Paragraph(
            "<i>No se encontraron hallazgos para este paciente.</i>",
            ParagraphStyle('Italic', parent=normal_style, textColor=colors.HexColor('#6B7280'))
        ))
    
    story.append(Spacer(1, 0.3*inch))
    
    # ===== RECOMENDACIÓN GENERAL =====
    story.append(Paragraph("📝 Recomendación General", subtitle_style))
    
    rec_table = Table(
        [[Paragraph(audit_data.get("recomendacion_general", "Continuar con auditoría de rutina."), normal_style)]],
        colWidths=[6*inch]
    )
    rec_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F0FDF4')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#166534')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#BBF7D0')),
    ]))
    
    story.append(rec_table)
    story.append(Spacer(1, 0.5*inch))
    
    # ===== FOOTER =====
    footer_text = (
        "<i>Este reporte fue generado automáticamente por el Sistema AudiMedIA. "
        "La información presentada debe ser validada por personal médico calificado.</i>"
    )
    story.append(Paragraph(
        footer_text,
        ParagraphStyle('Footer', parent=normal_style, fontSize=8, textColor=colors.HexColor('#6B7280'), alignment=TA_CENTER)
    ))
    
    # Construir PDF
    doc.build(story)
    
    # Devolver buffer
    buffer.seek(0)
    return buffer
