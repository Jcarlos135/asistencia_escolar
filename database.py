import sqlite3
import datetime
from typing import List, Dict, Optional, Tuple

DB_NAME = "asistencia_escolar.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def _columnas_tabla(cursor, tabla: str) -> List[str]:
    cursor.execute(f"PRAGMA table_info({tabla})")
    return [row["name"] for row in cursor.fetchall()]

def _agregar_columna_si_no_existe(cursor, tabla: str, columna: str, tipo: str, default: str = "''"):
    cols = _columnas_tabla(cursor, tabla)
    if columna not in cols:
        cursor.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} {tipo} DEFAULT {default}")

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Tabla Cursos / Grados
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cursos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        nivel TEXT,
        seccion TEXT,
        activo INTEGER DEFAULT 1,
        actualizado_en TEXT DEFAULT ''
    )
    """)

    # Tabla Estudiantes (con CI)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS estudiantes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        curso_id INTEGER NOT NULL,
        nombre_completo TEXT NOT NULL,
        ci TEXT DEFAULT '',
        tutor_nombre TEXT NOT NULL,
        tutor_ci TEXT DEFAULT '',
        tutor_telefono TEXT NOT NULL,
        activo INTEGER DEFAULT 1,
        actualizado_en TEXT DEFAULT '',
        FOREIGN KEY (curso_id) REFERENCES cursos (id) ON DELETE CASCADE
    )
    """)
    _agregar_columna_si_no_existe(cursor, "estudiantes", "ci", "TEXT", "''")
    _agregar_columna_si_no_existe(cursor, "estudiantes", "tutor_ci", "TEXT", "''")

    # Tabla Permisos
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS permisos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        estudiante_id INTEGER NOT NULL,
        fecha TEXT NOT NULL,
        motivo TEXT NOT NULL,
        aprobado INTEGER DEFAULT 1,
        activo INTEGER DEFAULT 1,
        actualizado_en TEXT DEFAULT '',
        FOREIGN KEY (estudiante_id) REFERENCES estudiantes (id) ON DELETE CASCADE
    )
    """)

    # Tabla Asistencias
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS asistencias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        estudiante_id INTEGER NOT NULL,
        fecha TEXT NOT NULL,
        estado TEXT NOT NULL DEFAULT 'PRESENTE',
        observacion TEXT,
        notificado_whatsapp INTEGER DEFAULT 0,
        FOREIGN KEY (estudiante_id) REFERENCES estudiantes (id) ON DELETE CASCADE,
        UNIQUE(estudiante_id, fecha)
    )
    """)

    # Tabla Configuración
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS configuracion (
        clave TEXT PRIMARY KEY,
        valor TEXT
    )
    """)

    # Tabla Docentes (con CI)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS docentes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre_completo TEXT NOT NULL,
        ci TEXT DEFAULT '',
        materia TEXT NOT NULL,
        telefono TEXT,
        email TEXT,
        activo INTEGER DEFAULT 1,
        creado_en TEXT DEFAULT (datetime('now','localtime')),
        actualizado_en TEXT DEFAULT ''
    )
    """)
    _agregar_columna_si_no_existe(cursor, "docentes", "ci", "TEXT", "''")

    # Tabla Materias
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS materias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL UNIQUE,
        nivel TEXT DEFAULT 'Secundaria',
        descripcion TEXT,
        activa INTEGER DEFAULT 1,
        actualizado_en TEXT DEFAULT ''
    )
    """)

    # === MIGRACIONES: agregar columnas activo y actualizado_en a tablas existentes ===
    _agregar_columna_si_no_existe(cursor, "cursos", "activo", "INTEGER", "1")
    _agregar_columna_si_no_existe(cursor, "cursos", "actualizado_en", "TEXT", "''")
    _agregar_columna_si_no_existe(cursor, "estudiantes", "activo", "INTEGER", "1")
    _agregar_columna_si_no_existe(cursor, "estudiantes", "actualizado_en", "TEXT", "''")
    _agregar_columna_si_no_existe(cursor, "permisos", "activo", "INTEGER", "1")
    _agregar_columna_si_no_existe(cursor, "permisos", "actualizado_en", "TEXT", "''")
    _agregar_columna_si_no_existe(cursor, "docentes", "actualizado_en", "TEXT", "''")
    _agregar_columna_si_no_existe(cursor, "materias", "actualizado_en", "TEXT", "''")

    # Configuración por defecto
    cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('institucion', 'Colegio Nacional')")
    cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('materia', 'Clase General')")
    cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('docente', 'Profesor(a)')")
    cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('codigo_pais', '+591')")
    cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('nivel_educativo', 'Secundaria')")
    cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('mensaje_whatsapp', 'Estimado(a) {tutor}: Le informamos de la institución {institucion} que su hijo(a) {estudiante} registró INASISTENCIA el día {fecha}. Por favor comunicarse para justificar la falta.')")
    cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('docente_actual_id', '')")
    cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('setup_completado', '0')")

    # Materias por defecto
    cursor.execute("SELECT COUNT(*) as count FROM materias")
    if cursor.fetchone()["count"] == 0:
        materias_default = [
            ("Matemática", "Secundaria", "Álgebra, geometría y cálculo"),
            ("Lenguaje y Literatura", "Secundaria", "Comprensión lectora y redacción"),
            ("Ciencias Sociales", "Secundaria", "Historia, geografía y civismo"),
            ("Ciencias Naturales", "Secundaria", "Biología, física y química"),
            ("Inglés", "Secundaria", "Idioma extranjero"),
            ("Educación Física", "Secundaria", "Deporte y salud"),
            ("Artes Plásticas", "Secundaria", "Expresión artística"),
            ("Tecnología", "Secundaria", "Informática y tecnología"),
            ("Filosofía", "Secundaria", "Pensamiento crítico"),
            ("Religión / Ética", "Secundaria", "Valores y ética"),
        ]
        for nombre_m, nivel_m, desc_m in materias_default:
            cursor.execute(
                "INSERT INTO materias (nombre, nivel, descripcion) VALUES (?, ?, ?)",
                (nombre_m, nivel_m, desc_m)
            )

    # Curso y estudiantes de ejemplo
    cursor.execute("SELECT COUNT(*) as count FROM cursos")
    if cursor.fetchone()["count"] == 0:
        cursor.execute("INSERT INTO cursos (nombre, nivel, seccion) VALUES ('1ro Secundaria', 'Secundaria', 'A')")
        curso_id = cursor.lastrowid

        alumnos_ejemplo = [
            ("Mateo González", "12345678", "Carlos González", "87654321", "71234567"),
            ("Sofía Martínez", "23456789", "Laura Martínez", "76543210", "78765432"),
            ("Lucas Rodríguez", "34567890", "Patricia Rodríguez", "65432109", "73334444"),
            ("Valentina Pérez", "45678901", "Roberto Pérez", "54321098", "75556666"),
            ("Joaquín Fernández", "56789012", "Elena Fernández", "43210987", "77778888")
        ]
        for nom, ci, tut, tut_ci, tel in alumnos_ejemplo:
            cursor.execute(
                "INSERT INTO estudiantes (curso_id, nombre_completo, ci, tutor_nombre, tutor_ci, tutor_telefono) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (curso_id, nom, ci, tut, tut_ci, tel)
            )

    conn.commit()
    conn.close()


# --- CURSOS ---
def obtener_cursos(solo_activos: bool = True) -> List[sqlite3.Row]:
    conn = get_connection()
    cursor = conn.cursor()
    where = "WHERE activo = 1" if solo_activos else "WHERE 1=1"
    cursor.execute(f"SELECT * FROM cursos {where} ORDER BY nombre")
    cursos = cursor.fetchall()
    conn.close()
    return cursos


def crear_curso(nombre: str, nivel: str = "", seccion: str = "") -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO cursos (nombre, nivel, seccion, activo) VALUES (?, ?, ?, 1)",
        (nombre, nivel, seccion))
    conn.commit()
    cid = cursor.lastrowid
    conn.close()
    return cid


def actualizar_curso(curso_id: int, nombre: str, nivel: str = "", seccion: str = ""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE cursos SET nombre=?, nivel=?, seccion=?,
               actualizado_en=datetime('now','localtime')
        WHERE id=?
    """, (nombre.strip(), nivel.strip(), seccion.strip(), curso_id))
    conn.commit()
    conn.close()


def eliminar_curso(curso_id: int):
    """Eliminación LÓGICA: marca inactivo, no borra datos históricos."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE cursos SET activo=0,
               actualizado_en=datetime('now','localtime')
        WHERE id=?
    """, (curso_id,))
    cursor.execute("""
        UPDATE estudiantes SET activo=0,
               actualizado_en=datetime('now','localtime')
        WHERE curso_id=?
    """, (curso_id,))
    conn.commit()
    conn.close()


def reactivar_curso(curso_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE cursos SET activo=1 WHERE id=?", (curso_id,))
    conn.commit()
    conn.close()


# --- ESTUDIANTES ---
def obtener_estudiantes_curso(curso_id: int, solo_activos: bool = True) -> List[sqlite3.Row]:
    conn = get_connection()
    cursor = conn.cursor()
    where = "AND activo = 1" if solo_activos else ""
    cursor.execute(
        f"SELECT * FROM estudiantes WHERE curso_id = ? {where} ORDER BY nombre_completo",
        (curso_id,))
    alumnos = cursor.fetchall()
    conn.close()
    return alumnos


def buscar_estudiantes(curso_id: Optional[int] = None, texto: str = "",
                       incluir_inactivos: bool = False) -> List[sqlite3.Row]:
    conn = get_connection()
    cursor = conn.cursor()
    like = f"%{texto.strip().lower()}%"
    filtro_activo = "" if incluir_inactivos else "AND e.activo = 1"
    if curso_id is not None:
        cursor.execute(f"""
            SELECT e.*, c.nombre AS curso_nombre
            FROM estudiantes e
            JOIN cursos c ON e.curso_id = c.id
            WHERE e.curso_id = ? {filtro_activo}
              AND (LOWER(e.nombre_completo) LIKE ?
                   OR LOWER(COALESCE(e.ci,'')) LIKE ?
                   OR LOWER(e.tutor_nombre) LIKE ?
                   OR LOWER(COALESCE(e.tutor_ci,'')) LIKE ?)
            ORDER BY e.nombre_completo
        """, (curso_id, like, like, like, like))
    else:
        cursor.execute(f"""
            SELECT e.*, c.nombre AS curso_nombre
            FROM estudiantes e
            JOIN cursos c ON e.curso_id = c.id
            WHERE 1=1 {filtro_activo}
              AND (LOWER(e.nombre_completo) LIKE ?
                   OR LOWER(COALESCE(e.ci,'')) LIKE ?
                   OR LOWER(e.tutor_nombre) LIKE ?
                   OR LOWER(COALESCE(e.tutor_ci,'')) LIKE ?)
            ORDER BY e.nombre_completo
        """, (like, like, like, like))
    filas = cursor.fetchall()
    conn.close()
    return filas


def crear_estudiante(curso_id: int, nombre: str, ci: str, tutor: str,
                     tutor_ci: str, telefono: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO estudiantes
        (curso_id, nombre_completo, ci, tutor_nombre, tutor_ci, tutor_telefono, activo)
        VALUES (?, ?, ?, ?, ?, ?, 1)
    """, (curso_id, nombre.strip(), ci.strip(), tutor.strip(),
          tutor_ci.strip(), telefono.strip()))
    conn.commit()
    conn.close()


def actualizar_estudiante(estudiante_id: int, curso_id: int, nombre: str, ci: str,
                          tutor: str, tutor_ci: str, telefono: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE estudiantes
        SET curso_id=?, nombre_completo=?, ci=?, tutor_nombre=?, tutor_ci=?,
            tutor_telefono=?, actualizado_en=datetime('now','localtime')
        WHERE id=?
    """, (curso_id, nombre.strip(), ci.strip(), tutor.strip(),
          tutor_ci.strip(), telefono.strip(), estudiante_id))
    conn.commit()
    conn.close()


def eliminar_estudiante(estudiante_id: int):
    """Eliminación LÓGICA."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE estudiantes SET activo=0,
               actualizado_en=datetime('now','localtime')
        WHERE id=?
    """, (estudiante_id,))
    conn.commit()
    conn.close()


def reactivar_estudiante(estudiante_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE estudiantes SET activo=1 WHERE id=?", (estudiante_id,))
    conn.commit()
    conn.close()


# --- DOCENTES ---
def crear_docente(nombre: str, ci: str, materia: str, telefono: str = "", email: str = "") -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO docentes (nombre_completo, ci, materia, telefono, email, activo) VALUES (?, ?, ?, ?, ?, 1)",
        (nombre.strip(), ci.strip(), materia.strip(), telefono.strip(), email.strip())
    )
    conn.commit()
    did = cursor.lastrowid
    conn.close()
    return did


def obtener_docentes(solo_activos: bool = True, texto: str = "") -> List[sqlite3.Row]:
    conn = get_connection()
    cursor = conn.cursor()
    where = "WHERE activo = 1" if solo_activos else "WHERE 1=1"
    params: List = []
    if texto.strip():
        like = f"%{texto.strip().lower()}%"
        where += " AND (LOWER(nombre_completo) LIKE ? OR LOWER(COALESCE(ci,'')) LIKE ? OR LOWER(materia) LIKE ?)"
        params.extend([like, like, like])
    cursor.execute(f"SELECT * FROM docentes {where} ORDER BY nombre_completo", params)
    docentes = cursor.fetchall()
    conn.close()
    return docentes


def obtener_docente(docente_id: int) -> Optional[sqlite3.Row]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM docentes WHERE id = ?", (docente_id,))
    doc = cursor.fetchone()
    conn.close()
    return doc


def eliminar_docente(docente_id: int):
    """Eliminación LÓGICA."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE docentes SET activo=0,
               actualizado_en=datetime('now','localtime')
        WHERE id=?
    """, (docente_id,))
    conn.commit()
    conn.close()


def reactivar_docente(docente_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE docentes SET activo=1 WHERE id=?", (docente_id,))
    conn.commit()
    conn.close()


def actualizar_docente(docente_id: int, nombre: str, ci: str, materia: str,
                       telefono: str = "", email: str = ""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE docentes SET nombre_completo = ?, ci = ?, materia = ?, telefono = ?, email = ?,
               actualizado_en=datetime('now','localtime')
        WHERE id = ?
    """, (nombre.strip(), ci.strip(), materia.strip(), telefono.strip(), email.strip(), docente_id))
    conn.commit()
    conn.close()


# --- MATERIAS ---
def crear_materia(nombre: str, nivel: str = "Secundaria", descripcion: str = "") -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO materias (nombre, nivel, descripcion, activa) VALUES (?, ?, ?, 1)",
        (nombre.strip(), nivel.strip(), descripcion.strip())
    )
    conn.commit()
    mid = cursor.lastrowid
    conn.close()
    return mid


def obtener_materias(solo_activas: bool = True, texto: str = "") -> List[sqlite3.Row]:
    conn = get_connection()
    cursor = conn.cursor()
    where = "WHERE activa = 1" if solo_activas else "WHERE 1=1"
    params: List = []
    if texto.strip():
        like = f"%{texto.strip().lower()}%"
        where += " AND (LOWER(nombre) LIKE ? OR LOWER(COALESCE(descripcion,'')) LIKE ?)"
        params.extend([like, like])
    cursor.execute(f"SELECT * FROM materias {where} ORDER BY nombre", params)
    materias = cursor.fetchall()
    conn.close()
    return materias


def actualizar_materia(materia_id: int, nombre: str, nivel: str = "Secundaria", descripcion: str = ""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE materias SET nombre=?, nivel=?, descripcion=?,
               actualizado_en=datetime('now','localtime')
        WHERE id=?
    """, (nombre.strip(), nivel.strip(), descripcion.strip(), materia_id))
    conn.commit()
    conn.close()


def eliminar_materia(materia_id: int):
    """Eliminación LÓGICA."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE materias SET activa=0,
               actualizado_en=datetime('now','localtime')
        WHERE id=?
    """, (materia_id,))
    conn.commit()
    conn.close()


def reactivar_materia(materia_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE materias SET activa=1 WHERE id=?", (materia_id,))
    conn.commit()
    conn.close()


# --- ASISTENCIA ---
def cargar_o_iniciar_asistencia_dia(curso_id: int, fecha: str) -> List[Dict]:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM estudiantes WHERE curso_id = ? AND activo = 1 ORDER BY nombre_completo",
        (curso_id,))
    estudiantes = cursor.fetchall()
    if not estudiantes:
        conn.close()
        return []

    cursor.execute(
        "SELECT estudiante_id, motivo FROM permisos WHERE fecha = ? AND aprobado = 1 AND activo = 1",
        (fecha,))
    permisos = {row["estudiante_id"]: row["motivo"] for row in cursor.fetchall()}

    for est in estudiantes:
        eid = est["id"]
        estado_inicial = "PERMISO" if eid in permisos else "PRESENTE"
        obs_inicial = f"Permiso justificado: {permisos[eid]}" if eid in permisos else ""
        cursor.execute("""
            INSERT OR IGNORE INTO asistencias (estudiante_id, fecha, estado, observacion, notificado_whatsapp)
            VALUES (?, ?, ?, ?, 0)
        """, (eid, fecha, estado_inicial, obs_inicial))

    conn.commit()

    cursor.execute("""
        SELECT 
            a.id as asistencia_id,
            e.id as estudiante_id,
            e.nombre_completo,
            COALESCE(e.ci,'') as ci,
            e.tutor_nombre,
            COALESCE(e.tutor_ci,'') as tutor_ci,
            e.tutor_telefono,
            a.fecha, a.estado, a.observacion, a.notificado_whatsapp
        FROM estudiantes e
        JOIN asistencias a ON e.id = a.estudiante_id
        WHERE e.curso_id = ? AND a.fecha = ? AND e.activo = 1
        ORDER BY e.nombre_completo
    """, (curso_id, fecha))

    filas = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return filas


def actualizar_estado_asistencia(asistencia_id: int, nuevo_estado: str, observacion: str = ""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE asistencias SET estado = ?, observacion = ? WHERE id = ?",
                   (nuevo_estado, observacion, asistencia_id))
    conn.commit()
    conn.close()


def marcar_whatsapp_notificado(asistencia_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE asistencias SET notificado_whatsapp = 1 WHERE id = ?", (asistencia_id,))
    conn.commit()
    conn.close()


# --- PERMISOS ---
def registrar_permiso(estudiante_id: int, fecha: str, motivo: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO permisos (estudiante_id, fecha, motivo, aprobado, activo) VALUES (?, ?, ?, 1, 1)",
        (estudiante_id, fecha, motivo))
    cursor.execute("""
        UPDATE asistencias SET estado = 'PERMISO', observacion = ?
        WHERE estudiante_id = ? AND fecha = ?
    """, (f"Permiso: {motivo}", estudiante_id, fecha))
    conn.commit()
    conn.close()


def actualizar_permiso(permiso_id: int, fecha: str, motivo: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE permisos SET fecha=?, motivo=?,
               actualizado_en=datetime('now','localtime')
        WHERE id=?
    """, (fecha, motivo.strip(), permiso_id))
    conn.commit()
    conn.close()


def eliminar_permiso(permiso_id: int):
    """Eliminación LÓGICA."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE permisos SET activo=0,
               actualizado_en=datetime('now','localtime')
        WHERE id=?
    """, (permiso_id,))
    conn.commit()
    conn.close()


def reactivar_permiso(permiso_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE permisos SET activo=1 WHERE id=?", (permiso_id,))
    conn.commit()
    conn.close()


def obtener_permisos(texto: str = "", incluir_inactivos: bool = False) -> List[sqlite3.Row]:
    conn = get_connection()
    cursor = conn.cursor()
    condiciones = []
    params: List = []
    if not incluir_inactivos:
        condiciones.append("p.activo = 1")
    if texto.strip():
        like = f"%{texto.strip().lower()}%"
        condiciones.append("""(
            LOWER(e.nombre_completo) LIKE ? OR LOWER(COALESCE(e.ci,'')) LIKE ?
            OR LOWER(e.tutor_nombre) LIKE ? OR LOWER(COALESCE(e.tutor_ci,'')) LIKE ?
        )""")
        params.extend([like, like, like, like])
    where = ("WHERE " + " AND ".join(condiciones)) if condiciones else ""
    cursor.execute(f"""
        SELECT p.*, e.nombre_completo, COALESCE(e.ci,'') as ci,
               e.tutor_nombre, COALESCE(e.tutor_ci,'') as tutor_ci,
               c.nombre as curso_nombre
        FROM permisos p
        JOIN estudiantes e ON p.estudiante_id = e.id
        JOIN cursos c ON e.curso_id = c.id
        {where}
        ORDER BY p.fecha DESC
    """, params)
    permisos = cursor.fetchall()
    conn.close()
    return permisos


# --- CONFIGURACIÓN ---
def obtener_configuracion() -> Dict[str, str]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT clave, valor FROM configuracion")
    config = {row["clave"]: row["valor"] for row in cursor.fetchall()}
    conn.close()
    return config


def guardar_configuracion(clave: str, valor: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)", (clave, valor))
    conn.commit()
    conn.close()


# --- SETUP ---
def setup_completado() -> bool:
    cfg = obtener_configuracion()
    return cfg.get("setup_completado", "0") == "1"


def marcar_setup_completado(docente_id: int, docente_nombre: str, materia: str):
    guardar_configuracion("setup_completado", "1")
    guardar_configuracion("docente_actual_id", str(docente_id))
    guardar_configuracion("docente", docente_nombre)
    guardar_configuracion("materia", materia)


# ============================================================
# ASIGNACIÓN DOCENTE ↔ CURSO (relación N:M)
# ============================================================

def _crear_tabla_docente_curso(cursor):
    """Crea la tabla de relación docente-curso si no existe."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS docente_curso (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            docente_id INTEGER NOT NULL,
            curso_id INTEGER NOT NULL,
            activo INTEGER DEFAULT 1,
            actualizado_en TEXT DEFAULT '',
            FOREIGN KEY(docente_id) REFERENCES docentes(id),
            FOREIGN KEY(curso_id) REFERENCES cursos(id),
            UNIQUE(docente_id, curso_id)
        )
    """)


def asignar_curso_a_docente(docente_id: int, curso_id: int):
    """Asigna (o reactiva) un curso a un docente."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO docente_curso (docente_id, curso_id, activo) VALUES (?, ?, 1)",
            (docente_id, curso_id)
        )
    except sqlite3.IntegrityError:
        # Ya existe la fila → reactivarla (borrado lógico reversible)
        cursor.execute(
            "UPDATE docente_curso SET activo=1, actualizado_en=datetime('now','localtime') "
            "WHERE docente_id=? AND curso_id=?",
            (docente_id, curso_id)
        )
    conn.commit()
    conn.close()


def desasignar_curso_de_docente(docente_id: int, curso_id: int):
    """Borrado lógico: desactiva la asignación docente-curso."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE docente_curso SET activo=0, actualizado_en=datetime('now','localtime') "
        "WHERE docente_id=? AND curso_id=?",
        (docente_id, curso_id)
    )
    conn.commit()
    conn.close()


def obtener_cursos_de_docente(docente_id: int, incluir_inactivos: bool = False) -> List[sqlite3.Row]:
    """Lista los cursos asignados a un docente (solo activos por defecto)."""
    conn = get_connection()
    cursor = conn.cursor()
    filtro = "" if incluir_inactivos else "AND dc.activo = 1"
    cursor.execute(f"""
        SELECT c.id, c.nombre, c.seccion, dc.activo
        FROM docente_curso dc
        JOIN cursos c ON c.id = dc.curso_id
        WHERE dc.docente_id = ? {filtro}
        ORDER BY c.nombre
    """, (docente_id,))
    filas = cursor.fetchall()
    conn.close()
    return filas


def obtener_docentes_con_cursos(solo_activos: bool = True, texto: str = "") -> List[Dict]:
    """Devuelve docentes enriquecidos con la lista de cursos asignados."""
    docentes = obtener_docentes(solo_activos, texto)
    resultado = []
    for d in docentes:
        d_dict = dict(d)
        cursos = obtener_cursos_de_docente(d["id"])
        d_dict["cursos_asignados"] = [dict(c) for c in cursos]
        resultado.append(d_dict)
    return resultado