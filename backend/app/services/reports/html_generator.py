"""Generador de reportes HTML."""
from typing import Dict, Any
from datetime import datetime


def generate_html_report(audit_data: Dict[str, Any]) -> str:
    """
    Genera un reporte de auditoría en formato HTML.
    
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
        String con contenido HTML del reporte
    """
    paciente = audit_data.get("paciente", {})
    riesgo = audit_data.get("riesgo_global", "bajo")
    hallazgos = audit_data.get("hallazgos", [])
    
    # Color según riesgo
    color_riesgo = {
        "alto": "#dc2626",
        "medio": "#f59e0b",
        "bajo": "#16a34a",
        "pending": "#6b7280"
    }.get(riesgo, "#6b7280")
    
    # Formatear exposición COP
    exposicion = audit_data.get("exposicion_glosas", 0)
    exposicion_fmt = f"${exposicion:,.0f} COP" if exposicion else "No aplica"
    
    # Agrupar hallazgos por módulo
    hallazgos_por_modulo = {}
    for h in hallazgos:
        modulo = h.modulo if hasattr(h, 'modulo') else h.get('modulo', 'General')
        if modulo not in hallazgos_por_modulo:
            hallazgos_por_modulo[modulo] = []
        hallazgos_por_modulo[modulo].append(h)
    
    # Generar HTML
    html = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reporte de Auditoría - {paciente.get('label', 'Paciente')}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #1f2937;
            background: #f9fafb;
            padding: 2rem;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 0.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
            color: white;
            padding: 2rem;
        }}
        
        .header h1 {{
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }}
        
        .header p {{
            opacity: 0.9;
            font-size: 0.95rem;
        }}
        
        .content {{
            padding: 2rem;
        }}
        
        .section {{
            margin-bottom: 2rem;
        }}
        
        .section-title {{
            font-size: 1.5rem;
            font-weight: 600;
            border-bottom: 2px solid #e5e7eb;
            padding-bottom: 0.5rem;
            margin-bottom: 1rem;
            color: #111827;
        }}
        
        .info-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        
        .info-card {{
            background: #f3f4f6;
            padding: 1rem;
            border-radius: 0.375rem;
            border-left: 4px solid #3b82f6;
        }}
        
        .info-label {{
            font-size: 0.875rem;
            color: #6b7280;
            font-weight: 500;
            margin-bottom: 0.25rem;
        }}
        
        .info-value {{
            font-size: 1.125rem;
            font-weight: 600;
            color: #111827;
        }}
        
        .badge {{
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.875rem;
            font-weight: 600;
            text-transform: uppercase;
        }}
        
        .badge-alto {{
            background: #fef2f2;
            color: #dc2626;
        }}
        
        .badge-medio {{
            background: #fffbeb;
            color: #f59e0b;
        }}
        
        .badge-bajo {{
            background: #f0fdf4;
            color: #16a34a;
        }}
        
        .finding {{
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 0.375rem;
            padding: 1rem;
            margin-bottom: 1rem;
        }}
        
        .finding-header {{
            display: flex;
            justify-content: space-between;
            align-items: start;
            margin-bottom: 0.75rem;
        }}
        
        .finding-title {{
            font-weight: 600;
            color: #111827;
            flex: 1;
        }}
        
        .finding-body {{
            color: #4b5563;
            font-size: 0.95rem;
            line-height: 1.6;
            margin-bottom: 0.75rem;
        }}
        
        .finding-footer {{
            display: flex;
            gap: 1rem;
            font-size: 0.875rem;
            color: #6b7280;
            border-top: 1px solid #f3f4f6;
            padding-top: 0.75rem;
        }}
        
        .recommendation {{
            background: #eff6ff;
            border-left: 4px solid #3b82f6;
            padding: 1rem;
            border-radius: 0.375rem;
            margin-top: 0.5rem;
        }}
        
        .recommendation-label {{
            font-weight: 600;
            color: #1e40af;
            margin-bottom: 0.5rem;
        }}
        
        .summary {{
            background: #f0fdf4;
            border: 1px solid #bbf7d0;
            border-radius: 0.5rem;
            padding: 1.5rem;
            margin-top: 2rem;
        }}
        
        .summary-title {{
            font-size: 1.25rem;
            font-weight: 600;
            color: #166534;
            margin-bottom: 1rem;
        }}
        
        .footer {{
            background: #f9fafb;
            padding: 1.5rem 2rem;
            text-align: center;
            font-size: 0.875rem;
            color: #6b7280;
            border-top: 1px solid #e5e7eb;
        }}
        
        @media print {{
            body {{
                background: white;
                padding: 0;
            }}
            
            .container {{
                box-shadow: none;
            }}
            
            .finding {{
                page-break-inside: avoid;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏥 Reporte de Auditoría Médica</h1>
            <p>Sistema AudiMedIA - Auditoría Concurrente con IA</p>
            <p>Generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}</p>
        </div>
        
        <div class="content">
            <!-- ENCABEZADO -->
            <section class="section">
                <h2 class="section-title">📋 Información del Paciente</h2>
                <div class="info-grid">
                    <div class="info-card">
                        <div class="info-label">Identificador</div>
                        <div class="info-value">{paciente.get('label', 'N/A')}</div>
                    </div>
                    <div class="info-card">
                        <div class="info-label">Diagnóstico Principal</div>
                        <div class="info-value">{paciente.get('diagnostico_principal', 'N/A')}</div>
                    </div>
                    <div class="info-card">
                        <div class="info-label">Código CIE-10</div>
                        <div class="info-value">{paciente.get('codigo_cie10', 'N/A')}</div>
                    </div>
                    <div class="info-card">
                        <div class="info-label">Días Hospitalización</div>
                        <div class="info-value">{paciente.get('dias_hospitalizacion', 'N/A')}</div>
                    </div>
                    <div class="info-card">
                        <div class="info-label">Nivel de Riesgo</div>
                        <div class="info-value">
                            <span class="badge badge-{riesgo}">{riesgo.upper()}</span>
                        </div>
                    </div>
                    <div class="info-card">
                        <div class="info-label">Total Hallazgos</div>
                        <div class="info-value">{audit_data.get('total_hallazgos', 0)}</div>
                    </div>
                    <div class="info-card" style="border-left-color: #dc2626;">
                        <div class="info-label">Exposición a Glosas</div>
                        <div class="info-value" style="color: #dc2626;">{exposicion_fmt}</div>
                    </div>
                </div>
            </section>
            
            <!-- HALLAZGOS POR MÓDULO -->
            <section class="section">
                <h2 class="section-title">🔍 Hallazgos por Módulo de Auditoría</h2>
"""
    
    # Agregar hallazgos por módulo
    if hallazgos_por_modulo:
        for modulo, findings in hallazgos_por_modulo.items():
            html += f"""
                <div style="margin-bottom: 2rem;">
                    <h3 style="color: #1e40af; font-size: 1.25rem; margin-bottom: 1rem;">
                        {modulo.replace('_', ' ').title()}
                    </h3>
"""
            for finding in findings:
                desc = finding.descripcion if hasattr(finding, 'descripcion') else finding.get('descripcion', '')
                rec = finding.recomendacion if hasattr(finding, 'recomendacion') else finding.get('recomendacion', '')
                riesgo_f = finding.riesgo if hasattr(finding, 'riesgo') else finding.get('riesgo', 'bajo')
                valor = finding.valor_glosa_estimado if hasattr(finding, 'valor_glosa_estimado') else finding.get('valor_glosa_estimado', 0)
                normativa = finding.normativa_aplicable if hasattr(finding, 'normativa_aplicable') else finding.get('normativa_aplicable', '')
                
                valor_fmt = f"${valor:,.0f} COP" if valor else "N/A"
                
                html += f"""
                    <div class="finding">
                        <div class="finding-header">
                            <div class="finding-title">{desc}</div>
                            <span class="badge badge-{riesgo_f}">{riesgo_f.upper()}</span>
                        </div>
                        <div class="recommendation">
                            <div class="recommendation-label">💡 Recomendación:</div>
                            <div>{rec}</div>
                        </div>
                        <div class="finding-footer">
                            <div><strong>Valor glosa estimado:</strong> {valor_fmt}</div>
                            {f'<div><strong>Normativa:</strong> {normativa}</div>' if normativa else ''}
                        </div>
                    </div>
"""
            html += """
                </div>
"""
    else:
        html += """
                <p style="color: #6b7280; font-style: italic;">No se encontraron hallazgos para este paciente.</p>
"""
    
    html += """
            </section>
            
            <!-- RECOMENDACIÓN GENERAL -->
            <div class="summary">
                <div class="summary-title">📝 Recomendación General</div>
                <p style="color: #166534; line-height: 1.8;">{}</p>
            </div>
        </div>
        
        <div class="footer">
            <p><strong>AudiMedIA</strong> - Sistema de Auditoría Médica Concurrente con Inteligencia Artificial</p>
            <p style="margin-top: 0.5rem;">
                Este reporte fue generado automáticamente. La información presentada debe ser validada por personal médico calificado.
            </p>
        </div>
    </div>
</body>
</html>
""".format(audit_data.get("recomendacion_general", "Continuar con auditoría de rutina."))
    
    return html
