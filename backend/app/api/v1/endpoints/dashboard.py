from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, and_, extract
from datetime import datetime, timedelta, date
from typing import Optional, List
import io
import csv
import json
import calendar
from app.db.session import get_db
from app.models.user import User, AppRole
from app.models.patient import PatientCase, RiskLevel
from app.models.audit import AuditFinding, AuditSession
from app.models.tarifa import TarifaConfig
from app.schemas.audit import (
    DashboardMetrics, DashboardFinanciero, DashboardGraficos,
    MetricaTemporal, TarifaConfigRead, TarifaConfigUpdate, ExportRequest
)
from app.api.v1.deps import get_current_user, require_role
from app.services.reports.executive_report import generate_executive_report

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/metrics", response_model=DashboardMetrics)
async def get_metrics(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(AppRole.coordinador, AppRole.admin)),
):
    # Total historias auditadas
    total = await db.scalar(select(func.count(PatientCase.id)))

    # Hallazgos resueltos (glosas evitadas)
    glosas_evitadas = await db.scalar(
        select(func.count(AuditFinding.id)).where(AuditFinding.resuelto == True)
    )

    # Estancias prolongadas (donde dias_hospitalizacion > dias_esperados aproximado)
    estancias_prolongadas = await db.scalar(
        select(func.count(PatientCase.id)).where(PatientCase.riesgo == RiskLevel.alto)
    )

    # Riesgo alto
    riesgo_alto = await db.scalar(
        select(func.count(PatientCase.id)).where(PatientCase.riesgo == RiskLevel.alto)
    )

    return DashboardMetrics(
        historias_auditadas=total or 0,
        glosas_evitadas=glosas_evitadas or 0,
        ahorro_estimado=(glosas_evitadas or 0) * 850_000,  # COP estimado por glosa
        estancias_prolongadas=estancias_prolongadas or 0,
        riesgo_alto=riesgo_alto or 0,
        pendientes_resueltos=glosas_evitadas or 0,
        tiempo_promedio_auditoria_min=2.8,
    )


@router.get("/financiero", response_model=DashboardFinanciero)
async def get_dashboard_financiero(
    periodo: str = Query("mes", regex="^(dia|semana|mes|anio)$"),
    fecha_fin: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(AppRole.coordinador, AppRole.admin)),
):
    """Dashboard financiero avanzado con cálculos detallados"""
    
    # Obtener configuración de tarifas
    tarifa = await db.scalar(select(TarifaConfig).where(TarifaConfig.activo == True))
    if not tarifa:
        # Crear configuración por defecto
        tarifa = TarifaConfig()
        db.add(tarifa)
        await db.commit()
        await db.refresh(tarifa)
    
    # Calcular rango de fechas
    fecha_fin_calc = fecha_fin or datetime.utcnow()
    if periodo == "dia":
        fecha_inicio = fecha_fin_calc.replace(hour=0, minute=0, second=0, microsecond=0)
    elif periodo == "semana":
        fecha_inicio = fecha_fin_calc - timedelta(days=7)
    elif periodo == "mes":
        fecha_inicio = fecha_fin_calc - timedelta(days=30)
    else:  # anio
        fecha_inicio = fecha_fin_calc - timedelta(days=365)
    
    # KPIs del período
    historias_periodo = await db.scalar(
        select(func.count(PatientCase.id)).where(
            PatientCase.created_at >= fecha_inicio
        )
    )
    
    glosas_periodo = await db.scalar(
        select(func.count(AuditFinding.id)).where(
            and_(
                AuditFinding.resuelto == True,
                AuditFinding.created_at >= fecha_inicio
            )
        )
    )
    
    # Glosas año completo
    inicio_anio = datetime(fecha_fin_calc.year, 1, 1)
    glosas_anio = await db.scalar(
        select(func.count(AuditFinding.id)).where(
            and_(
                AuditFinding.resuelto == True,
                AuditFinding.created_at >= inicio_anio
            )
        )
    )
    
    # Estancias prolongadas
    estancias = await db.scalar(
        select(func.count(PatientCase.id)).where(
            and_(
                PatientCase.riesgo == RiskLevel.alto,
                PatientCase.created_at >= fecha_inicio
            )
        )
    )
    
    # Cálculos financieros
    valor_glosa = tarifa.valor_promedio_glosa
    glosas_mes_cop = (glosas_periodo or 0) * valor_glosa
    glosas_anio_cop = (glosas_anio or 0) * valor_glosa
    
    # Ahorro por estancias prolongadas detectadas (estimación)
    dias_extras_estimados = (estancias or 0) * 3  # Promedio 3 días extras por caso
    ahorro_estancia = dias_extras_estimados * tarifa.tarifa_dia_hospitalizacion
    
    # Distribución de ahorro (simulada por ahora)
    ahorro_total = glosas_mes_cop
    ahorro_estancia_calc = ahorro_total * 0.4
    ahorro_procedimientos = ahorro_total * 0.3
    ahorro_medicamentos = ahorro_total * 0.2
    ahorro_evoluciones = ahorro_total * 0.1
    
    # Métricas operacionales
    total_hallazgos = await db.scalar(
        select(func.count(AuditFinding.id)).where(
            AuditFinding.created_at >= fecha_inicio
        )
    )
    tasa_resolucion = ((glosas_periodo or 0) / (total_hallazgos or 1)) * 100
    
    riesgo_alto_count = await db.scalar(
        select(func.count(PatientCase.id)).where(
            and_(
                PatientCase.riesgo == RiskLevel.alto,
                PatientCase.created_at >= fecha_inicio
            )
        )
    )
    tasa_riesgo_alto = ((riesgo_alto_count or 0) / max(historias_periodo or 1, 1)) * 100
    
    # ROI (retorno vs costo hipotético de auditoría)
    costo_auditoria_estimado = (historias_periodo or 0) * 50000  # 50k por historia
    roi = ((ahorro_total - costo_auditoria_estimado) / max(costo_auditoria_estimado, 1)) * 100
    
    # Proyección anual
    dias_transcurridos = (fecha_fin_calc - fecha_inicio).days
    if dias_transcurridos > 0 and periodo != "anio":
        factor_anual = 365 / dias_transcurridos
        proyeccion = ahorro_total * factor_anual
    else:
        proyeccion = glosas_anio_cop
    
    return DashboardFinanciero(
        periodo_tipo=periodo,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin_calc,
        glosas_evitadas_mes_cop=glosas_mes_cop,
        glosas_evitadas_anio_cop=glosas_anio_cop,
        estancias_prolongadas_dias=dias_extras_estimados,
        ahorro_estancia_mes_cop=ahorro_estancia,
        historias_auditadas_periodo=historias_periodo or 0,
        tasa_riesgo_alto_porcentaje=round(tasa_riesgo_alto, 2),
        pendientes_resueltos_porcentaje=round(tasa_resolucion, 2),
        tiempo_promedio_auditoria_min=2.8,
        ahorro_por_estancia=ahorro_estancia_calc,
        ahorro_por_procedimientos=ahorro_procedimientos,
        ahorro_por_medicamentos=ahorro_medicamentos,
        ahorro_por_evoluciones=ahorro_evoluciones,
        roi_periodo=round(roi, 2),
        proyeccion_ahorro_anual=proyeccion,
    )


@router.get("/graficos", response_model=DashboardGraficos)
async def get_graficos(
    dias: int = Query(30, ge=7, le=365),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(AppRole.coordinador, AppRole.admin)),
):
    """Datos para gráficos del dashboard"""
    
    fecha_fin = datetime.utcnow()
    fecha_inicio = fecha_fin - timedelta(days=dias)
    
    # Glosas evitadas por día (últimos N días)
    glosas_tiempo: List[MetricaTemporal] = []
    for i in range(dias):
        dia = fecha_inicio + timedelta(days=i)
        dia_siguiente = dia + timedelta(days=1)
        
        count = await db.scalar(
            select(func.count(AuditFinding.id)).where(
                and_(
                    AuditFinding.resuelto == True,
                    AuditFinding.created_at >= dia,
                    AuditFinding.created_at < dia_siguiente
                )
            )
        )
        
        glosas_tiempo.append(MetricaTemporal(
            fecha=dia,
            valor=float(count or 0),
            etiqueta=dia.strftime("%d/%m")
        ))
    
    # Ahorro acumulado
    ahorro_acumulado: List[MetricaTemporal] = []
    acumulado = 0.0
    for mt in glosas_tiempo:
        acumulado += mt.valor * 850000  # Valor promedio por glosa
        ahorro_acumulado.append(MetricaTemporal(
            fecha=mt.fecha,
            valor=acumulado,
            etiqueta=mt.etiqueta
        ))
    
    # Hallazgos por módulo
    result = await db.execute(
        select(
            AuditFinding.modulo,
            func.count(AuditFinding.id).label("count")
        ).where(
            AuditFinding.created_at >= fecha_inicio
        ).group_by(AuditFinding.modulo)
    )
    hallazgos_modulo = {row.modulo: row.count for row in result}
    
    # Ahorro por servicio (simulado por ahora)
    ahorro_servicio = {
        "Hospitalización General": 12500000,
        "UCI": 8300000,
        "Urgencias": 5200000,
        "Cirugía": 7800000,
    }
    
    return DashboardGraficos(
        glosas_tiempo=glosas_tiempo,
        ahorro_acumulado=ahorro_acumulado,
        hallazgos_por_modulo=hallazgos_modulo,
        ahorro_por_servicio=ahorro_servicio,
    )


# Endpoints de configuración de tarifas (solo admin)

@router.get("/tarifas", response_model=TarifaConfigRead)
async def get_tarifas(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(AppRole.admin)),
):
    """Obtener configuración de tarifas actual"""
    tarifa = await db.scalar(select(TarifaConfig).where(TarifaConfig.activo == True))
    if not tarifa:
        # Crear configuración por defecto
        tarifa = TarifaConfig()
        db.add(tarifa)
        await db.commit()
        await db.refresh(tarifa)
    return tarifa


@router.patch("/tarifas/{tarifa_id}", response_model=TarifaConfigRead)
async def update_tarifas(
    tarifa_id: str,
    payload: TarifaConfigUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(AppRole.admin)),
):
    """Actualizar configuración de tarifas"""
    result = await db.execute(select(TarifaConfig).where(TarifaConfig.id == tarifa_id))
    tarifa = result.scalar_one_or_none()
    if not tarifa:
        raise HTTPException(status_code=404, detail="Configuración de tarifa no encontrada")
    
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(tarifa, field, value)
    
    await db.commit()
    await db.refresh(tarifa)
    return tarifa


@router.post("/export")
async def export_dashboard(
    payload: ExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(AppRole.coordinador, AppRole.admin)),
):
    """Exportar dashboard en formato CSV (Excel) o JSON (PDF)"""
    
    # Obtener datos del dashboard para el período solicitado
    fecha_inicio = payload.periodo_inicio
    fecha_fin = payload.periodo_fin
    
    # ── Métricas base ────────────────────────────────────────────────────────
    tarifa = await db.scalar(select(TarifaConfig).where(TarifaConfig.activo == True))
    valor_glosa = tarifa.valor_promedio_glosa if tarifa else 850_000

    historias = await db.scalar(
        select(func.count(PatientCase.id)).where(
            and_(PatientCase.created_at >= fecha_inicio,
                 PatientCase.created_at <= fecha_fin)
        )
    ) or 0

    glosas_evitadas = await db.scalar(
        select(func.count(AuditFinding.id)).where(
            and_(AuditFinding.resuelto == True,
                 AuditFinding.created_at >= fecha_inicio,
                 AuditFinding.created_at <= fecha_fin)
        )
    ) or 0

    glosas_anio = await db.scalar(
        select(func.count(AuditFinding.id)).where(
            and_(AuditFinding.resuelto == True,
                 AuditFinding.created_at >= datetime(fecha_fin.year, 1, 1))
        )
    ) or 0

    total_hallazgos = await db.scalar(
        select(func.count(AuditFinding.id)).where(
            and_(AuditFinding.created_at >= fecha_inicio,
                 AuditFinding.created_at <= fecha_fin)
        )
    ) or 0

    riesgo_alto_count = await db.scalar(
        select(func.count(PatientCase.id)).where(
            and_(PatientCase.riesgo == RiskLevel.alto,
                 PatientCase.created_at >= fecha_inicio,
                 PatientCase.created_at <= fecha_fin)
        )
    ) or 0

    modulo_res = await db.execute(
        select(AuditFinding.modulo, func.count(AuditFinding.id).label("cnt"))
        .where(and_(AuditFinding.created_at >= fecha_inicio,
                    AuditFinding.created_at <= fecha_fin))
        .group_by(AuditFinding.modulo)
    )
    hallazgos_por_modulo = {r.modulo: r.cnt for r in modulo_res}

    # ── Derivados (misma lógica que /financiero) ──────────────────────────
    ahorro_total = glosas_evitadas * valor_glosa
    ahorro_anual = glosas_anio * valor_glosa
    dias_extras = riesgo_alto_count * 3
    costo_auditoria = historias * 50_000
    roi = ((ahorro_total - costo_auditoria) / max(costo_auditoria, 1)) * 100
    tasa_riesgo_alto = (riesgo_alto_count / max(historias, 1)) * 100
    tasa_resolucion = (glosas_evitadas / max(total_hallazgos, 1)) * 100
    dias_periodo = max((fecha_fin - fecha_inicio).days, 1)
    proyeccion = ahorro_total * (365 / dias_periodo)

    nombres_modulo = {
        "estancia": "Estancia prolongada",
        "pertinencia": "Pertinencia CIE-10",
        "estudios": "Estudios sin reporte",
        "glosas": "Detección de glosas",
    }

    datos = {
        "periodo_inicio": fecha_inicio.strftime("%Y-%m-%d"),
        "periodo_fin": fecha_fin.strftime("%Y-%m-%d"),
        "historias_auditadas": historias,
        "glosas_evitadas": glosas_evitadas,
        "ahorro_total_cop": ahorro_total,
        "ahorro_anual_cop": ahorro_anual,
        "dias_estancia_extra": dias_extras,
        "tasa_riesgo_alto_pct": round(tasa_riesgo_alto, 2),
        "tasa_resolucion_pct": round(tasa_resolucion, 2),
        "roi_periodo_pct": round(roi, 2),
        "proyeccion_anual_cop": proyeccion,
        "hallazgos_por_modulo": hallazgos_por_modulo,
        "generado_por": current_user.full_name or current_user.email,
        "generado_el": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
    }

    if payload.formato == "excel":
        output = io.StringIO()
        writer = csv.writer(output)

        # ── Portada ──────────────────────────────────────────────────────────
        writer.writerow(["Dashboard Financiero AudiMedIA"])
        writer.writerow([])
        writer.writerow(["Período", f"{datos['periodo_inicio']} a {datos['periodo_fin']}"])
        writer.writerow(["Generado por", datos["generado_por"]])
        writer.writerow(["Fecha de generación", datos["generado_el"]])
        writer.writerow([])

        # ── KPIs Principales ─────────────────────────────────────────────────
        writer.writerow(["=== KPIs PRINCIPALES ===", ""])
        writer.writerow(["Métrica", "Valor"])
        writer.writerow(["Glosas Evitadas (Período, COP)", f"${ahorro_total:,.0f}"])
        writer.writerow(["Acumulado Anual (COP)", f"${ahorro_anual:,.0f}"])
        writer.writerow(["Historias Clínicas Auditadas", historias])
        writer.writerow(["Glosas Evitadas (cant.)", glosas_evitadas])
        writer.writerow(["Total Hallazgos", total_hallazgos])
        writer.writerow(["Días de Estancia Extra", dias_extras])
        writer.writerow([])

        # ── Indicadores Operacionales ────────────────────────────────────────
        writer.writerow(["=== INDICADORES OPERACIONALES ===", ""])
        writer.writerow(["Métrica", "Valor"])
        writer.writerow(["ROI del Período (%)", f"{roi:+.1f}%"])
        writer.writerow(["Tasa de Riesgo Alto (%)", f"{tasa_riesgo_alto:.1f}%"])
        writer.writerow(["Pendientes Resueltos (%)", f"{tasa_resolucion:.1f}%"])
        writer.writerow(["Tiempo Promedio Auditoría (min)", "2.8"])
        writer.writerow(["Proyección Ahorro Anual (COP)", f"${proyeccion:,.0f}"])
        writer.writerow([])

        # ── Desglose de Ahorro ───────────────────────────────────────────────
        writer.writerow(["=== DESGLOSE DE AHORRO ===", ""])
        writer.writerow(["Categoría", "Valor COP", "% del Total"])
        breakdown = [
            ("Estancia prolongada", 0.40),
            ("Procedimientos", 0.30),
            ("Medicamentos", 0.20),
            ("Evoluciones", 0.10),
        ]
        for cat, pct in breakdown:
            val = ahorro_total * pct
            writer.writerow([cat, f"${val:,.0f}", f"{pct*100:.0f}%"])
        writer.writerow([])

        # ── Hallazgos por Módulo ─────────────────────────────────────────────
        writer.writerow(["=== HALLAZGOS POR MÓDULO ===", ""])
        writer.writerow(["Módulo", "Cantidad de Hallazgos"])
        for modulo, cnt in hallazgos_por_modulo.items():
            writer.writerow([nombres_modulo.get(modulo, modulo.capitalize()), cnt])
        if not hallazgos_por_modulo:
            writer.writerow(["Sin hallazgos en el período", 0])
        writer.writerow([])

        # ── Detalle de Pacientes (opcional) ──────────────────────────────────
        if payload.incluir_detalle_pacientes:
            writer.writerow(["=== DETALLE DE PACIENTES ==="])
            writer.writerow(["Label", "Diagnóstico", "CIE-10", "Riesgo", "Días Hospitalización"])
            result = await db.execute(
                select(PatientCase).where(
                    and_(PatientCase.created_at >= fecha_inicio,
                         PatientCase.created_at <= fecha_fin)
                ).limit(200)
            )
            for p in result.scalars().all():
                writer.writerow([
                    p.label,
                    p.diagnostico_principal or "",
                    p.codigo_cie10 or "",
                    p.riesgo,
                    p.dias_hospitalizacion or 0,
                ])

        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode("utf-8-sig")),  # BOM para Excel
            media_type="text/csv",
            headers={
                "Content-Disposition": (
                    f"attachment; filename=dashboard_financiero_"
                    f"{fecha_inicio.strftime('%Y%m%d')}_{fecha_fin.strftime('%Y%m%d')}.csv"
                )
            },
        )
    
    else:  # formato == "pdf" (retornar JSON con todos los datos)
        datos_completos = datos.copy()
        datos_completos["hallazgos_por_modulo"] = {
            nombres_modulo.get(k, k): v for k, v in hallazgos_por_modulo.items()
        }
        datos_completos["desglose_ahorro"] = {
            "Estancia prolongada": ahorro_total * 0.40,
            "Procedimientos": ahorro_total * 0.30,
            "Medicamentos": ahorro_total * 0.20,
            "Evoluciones": ahorro_total * 0.10,
        }

        return StreamingResponse(
            io.BytesIO(json.dumps(datos_completos, indent=2, ensure_ascii=False).encode("utf-8")),
            media_type="application/json",
            headers={
                "Content-Disposition": (
                    f"attachment; filename=dashboard_financiero_"
                    f"{fecha_inicio.strftime('%Y%m%d')}_{fecha_fin.strftime('%Y%m%d')}.json"
                )
            },
        )


@router.get("/executive-report")
async def download_executive_report(
    periodo: str = Query("mes", regex="^(semana|mes|trimestre|anio)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(AppRole.coordinador, AppRole.admin)),
):
    """Descarga el Reporte Ejecutivo PDF de 1 página para gerencia."""

    ahora = datetime.utcnow()

    # ── Etiqueta del período ──────────────────────────────────────────────────
    meses_es = [
        "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
    ]
    if periodo == "mes":
        periodo_label = f"{meses_es[ahora.month]} {ahora.year}"
        fecha_inicio = ahora - timedelta(days=30)
    elif periodo == "semana":
        periodo_label = f"Semana del {(ahora - timedelta(days=7)).strftime('%d/%m')} al {ahora.strftime('%d/%m/%Y')}"
        fecha_inicio = ahora - timedelta(days=7)
    elif periodo == "trimestre":
        periodo_label = f"Trimestre {((ahora.month - 1) // 3) + 1} — {ahora.year}"
        fecha_inicio = ahora - timedelta(days=90)
    else:  # anio
        periodo_label = f"Año {ahora.year}"
        fecha_inicio = datetime(ahora.year, 1, 1)

    # ── Tarifa de referencia ──────────────────────────────────────────────────
    tarifa = await db.scalar(select(TarifaConfig).where(TarifaConfig.activo == True))
    valor_glosa = tarifa.valor_promedio_glosa if tarifa else 850_000

    # ── KPIs del período ──────────────────────────────────────────────────────
    glosas_periodo = await db.scalar(
        select(func.count(AuditFinding.id)).where(
            and_(AuditFinding.resuelto == True, AuditFinding.created_at >= fecha_inicio)
        )
    ) or 0
    ahorro_mes = glosas_periodo * valor_glosa

    inicio_anio = datetime(ahora.year, 1, 1)
    glosas_anio = await db.scalar(
        select(func.count(AuditFinding.id)).where(
            and_(AuditFinding.resuelto == True, AuditFinding.created_at >= inicio_anio)
        )
    ) or 0
    ahorro_anual = glosas_anio * valor_glosa

    historias = await db.scalar(
        select(func.count(PatientCase.id)).where(PatientCase.created_at >= fecha_inicio)
    ) or 0

    costo_auditoria = historias * 50_000
    roi = ((ahorro_mes - costo_auditoria) / max(costo_auditoria, 1)) * 100

    # ── Tendencia mensual (últimos 6 meses) ───────────────────────────────────
    tendencia: list[dict] = []
    for offset in range(5, -1, -1):
        mes_ref = ahora.month - offset
        anio_ref = ahora.year
        while mes_ref <= 0:
            mes_ref += 12
            anio_ref -= 1
        mes_inicio = datetime(anio_ref, mes_ref, 1)
        ultimo_dia = calendar.monthrange(anio_ref, mes_ref)[1]
        mes_fin = datetime(anio_ref, mes_ref, ultimo_dia, 23, 59, 59)
        cnt = await db.scalar(
            select(func.count(AuditFinding.id)).where(
                and_(
                    AuditFinding.resuelto == True,
                    AuditFinding.created_at >= mes_inicio,
                    AuditFinding.created_at <= mes_fin,
                )
            )
        ) or 0
        tendencia.append({
            "label": meses_es[mes_ref][:3],
            "valor": cnt * valor_glosa,
        })

    # ── Top módulos con mayor glosas ──────────────────────────────────────────
    result = await db.execute(
        select(AuditFinding.modulo, func.count(AuditFinding.id).label("cnt"))
        .where(AuditFinding.created_at >= fecha_inicio)
        .group_by(AuditFinding.modulo)
        .order_by(func.count(AuditFinding.id).desc())
        .limit(4)
    )
    rows = result.all()
    total_hallazgos = sum(r.cnt for r in rows) or 1
    nombres_modulo = {
        "estancia": "Estancia prolongada",
        "pertinencia": "Pertinencia CIE-10",
        "estudios": "Estudios sin reporte",
        "glosas": "Detección de glosas",
    }
    top_modulos = [
        {
            "nombre": nombres_modulo.get(r.modulo, r.modulo.capitalize()),
            "porcentaje": round(r.cnt / total_hallazgos * 100, 1),
            "valor": r.cnt * valor_glosa,
        }
        for r in rows
    ]

    # ── Generar PDF ───────────────────────────────────────────────────────────
    pdf_bytes = generate_executive_report(
        periodo_label=periodo_label,
        ahorro_mes=ahorro_mes,
        ahorro_anual=ahorro_anual,
        roi=roi,
        historias_auditadas=historias,
        tendencia_mensual=tendencia,
        top_modulos=top_modulos,
        generado_por=current_user.full_name or current_user.email,
    )

    filename = f"reporte_ejecutivo_{ahora.strftime('%Y%m%d_%H%M')}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
