import csv
import os
import datetime
from typing import List, Dict, Any
from database import get_connection


def obtener_resumen_dia(curso_id: int, fecha: str) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN a.estado = 'PRESENTE' THEN 1 ELSE 0 END) as presentes,
            SUM(CASE WHEN a.estado = 'AUSENTE' THEN 1 ELSE 0 END) as ausentes,
            SUM(CASE WHEN a.estado = 'PERMISO' THEN 1 ELSE 0 END) as permisos,
            SUM(CASE WHEN a.estado = 'ATRASO' THEN 1 ELSE 0 END) as atrasos
        FROM asistencias a
        JOIN estudiantes e ON a.estudiante_id = e.id
        WHERE e.curso_id = ? AND a.fecha = ?
    """, (curso_id, fecha))
    row = cursor.fetchone()
    conn.close()

    total = row["total"] or 0
    presentes = row["presentes"] or 0
    ausentes = row["ausentes"] or 0
    permisos = row["permisos"] or 0
    atrasos = row["atrasos"] or 0
    porcentaje = round(((presentes + atrasos) / total * 100), 1) if total > 0 else 0.0

    return {
        "total": total, "presentes": presentes, "ausentes": ausentes,
        "permisos": permisos, "atrasos": atrasos,
        "porcentaje_asistencia": porcentaje
    }


def obtener_resumen_mensual(curso_id: int, anio_mes: str, texto: str = "") -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    where = "WHERE e.curso_id = ?"
    params: List = [f"{anio_mes}%", curso_id]
    if texto.strip():
        like = f"%{texto.strip().lower()}%"
        where += " AND (LOWER(e.nombre_completo) LIKE ? OR LOWER(COALESCE(e.ci,'')) LIKE ? OR LOWER(e.tutor_nombre) LIKE ? OR LOWER(COALESCE(e.tutor_ci,'')) LIKE ?)"
        params.extend([like, like, like, like])

    cursor.execute(f"""
        SELECT 
            e.id,
            e.nombre_completo,
            COALESCE(e.ci,'') as ci,
            e.tutor_nombre,
            COALESCE(e.tutor_ci,'') as tutor_ci,
            e.tutor_telefono,
            COUNT(a.id) as total_dias,
            SUM(CASE WHEN a.estado = 'PRESENTE' THEN 1 ELSE 0 END) as total_presente,
            SUM(CASE WHEN a.estado = 'AUSENTE' THEN 1 ELSE 0 END) as total_ausente,
            SUM(CASE WHEN a.estado = 'PERMISO' THEN 1 ELSE 0 END) as total_permiso,
            SUM(CASE WHEN a.estado = 'ATRASO' THEN 1 ELSE 0 END) as total_atraso
        FROM estudiantes e
        LEFT JOIN asistencias a ON e.id = a.estudiante_id AND a.fecha LIKE ?
        {where}
        GROUP BY e.id
        ORDER BY e.nombre_completo
    """, params)

    resultados = []
    for r in cursor.fetchall():
        dias = r["total_dias"] or 0
        pres = r["total_presente"] or 0
        aus = r["total_ausente"] or 0
        per = r["total_permiso"] or 0
        atr = r["total_atraso"] or 0
        porc = round(((pres + atr) / dias * 100), 1) if dias > 0 else 100.0
        alerta = aus >= 3 or porc < 80.0

        resultados.append({
            "id": r["id"],
            "nombre": r["nombre_completo"],
            "ci": r["ci"],
            "tutor": r["tutor_nombre"],
            "tutor_ci": r["tutor_ci"],
            "telefono": r["tutor_telefono"],
            "dias": dias, "presentes": pres, "ausentes": aus,
            "permisos": per, "atrasos": atr,
            "porcentaje": porc, "en_riesgo": alerta
        })
    conn.close()
    return resultados


def exportar_reporte_csv(
    curso_nombre: str,
    anio_mes: str,
    datos: List[Dict[str, Any]],
    ruta_destino: str = "",
    institucion: str = "Colegio Nacional",
    docente: str = "Profesor(a)",
    materia: str = "Clase General",
    nivel: str = "Secundaria",
    docente_ci: str = "",
) -> str:
    if not ruta_destino:
        nombre_archivo = f"Reporte_Asistencia_{curso_nombre.replace(' ', '_')}_{anio_mes}.csv"
        ruta_destino = os.path.abspath(nombre_archivo)

    total_alumnos = len(datos)
    total_presentes = sum(d["presentes"] for d in datos)
    total_ausentes = sum(d["ausentes"] for d in datos)
    total_permisos = sum(d["permisos"] for d in datos)
    total_atrasos = sum(d["atrasos"] for d in datos)
    total_dias_reg = sum(d["dias"] for d in datos)
    alumnos_riesgo = sum(1 for d in datos if d["en_riesgo"])

    if total_dias_reg > 0:
        promedio_general = round(((total_presentes + total_atrasos) / total_dias_reg * 100), 1)
    else:
        promedio_general = 0.0

    fecha_generacion = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(ruta_destino, mode="w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=",", quoting=csv.QUOTE_MINIMAL)

        # ===== ENCABEZADO INSTITUCIONAL =====
        writer.writerow(["═" * 110])
        writer.writerow([f"REPORTE DE ASISTENCIA ESCOLAR - NIVEL {nivel.upper()}"])
        writer.writerow(["═" * 110])
        writer.writerow([])
        writer.writerow(["Institución Educativa:", institucion])
        writer.writerow(["Docente Responsable:", docente])
        if docente_ci:
            writer.writerow(["CI del Docente:", docente_ci])
        writer.writerow(["Materia / Área:", materia])
        writer.writerow(["Curso / Grado:", curso_nombre])
        writer.writerow(["Periodo Reportado:", anio_mes])
        writer.writerow(["Fecha de Generación:", fecha_generacion])
        writer.writerow(["País:", "Bolivia (+591)"])
        writer.writerow([])
        writer.writerow(["═" * 110])
        writer.writerow(["RESUMEN GENERAL DEL CURSO"])
        writer.writerow(["═" * 110])
        writer.writerow([])
        writer.writerow(["Total de Estudiantes:", total_alumnos])
        writer.writerow(["Total de Registros de Asistencia:", total_dias_reg])
        writer.writerow(["Total Presentes:", total_presentes])
        writer.writerow(["Total Ausentes:", total_ausentes])
        writer.writerow(["Total Permisos:", total_permisos])
        writer.writerow(["Total Atrasos:", total_atrasos])
        writer.writerow(["Promedio General de Asistencia:", f"{promedio_general}%"])
        writer.writerow(["Alumnos en Riesgo (≥3 faltas o <80%):", alumnos_riesgo])
        writer.writerow([])
        writer.writerow(["═" * 110])
        writer.writerow(["DETALLE POR ESTUDIANTE"])
        writer.writerow(["═" * 110])
        writer.writerow([])

        # ===== CABECERA DE TABLA (con CI estudiante y CI tutor) =====
        writer.writerow([
            "N°",
            "CI Estudiante",
            "Estudiante",
            "Tutor / Apoderado",
            "CI Tutor",
            "Teléfono (Bolivia)",
            "Días Reg.",
            "Presentes",
            "Ausentes",
            "Permisos",
            "Atrasos",
            "% Asistencia",
            "Estado",
            "Observación"
        ])

        for idx, d in enumerate(datos, start=1):
            if d["en_riesgo"]:
                estado = "EN RIESGO"
                obs = "Requiere seguimiento del docente"
            else:
                estado = "REGULAR"
                obs = ""

            writer.writerow([
                idx,
                d.get("ci", ""),
                d["nombre"],
                d["tutor"],
                d.get("tutor_ci", ""),
                d["telefono"],
                d["dias"], d["presentes"], d["ausentes"],
                d["permisos"], d["atrasos"],
                f"{d['porcentaje']}%", estado, obs
            ])

        writer.writerow([])
        writer.writerow(["═" * 110])
        writer.writerow(["LEYENDA DE ESTADOS:"])
        writer.writerow(["  PRESENTE = Alumno asistió a clases"])
        writer.writerow(["  AUSENTE  = Falta sin justificación"])
        writer.writerow(["  PERMISO  = Falta justificada (documento o aviso previo)"])
        writer.writerow(["  ATRASO   = Llegada tarde (cuenta como asistencia parcial)"])
        writer.writerow(["  EN RIESGO = ≥3 faltas o asistencia <80% en el periodo"])
        writer.writerow([])
        writer.writerow(["═" * 110])
        writer.writerow(["Documento generado automáticamente por Sistema de Asistencia Escolar - Bolivia"])
        writer.writerow([f"Última actualización: {fecha_generacion}"])
        writer.writerow(["═" * 110])

    return ruta_destino