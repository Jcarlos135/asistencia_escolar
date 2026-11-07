import csv
import datetime
import os
import shutil
import sqlite3
from pathlib import Path
from typing import Dict, Any

import database as db


# SQLite: esperar a que terminen otras operaciones en vez de fallar
_original_get_connection = db.get_connection

def _get_connection_with_timeout():
    conn = sqlite3.connect(db.DB_NAME, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn

db.get_connection = _get_connection_with_timeout


def _db_path():
    return Path(db.DB_NAME).resolve()


def init_extra_db():
    """Crea colegios/turnos y agrega referencias opcionales a cursos sin borrar datos."""
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS colegios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            direccion TEXT DEFAULT '',
            telefono TEXT DEFAULT '',
            activo INTEGER NOT NULL DEFAULT 1,
            creado_en TEXT DEFAULT (datetime('now','localtime')),
            actualizado_en TEXT DEFAULT ''
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS turnos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            hora_inicio TEXT DEFAULT '',
            hora_fin TEXT DEFAULT '',
            activo INTEGER NOT NULL DEFAULT 1,
            actualizado_en TEXT DEFAULT ''
        )
    """)
    cols = [r["name"] for r in cur.execute("PRAGMA table_info(cursos)").fetchall()]
    if "colegio_id" not in cols:
        cur.execute("ALTER TABLE cursos ADD COLUMN colegio_id INTEGER")
    if "turno_id" not in cols:
        cur.execute("ALTER TABLE cursos ADD COLUMN turno_id INTEGER")

    # Migrar actualizado_en a colegios y turnos si no existía
    for tabla in ("colegios", "turnos"):
        cols_t = [r["name"] for r in cur.execute(f"PRAGMA table_info({tabla})").fetchall()]
        if "actualizado_en" not in cols_t:
            cur.execute(f"ALTER TABLE {tabla} ADD COLUMN actualizado_en TEXT DEFAULT ''")

    for nombre in ("Mañana", "Tarde", "Noche"):
        cur.execute("INSERT OR IGNORE INTO turnos(nombre) VALUES (?)", (nombre,))
    cfg = db.obtener_configuracion()
    nombre_colegio = (cfg.get("institucion") or "Colegio Nacional").strip()
    if nombre_colegio:
        cur.execute("INSERT OR IGNORE INTO colegios(nombre) VALUES (?)", (nombre_colegio,))
    conn.commit()
    conn.close()


# --- COLEGIOS ---
def listar_colegios(solo_activos=True):
    conn = db.get_connection()
    sql = "SELECT * FROM colegios" + (" WHERE activo=1" if solo_activos else "") + " ORDER BY nombre"
    rows = conn.execute(sql).fetchall()
    conn.close()
    return rows


def guardar_colegio(nombre, direccion="", telefono="", colegio_id=None):
    nombre = (nombre or "").strip()
    if not nombre:
        raise ValueError("El nombre del colegio es obligatorio.")
    conn = db.get_connection()
    cur = conn.cursor()
    if colegio_id:
        cur.execute("""
            UPDATE colegios SET nombre=?, direccion=?, telefono=?,
                   actualizado_en=datetime('now','localtime')
            WHERE id=?
        """, (nombre, direccion.strip(), telefono.strip(), colegio_id))
        result = colegio_id
    else:
        cur.execute("INSERT INTO colegios(nombre,direccion,telefono,activo) VALUES(?,?,?,1)",
                    (nombre, direccion.strip(), telefono.strip()))
        result = cur.lastrowid
    conn.commit()
    conn.close()
    return result


def desactivar_colegio(colegio_id):
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE colegios SET activo=0,
               actualizado_en=datetime('now','localtime')
        WHERE id=?
    """, (colegio_id,))
    conn.commit()
    conn.close()


def reactivar_colegio(colegio_id):
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE colegios SET activo=1 WHERE id=?", (colegio_id,))
    conn.commit()
    conn.close()


# --- TURNOS ---
def listar_turnos(solo_activos=True):
    conn = db.get_connection()
    sql = "SELECT * FROM turnos" + (" WHERE activo=1" if solo_activos else "") + " ORDER BY id"
    rows = conn.execute(sql).fetchall()
    conn.close()
    return rows


def guardar_turno(nombre, hora_inicio="", hora_fin="", turno_id=None):
    nombre = (nombre or "").strip()
    if not nombre:
        raise ValueError("El nombre del turno es obligatorio.")

    ultimo_error = None
    for intento in range(4):
        conn = None
        try:
            conn = db.get_connection()
            cur = conn.cursor()
            if turno_id:
                cur.execute("""
                    UPDATE turnos SET nombre=?, hora_inicio=?, hora_fin=?,
                           actualizado_en=datetime('now','localtime')
                    WHERE id=?
                """, (nombre, (hora_inicio or "").strip(),
                      (hora_fin or "").strip(), turno_id))
                result = turno_id
            else:
                cur.execute(
                    "INSERT INTO turnos(nombre,hora_inicio,hora_fin,activo) VALUES(?,?,?,1)",
                    (nombre, (hora_inicio or "").strip(), (hora_fin or "").strip())
                )
                result = cur.lastrowid
            conn.commit()
            return result
        except sqlite3.OperationalError as ex:
            ultimo_error = ex
            if "locked" not in str(ex).lower() or intento == 3:
                raise
            import time
            time.sleep(0.5 * (intento + 1))
        finally:
            if conn is not None:
                conn.close()

    raise ultimo_error


def desactivar_turno(turno_id):
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE turnos SET activo=0,
               actualizado_en=datetime('now','localtime')
        WHERE id=?
    """, (turno_id,))
    conn.commit()
    conn.close()


def reactivar_turno(turno_id):
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE turnos SET activo=1 WHERE id=?", (turno_id,))
    conn.commit()
    conn.close()


# --- ASIGNACIÓN ---
def asignar_colegio_turno_curso(curso_id, colegio_id=None, turno_id=None):
    conn = db.get_connection()
    conn.execute("UPDATE cursos SET colegio_id=?, turno_id=? WHERE id=?",
                 (colegio_id, turno_id, curso_id))
    conn.commit()
    conn.close()


def obtener_cursos_extendido():
    conn = db.get_connection()
    rows = conn.execute("""
        SELECT c.*, co.nombre AS colegio_nombre, t.nombre AS turno_nombre
        FROM cursos c
        LEFT JOIN colegios co ON co.id=c.colegio_id
        LEFT JOIN turnos t ON t.id=c.turno_id
        WHERE c.activo = 1
        ORDER BY co.nombre, t.nombre, c.nombre, c.seccion
    """).fetchall()
    conn.close()
    return rows


# --- BACKUPS ---
def crear_backup(ruta_destino):
    destino = Path(ruta_destino).expanduser().resolve()
    destino.parent.mkdir(parents=True, exist_ok=True)
    origen = _db_path()
    if not origen.exists():
        raise FileNotFoundError(f"No existe la base de datos: {origen}")
    if destino == origen:
        raise ValueError("El backup no puede sobrescribir la base de datos activa.")
    src = sqlite3.connect(str(origen))
    dst = sqlite3.connect(str(destino))
    try:
        src.backup(dst)
        resultado = dst.execute("PRAGMA integrity_check").fetchone()[0]
        if resultado != "ok":
            raise RuntimeError(f"El backup no superó la comprobación: {resultado}")
    finally:
        dst.close()
        src.close()
    return str(destino)


def restaurar_backup(ruta_backup):
    origen = Path(ruta_backup).expanduser().resolve()
    destino = _db_path()
    if not origen.exists():
        raise FileNotFoundError("No se encontró el archivo de respaldo.")
    if origen == destino:
        raise ValueError("Selecciona un archivo de backup diferente a la base activa.")

    prueba = sqlite3.connect(str(origen))
    try:
        integridad = prueba.execute("PRAGMA integrity_check").fetchone()[0]
        tablas = {r[0] for r in prueba.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        requeridas = {"cursos", "estudiantes", "asistencias", "configuracion"}
        if integridad != "ok" or not requeridas.issubset(tablas):
            raise ValueError("El archivo no es una copia válida de Asistencia Escolar.")
    finally:
        prueba.close()

    marca = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    preventivo = destino.with_name(f"{destino.stem}_antes_restaurar_{marca}{destino.suffix}")
    if destino.exists():
        shutil.copy2(destino, preventivo)

    src = sqlite3.connect(str(origen))
    dst = sqlite3.connect(str(destino))
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    return str(preventivo) if preventivo.exists() else ""


# --- IMPORTACIÓN CSV ---
def importar_estudiantes_csv(ruta_csv, curso_id, encoding="utf-8-sig"):
    if not os.path.isfile(ruta_csv):
        raise FileNotFoundError("No se encontró el archivo CSV.")
    aliases = {
        "nombre_completo": ("nombre_completo", "nombre", "estudiante", "alumno"),
        "ci": ("ci", "ci_estudiante", "carnet", "carnet_estudiante"),
        "tutor_nombre": ("tutor_nombre", "tutor", "padre_tutor", "apoderado"),
        "tutor_ci": ("tutor_ci", "ci_tutor", "carnet_tutor"),
        "tutor_telefono": ("tutor_telefono", "telefono", "celular", "whatsapp", "telefono_tutor"),
    }
    conn = db.get_connection()
    existentes = conn.execute(
        "SELECT nombre_completo, COALESCE(ci,'') ci FROM estudiantes WHERE curso_id=? AND activo=1",
        (curso_id,)).fetchall()
    cis = {str(r["ci"]).strip() for r in existentes if str(r["ci"]).strip()}
    nombres = {str(r["nombre_completo"]).strip().casefold() for r in existentes}
    insertados, duplicados, errores = 0, 0, []
    try:
        with open(ruta_csv, "r", encoding=encoding, newline="") as f:
            muestra = f.read(4096)
            f.seek(0)
            try:
                dialecto = csv.Sniffer().sniff(muestra, delimiters=",;\t")
            except csv.Error:
                dialecto = csv.excel
            lector = csv.DictReader(f, dialect=dialecto)
            if not lector.fieldnames:
                raise ValueError("El CSV no contiene encabezados.")
            mapa = {h.strip().lower(): h for h in lector.fieldnames if h}
            columnas = {}
            for destino, opciones in aliases.items():
                columnas[destino] = next((mapa[o] for o in opciones if o in mapa), None)
            if not columnas["nombre_completo"] or not columnas["tutor_nombre"] or not columnas["tutor_telefono"]:
                raise ValueError("Faltan columnas obligatorias: nombre_completo, tutor_nombre y tutor_telefono.")

            for numero, fila in enumerate(lector, start=2):
                dato = {k: (fila.get(col) or "").strip() if col else ""
                        for k, col in columnas.items()}
                nombre = dato["nombre_completo"]
                tutor = dato["tutor_nombre"]
                telefono = dato["tutor_telefono"]
                if not nombre or not tutor or not telefono:
                    errores.append(f"Fila {numero}: faltan nombre, tutor o teléfono.")
                    continue
                ci = dato["ci"]
                clave_nombre = nombre.casefold()
                if (ci and ci in cis) or clave_nombre in nombres:
                    duplicados += 1
                    continue
                conn.execute("""
                    INSERT INTO estudiantes
                    (curso_id,nombre_completo,ci,tutor_nombre,tutor_ci,tutor_telefono,activo)
                    VALUES (?,?,?,?,?,?,1)
                """, (int(curso_id), nombre, ci, tutor, dato["tutor_ci"], telefono))
                insertados += 1
                if ci:
                    cis.add(ci)
                nombres.add(clave_nombre)
        conn.commit()
    finally:
        conn.close()
    return {"insertados": insertados, "duplicados": duplicados, "errores": errores}
""" OBTENER TODOS LOS CURSOS """
def obtener_todos_cursos_con_detalle():
    """Devuelve todos los cursos activos con el detalle de su colegio y turno."""
    conn = db.get_connection()
    rows = conn.execute("""
        SELECT c.*, co.nombre AS colegio_nombre, t.nombre AS turno_nombre
        FROM cursos c
        LEFT JOIN colegios co ON co.id=c.colegio_id
        LEFT JOIN turnos t ON t.id=c.turno_id
        WHERE c.activo = 1
        ORDER BY c.nombre, c.seccion
    """).fetchall()
    conn.close()
    return rows