import flet as ft
import datetime
import os
import csv
import asyncio
import database as db
import whatsapp_helper as wa
import reports
import database_addons as extra
import sqlite3


def init_docente_curso_table():
    try:
        conn = db.get_connection()
        conn.execute("""
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
        conn.commit()
        conn.close()
    except Exception as ex:
        print(f"Error creando tabla docente_curso: {ex}")


def asignar_curso_a_docente(docente_id, curso_id):
    conn = db.get_connection()
    try:
        conn.execute(
            "INSERT INTO docente_curso (docente_id, curso_id, activo) VALUES (?, ?, 1)",
            (docente_id, curso_id)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.execute(
            "UPDATE docente_curso SET activo=1, actualizado_en=datetime('now','localtime') "
            "WHERE docente_id=? AND curso_id=?",
            (docente_id, curso_id)
        )
        conn.commit()
    finally:
        conn.close()


def desasignar_curso_de_docente(docente_id, curso_id):
    conn = db.get_connection()
    conn.execute(
        "UPDATE docente_curso SET activo=0, actualizado_en=datetime('now','localtime') "
        "WHERE docente_id=? AND curso_id=?",
        (docente_id, curso_id)
    )
    conn.commit()
    conn.close()


def obtener_cursos_de_docente(docente_id, incluir_inactivos=False):
    conn = db.get_connection()
    filtro = "" if incluir_inactivos else "AND dc.activo=1"
    cur = conn.execute(f"""
        SELECT c.id, c.nombre, c.seccion, dc.activo
        FROM docente_curso dc
        JOIN cursos c ON c.id = dc.curso_id
        WHERE dc.docente_id=? {filtro}
        ORDER BY c.nombre
    """, (docente_id,))
    cols = [d[0] for d in cur.description]
    filas = [dict(zip(cols, r)) for r in cur.fetchall()]
    conn.close()
    return filas


def main(page: ft.Page):
    page.title = "Control de Asistencia Docente - Secundaria"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(
        navigation_bar_theme=ft.NavigationBarTheme(
            label_text_style=ft.TextStyle(size=10, weight=ft.FontWeight.W_500)
        )
    )
    page.padding = 0
    page.window.width = 412
    page.window.height = 840
    page.window.resizable = True
    db.init_db()
    extra.init_extra_db()
    init_docente_curso_table()
    url_launcher = ft.UrlLauncher()
    file_picker = ft.FilePicker()
    page.services.append(file_picker)

    def mostrar_snack(mensaje: str, color=ft.Colors.GREEN_700):
        snack = ft.SnackBar(
            content=ft.Text(mensaje, color=ft.Colors.WHITE, weight=ft.FontWeight.W_500),
            bgcolor=color, duration=3500
        )
        page.overlay.append(snack)
        snack.open = True
        page.update()

    def dialogo_editar(titulo, campos, on_guardar):
        campos_ctrl = {}
        for label, value, key in campos:
            campos_ctrl[key] = ft.TextField(label=label, value=value or "", dense=True)

        def guardar(e):
            datos = {k: c.value for k, c in campos_ctrl.items()}
            try:
                ok = on_guardar(datos)
                if ok is False:
                    return
                page.pop_dialog()
                page.update()
                mostrar_snack("Cambios guardados correctamente.")
            except Exception as ex:
                mostrar_snack(f"Error al guardar: {ex}", ft.Colors.RED_700)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([ft.Icon(ft.Icons.EDIT, color=ft.Colors.INDIGO_700),
                          ft.Text(titulo, weight=ft.FontWeight.BOLD)]),
            content=ft.Column([campos_ctrl[k] for _, _, k in campos],
                              spacing=8, tight=True, width=380),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: (page.pop_dialog(), page.update())),
                ft.Button("Guardar", icon=ft.Icons.SAVE, on_click=guardar),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.show_dialog(dlg)
        page.update()

    def dialogo_confirmar_eliminar(nombre, on_confirmar, es_reactivar=False):
        def confirmar(ev):
            page.pop_dialog()
            page.update()
            on_confirmar()

        if es_reactivar:
            titulo = "Confirmar reactivación"
            contenido = f"¿Reactivar '{nombre}'?"
            texto_btn = "Reactivar"
            color_btn = ft.Colors.GREEN_600
        else:
            titulo = "Confirmar eliminación lógica"
            contenido = f"¿Desactivar '{nombre}'? No se borrarán sus datos históricos."
            texto_btn = "Desactivar"
            color_btn = ft.Colors.RED_600

        page.show_dialog(ft.AlertDialog(
            modal=True,
            title=ft.Text(titulo),
            content=ft.Text(contenido),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: (page.pop_dialog(), page.update())),
                ft.Button(texto_btn, bgcolor=color_btn, color=ft.Colors.WHITE,
                          on_click=confirmar),
            ]))
        page.update()

    def mostrar_presentacion():
        page.controls.clear()
        page.navigation_bar = None
        page.appbar = None
        page.add(ft.Container(
            expand=True, padding=24, alignment=ft.Alignment.CENTER,
            gradient=ft.LinearGradient(
                colors=[ft.Colors.INDIGO_900, ft.Colors.INDIGO_500],
                begin=ft.Alignment.TOP_CENTER, end=ft.Alignment.BOTTOM_CENTER
            ),
            content=ft.Column([
                ft.Icon(ft.Icons.SCHOOL, size=86, color=ft.Colors.WHITE),
                ft.Text("ASISTENCIA ESCOLAR MÓVIL", size=22,
                        weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE,
                        text_align=ft.TextAlign.CENTER),
                ft.Text("Control de asistencia, estudiantes, docentes y reportes",
                        size=13, color=ft.Colors.WHITE, text_align=ft.TextAlign.CENTER),
                ft.Text("Desarrollado con Python, Flet y SQLite", size=11,
                        italic=True, color=ft.Colors.WHITE),
                ft.Text("Debeloped by: J_C_CH_Q", size=10,
                        italic=True, color=ft.Colors.WHITE),
                ft.Container(height=30),
                ft.ProgressRing(color=ft.Colors.WHITE, width=34, stroke_width=3),
                ft.Text("Iniciando aplicación...", size=12, italic=True,
                        color=ft.Colors.with_opacity(0.7, ft.Colors.WHITE)),
            ], alignment=ft.MainAxisAlignment.CENTER,
               horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)
        ))
        page.update()

        async def auto_inicio():
            await asyncio.sleep(2)
            mostrar_selector_colegio()
        page.run_task(auto_inicio)

    def mostrar_selector_colegio():
        page.controls.clear()
        page.navigation_bar = None
        page.appbar = None

        colegios = list(extra.listar_colegios())
        if not colegios:
            page.add(ft.Container(
                expand=True, padding=20,
                content=ft.Column([
                    ft.Icon(ft.Icons.ERROR_OUTLINE, color=ft.Colors.RED_700, size=40),
                    ft.Text("No hay colegios registrados.", color=ft.Colors.RED_700),
                    ft.Button("Volver", on_click=lambda e: mostrar_presentacion())
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            ))
            page.update()
            return

        dd_colegio = ft.Dropdown(
            label="Selecciona el colegio", dense=True,
            options=[ft.dropdown.Option(str(c["id"]), c["nombre"]) for c in colegios],
            value=str(colegios[0]["id"])
        )

        # RadioGroup con columna de Radio (selección única)
        col_radios = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=4)
        radio_group_cursos = ft.RadioGroup(content=col_radios)

        def cargar_cursos(e=None):
            col_radios.controls.clear()
            radio_group_cursos.value = None
            try:
                cid = int(dd_colegio.value)
                cursos = [dict(c) for c in extra.obtener_cursos_extendido()]
                disponibles = [c for c in cursos if c.get("colegio_id") == cid or not c.get("colegio_id")]
                if not disponibles:
                    col_radios.controls.append(ft.Text("No hay cursos para este colegio.", italic=True))
                else:
                    col_radios.controls.append(ft.Text("Selecciona un curso:", size=12))

                    for curso in disponibles:
                        col_radios.controls.append(ft.Row([
                            ft.Radio(
                                value=str(curso["id"]),
                                label=f"{curso['nombre']} {curso.get('seccion') or ''}".strip()
                            ),
                            ft.IconButton(ft.Icons.EDIT, icon_size=16,
                                          icon_color=ft.Colors.INDIGO_600,
                                          tooltip="Editar curso",
                                          on_click=lambda e, c=curso: editar_curso(c)),
                            ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_size=16,
                                          icon_color=ft.Colors.RED_400,
                                          tooltip="Desactivar curso",
                                          on_click=lambda e, c=curso: eliminar_curso_ui(c)),
                        ], spacing=4, expand=True,
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN))

            except Exception as ex:
                col_radios.controls.append(ft.Text(f"Error: {ex}", color=ft.Colors.RED_700))
            page.update()

        def crear_curso(e):
            txt_nombre = ft.TextField(label="Nombre (Ej: 2do Secundaria)", dense=True)
            txt_seccion = ft.TextField(label="Sección (Ej: A, B)", dense=True)

            def guardar(ev):
                nombre = txt_nombre.value.strip()
                seccion = txt_seccion.value.strip()
                if not nombre:
                    mostrar_snack("Escribe el nombre.", ft.Colors.RED_700)
                    return
                try:
                    cid = db.crear_curso(nombre, "Secundaria", seccion)
                    colegio_id = int(dd_colegio.value)
                    extra.asignar_colegio_turno_curso(cid, colegio_id, None)
                    page.pop_dialog()
                    cargar_cursos()
                    mostrar_snack("Curso creado.", ft.Colors.GREEN_700)
                except Exception as ex:
                    mostrar_snack(f"Error: {ex}", ft.Colors.RED_700)

            dlg = ft.AlertDialog(
                modal=True,
                title=ft.Text("Nuevo curso"),
                content=ft.Column([txt_nombre, txt_seccion], tight=True, spacing=10),
                actions=[
                    ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog()),
                    ft.Button("Crear", icon=ft.Icons.ADD, on_click=guardar)
                ]
            )
            page.show_dialog(dlg)
            page.update()

        # ===== FUNCIONES DE EDICIÓN (movidas ANTES de page.add para evitar UnboundLocalError) =====
        def editar_curso(curso):
            txt_nom = ft.TextField(label="Nombre del curso", value=curso["nombre"], dense=True)
            txt_sec = ft.TextField(label="Sección", value=curso.get("seccion") or "", dense=True)
            txt_niv = ft.TextField(label="Nivel", value=curso.get("nivel") or "Secundaria", dense=True)

            def guardar(ev):
                if not txt_nom.value.strip():
                    mostrar_snack("El nombre no puede quedar vacío.", ft.Colors.RED_700)
                    return
                db.actualizar_curso(curso["id"], txt_nom.value.strip(),
                                    txt_niv.value.strip(), txt_sec.value.strip())
                page.pop_dialog()
                cargar_cursos()
                mostrar_snack("Curso actualizado correctamente.")

            dlg = ft.AlertDialog(
                modal=True,
                title=ft.Text("Editar curso"),
                content=ft.Column([txt_nom, txt_sec, txt_niv], tight=True, spacing=10),
                actions=[
                    ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog()),
                    ft.Button("Guardar", icon=ft.Icons.SAVE, on_click=guardar)
                ]
            )
            page.show_dialog(dlg)
            page.update()

        def eliminar_curso_ui(curso):
            nombre = f"{curso['nombre']} {curso.get('seccion') or ''}".strip()

            def confirmar():
                db.eliminar_curso(curso["id"])
                mostrar_snack(f"Curso '{nombre}' desactivado (eliminación lógica).")
                cargar_cursos()
            dialogo_confirmar_eliminar(nombre, confirmar, es_reactivar=False)

        def editar_colegio_ui(e):
            lista_colegios = list(extra.listar_colegios())
            col = next((c for c in lista_colegios if str(c["id"]) == dd_colegio.value), None)
            if not col:
                mostrar_snack("Selecciona un colegio primero.", ft.Colors.RED_700)
                return
            txt_nom = ft.TextField(label="Nombre del colegio", value=col["nombre"], dense=True)
            txt_dir = ft.TextField(label="Dirección", value=col.get("direccion") or "", dense=True)
            txt_tel = ft.TextField(label="Teléfono", value=col.get("telefono") or "", dense=True)

            def guardar(ev):
                if not txt_nom.value.strip():
                    mostrar_snack("El nombre no puede quedar vacío.", ft.Colors.RED_700)
                    return
                extra.guardar_colegio(txt_nom.value.strip(), txt_dir.value.strip(),
                                      txt_tel.value.strip(), colegio_id=col["id"])
                page.pop_dialog()
                dd_colegio.options = [ft.dropdown.Option(str(c["id"]), c["nombre"])
                                      for c in extra.listar_colegios()]
                page.update()
                mostrar_snack("Colegio actualizado correctamente.")

            dlg = ft.AlertDialog(
                modal=True,
                title=ft.Text("Editar colegio"),
                content=ft.Column([txt_nom, txt_dir, txt_tel], tight=True, spacing=10),
                actions=[
                    ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog()),
                    ft.Button("Guardar", icon=ft.Icons.SAVE, on_click=guardar)
                ]
            )
            page.show_dialog(dlg)
            page.update()
        # ===== FIN FUNCIONES DE EDICIÓN =====

        def continuar(e):
            if not radio_group_cursos.value:
                mostrar_snack("Selecciona un curso.", ft.Colors.RED_700)
                return
            seleccionados = [radio_group_cursos.value]
            colegio_id = int(dd_colegio.value)
            db.guardar_configuracion("colegio_actual_id", str(colegio_id))
            db.guardar_configuracion("cursos_activos_ids", ",".join(seleccionados))
            colegio = next((c for c in colegios if c["id"] == colegio_id), None)
            if colegio:
                db.guardar_configuracion("institucion", colegio["nombre"])
            # Vincular el curso seleccionado al colegio si aún no tiene uno
            todos = [dict(c) for c in extra.obtener_cursos_extendido()]
            for curso in todos:
                if str(curso["id"]) in seleccionados and not curso.get("colegio_id"):
                    extra.asignar_colegio_turno_curso(curso["id"], colegio_id, None)
            if not db.setup_completado():
                mostrar_pantalla_setup()
            else:
                iniciar_app_principal()

        dd_colegio.on_change = cargar_cursos
        cargar_cursos()

        page.add(ft.Container(
            expand=True, padding=18,
            content=ft.Column([
                ft.Row([
                    ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda e: mostrar_presentacion()),
                    ft.Text("Colegio y cursos", size=19, weight=ft.FontWeight.BOLD)
                ]),
                ft.Divider(),
                dd_colegio,
                ft.Row([
                    ft.Text("Curso disponible", weight=ft.FontWeight.BOLD, expand=True),
                   
                    ft.IconButton(icon=ft.Icons.ADD_CIRCLE, icon_color=ft.Colors.GREEN_700, on_click=crear_curso)
                ]),
                radio_group_cursos,
                ft.Container(expand=True),
                ft.Button(content="Continuar", icon=ft.Icons.CHECK, on_click=continuar, width=300)
            ], expand=True, spacing=12)
        ))
        page.update()

    def mostrar_pantalla_setup():
        materias_db = db.obtener_materias()
        txt_docente_nombre = ft.TextField(label="Nombre completo del Docente",
                                          hint_text="Ej: Prof. Juan Pérez Mamani", dense=True,
                                          prefix_icon=ft.Icons.PERSON)
        txt_docente_ci = ft.TextField(label="Carnet de Identidad (CI)", dense=True,
                                       prefix_icon=ft.Icons.BADGE)
        dropdown_materia = ft.Dropdown(
            label="Materia que regenta", dense=True,
            options=[ft.dropdown.Option(str(m["id"]), m["nombre"]) for m in materias_db],
            hint_text="Selecciona la materia"
        )
        txt_materia_nueva = ft.TextField(
            label="¿No encuentras tu materia? Escribe una nueva",
            hint_text="Ej: Física Avanzada", dense=True, prefix_icon=ft.Icons.ADD
        )
        txt_telefono_docente = ft.TextField(
            label="Teléfono del Docente (opcional)", prefix=ft.Text("+591 "),
            dense=True, keyboard_type=ft.KeyboardType.PHONE
        )

        def registrar_docente_setup(e):
            nombre = txt_docente_nombre.value.strip()
            ci = txt_docente_ci.value.strip()
            if not nombre or not ci:
                mostrar_snack("Ingresa el nombre y CI del docente.", ft.Colors.RED_700)
                return
            materia_final = ""
            if txt_materia_nueva.value.strip():
                materia_final = txt_materia_nueva.value.strip()
                try:
                    db.crear_materia(materia_final, "Secundaria", "Creada en registro inicial")
                except Exception:
                    pass
            elif dropdown_materia.value:
                mat = next((m for m in materias_db if str(m["id"]) == dropdown_materia.value), None)
                materia_final = mat["nombre"] if mat else ""
            else:
                mostrar_snack("Selecciona o escribe una materia.", ft.Colors.RED_700)
                return
            try:
                did = db.crear_docente(
                    nombre=nombre, ci=ci, materia=materia_final,
                    telefono=txt_telefono_docente.value.strip()
                )
                db.marcar_setup_completado(did, nombre, materia_final)
                mostrar_snack(f"¡Bienvenido(a), {nombre}!")
                iniciar_app_principal()
            except Exception as ex:
                mostrar_snack(f"Error al registrar: {ex}", ft.Colors.RED_700)

        vista_setup = ft.Container(
            padding=25, expand=True,
            gradient=ft.LinearGradient(
                colors=[ft.Colors.INDIGO_50, ft.Colors.WHITE],
                begin=ft.Alignment.TOP_CENTER, end=ft.Alignment.BOTTOM_CENTER
            ),
            content=ft.Column([
                ft.Container(height=15),
                ft.Icon(ft.Icons.SCHOOL, size=70, color=ft.Colors.INDIGO_700),
                ft.Text("Bienvenido al Sistema", size=22, weight=ft.FontWeight.BOLD,
                        color=ft.Colors.INDIGO_900, text_align=ft.TextAlign.CENTER),
                ft.Text("Control de Asistencia Escolar - Nivel Secundaria",
                        size=12, color=ft.Colors.GREY_700, text_align=ft.TextAlign.CENTER),
                ft.Container(height=12),
                ft.Card(
                    elevation=4,
                    content=ft.Container(
                        padding=20,
                        content=ft.Column([
                            ft.Row([
                                ft.Icon(ft.Icons.PERSON_ADD, color=ft.Colors.INDIGO_700),
                                ft.Text("Registrar Docente", size=17, weight=ft.FontWeight.BOLD),
                            ]),
                            ft.Divider(),
                            txt_docente_nombre,
                            txt_docente_ci,
                            dropdown_materia,
                            ft.Text("O crea una nueva materia:", size=11, italic=True, color=ft.Colors.GREY_600),
                            txt_materia_nueva,
                            ft.Divider(height=8),
                            txt_telefono_docente,
                            ft.Container(height=8),
                            ft.Button(content="Registrar y Entrar", icon=ft.Icons.LOGIN,
                                       on_click=registrar_docente_setup, width=350),
                        ], spacing=8)
                    )
                )
            ], scroll=ft.ScrollMode.AUTO, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        )
        page.controls.clear()
        page.navigation_bar = None
        page.appbar = None
        page.add(vista_setup)
        page.update()

    def iniciar_app_principal():
        page.controls.clear()
        estado_app = {
            "fecha_seleccionada": datetime.date.today().strftime("%Y-%m-%d"),
            "curso_id_seleccionado": None,
            "config": db.obtener_configuracion()
        }
        todos_los_cursos = list(extra.obtener_cursos_extendido())
        cfg_inicio = db.obtener_configuracion()
        colegio_activo = cfg_inicio.get("colegio_actual_id")
        ids_activos_txt = cfg_inicio.get("cursos_activos_ids", "") or ""
        ids_activos = {int(x) for x in ids_activos_txt.split(",") if x.strip().isdigit()}
        if ids_activos:
            cursos_lista = [c for c in todos_los_cursos if c["id"] in ids_activos]
        else:
            cursos_lista = [c for c in todos_los_cursos
                            if not colegio_activo or str(c["colegio_id"] or "") == str(colegio_activo)]
        if not cursos_lista and colegio_activo:
            cursos_lista = [c for c in todos_los_cursos
                            if str(c["colegio_id"] or "") == str(colegio_activo)]
        if not cursos_lista:
            cursos_lista = list(db.obtener_cursos())
        if cursos_lista:
            estado_app["curso_id_seleccionado"] = cursos_lista[0]["id"]

        def abrir_whatsapp_estudiante(nombre_alumno, nombre_tutor, telefono, asistencia_id):
            cfg = db.obtener_configuracion()
            mensaje = wa.formatear_mensaje_ausencia(
                plantilla=cfg.get("mensaje_whatsapp", ""),
                tutor=nombre_tutor, estudiante=nombre_alumno,
                fecha=estado_app["fecha_seleccionada"],
                institucion=cfg.get("institucion", "Colegio")
            )
            enlace = wa.generar_enlace_whatsapp(
                telefono=telefono, mensaje=mensaje,
                codigo_pais=cfg.get("codigo_pais", "+591")
            )
            db.marcar_whatsapp_notificado(asistencia_id)

            async def lanzar_url():
                try:
                    await url_launcher.launch_url(enlace)
                    mostrar_snack(f"Abriendo WhatsApp para {nombre_tutor}...")
                except Exception as ex:
                    mostrar_snack(f"No se pudo abrir WhatsApp: {ex}", ft.Colors.RED_700)
                recargar_pase_lista()
            page.run_task(lanzar_url)

        def confirmar_alerta_ausencia(nombre_alumno, nombre_tutor, telefono, asistencia_id):
            def confirmar(e):
                page.pop_dialog()
                page.update()
                abrir_whatsapp_estudiante(nombre_alumno, nombre_tutor, telefono, asistencia_id)

            def cancelar(e):
                page.pop_dialog()
                page.update()

            dialogo = ft.AlertDialog(
                modal=True,
                title=ft.Row([
                    ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=ft.Colors.ORANGE_800),
                    ft.Text("Inasistencia Registrada", weight=ft.FontWeight.BOLD, size=18)
                ]),
                content=ft.Column([
                    ft.Text("¿Desea enviar notificación inmediata a WhatsApp del tutor?"),
                    ft.Container(height=8),
                    ft.Text(f"Estudiante: {nombre_alumno}", weight=ft.FontWeight.W_600),
                    ft.Text(f"Tutor: {nombre_tutor} ({telefono})", color=ft.Colors.GREY_700),
                ], tight=True),
                actions=[
                    ft.TextButton("Omitir", on_click=cancelar),
                    ft.Button(content="Enviar WhatsApp", icon=ft.Icons.SEND,
                              bgcolor=ft.Colors.GREEN_600, color=ft.Colors.WHITE,
                              on_click=confirmar),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            page.show_dialog(dialogo)
            page.update()

        lista_alumnos_col = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=10, expand=True)
        resumen_dia_row = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_AROUND,
            vertical_alignment=ft.CrossAxisAlignment.START,
            wrap=False
        )
        txt_busqueda_asistencia = ft.TextField(
            hint_text="Buscar por nombre o CI...", dense=True,
            prefix_icon=ft.Icons.SEARCH,
            on_change=lambda e: recargar_pase_lista()
        )
        dropdown_cursos = ft.Dropdown(
            label="Curso / Grado", dense=True,
            options=[ft.dropdown.Option(str(c["id"]), f"{c['nombre']} {c['seccion'] or ''}".strip())
                     for c in cursos_lista],
            value=str(estado_app["curso_id_seleccionado"]) if estado_app["curso_id_seleccionado"] else None,
            expand=True
        )
        txt_fecha = ft.TextField(label="Fecha", value=estado_app["fecha_seleccionada"],
                                  read_only=True, dense=True, width=130)

        def cambiar_fecha(e):
            if date_picker.value:
                fecha_str = date_picker.value.strftime("%Y-%m-%d")
                txt_fecha.value = fecha_str
                estado_app["fecha_seleccionada"] = fecha_str
                recargar_pase_lista()

        date_picker = ft.DatePicker(
            first_date=datetime.datetime(2024, 1, 1),
            last_date=datetime.datetime(2030, 12, 31),
            on_change=cambiar_fecha
        )
        page.overlay.append(date_picker)
        btn_calendario = ft.IconButton(icon=ft.Icons.CALENDAR_MONTH, tooltip="Cambiar Fecha",
                                       on_click=lambda e: (setattr(date_picker, "open", True), page.update()))

        def cambiar_curso(e):
            if dropdown_cursos.value:
                estado_app["curso_id_seleccionado"] = int(dropdown_cursos.value)
                recargar_pase_lista()

        dropdown_cursos.on_change = cambiar_curso

        def cambiar_estado_asistencia(asistencia_id, nuevo_estado, alumno_nombre, tutor, tel):
            db.actualizar_estado_asistencia(asistencia_id, nuevo_estado)
            recargar_pase_lista()
            if nuevo_estado == "AUSENTE":
                confirmar_alerta_ausencia(alumno_nombre, tutor, tel, asistencia_id)
            else:
                mostrar_snack(f"{alumno_nombre} marcado como {nuevo_estado}")

        def recargar_pase_lista():
            lista_alumnos_col.controls.clear()
            curso_id = estado_app["curso_id_seleccionado"]
            fecha = estado_app["fecha_seleccionada"]
            filtro = txt_busqueda_asistencia.value or ""
            if not curso_id:
                lista_alumnos_col.controls.append(
                    ft.Container(content=ft.Text("Por favor, crea o selecciona un curso.", italic=True),
                                 alignment=ft.Alignment.CENTER, padding=20))
                page.update()
                return
            registros = db.cargar_o_iniciar_asistencia_dia(curso_id, fecha)
            resumen = reports.obtener_resumen_dia(curso_id, fecha)
            resumen_dia_row.controls = [
                ft.Card(content=ft.Container(content=ft.Column([
                    ft.Text("Presentes", size=12, color=ft.Colors.GREEN_800, weight=ft.FontWeight.BOLD),
                    ft.Text(f"{resumen['presentes']}", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_900)
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2), padding=10, width=85), bgcolor=ft.Colors.GREEN_50),
                ft.Card(content=ft.Container(content=ft.Column([
                    ft.Text("Ausentes", size=12, color=ft.Colors.RED_800, weight=ft.FontWeight.BOLD),
                    ft.Text(f"{resumen['ausentes']}", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_900)
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2), padding=10, width=85), bgcolor=ft.Colors.RED_50),
                ft.Card(content=ft.Container(content=ft.Column([
                    ft.Text("Permisos", size=12, color=ft.Colors.BLUE_800, weight=ft.FontWeight.BOLD),
                    ft.Text(f"{resumen['permisos']}", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900)
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2), padding=10, width=85), bgcolor=ft.Colors.BLUE_50),
                ft.Card(content=ft.Container(content=ft.Column([
                    ft.Text("% Asist.", size=12, color=ft.Colors.PURPLE_800, weight=ft.FontWeight.BOLD),
                    ft.Text(f"{resumen['porcentaje_asistencia']}%", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.PURPLE_900)
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2), padding=10, width=85), bgcolor=ft.Colors.PURPLE_50),
            ]
            if filtro.strip():
                f = filtro.strip().lower()
                registros = [r for r in registros
                             if f in r["nombre_completo"].lower()
                             or f in (r.get("ci") or "").lower()
                             or f in r["tutor_nombre"].lower()
                             or f in (r.get("tutor_ci") or "").lower()]
            for r in registros:
                aid = r["asistencia_id"]; nom = r["nombre_completo"]
                tut = r["tutor_nombre"]; tel = r["tutor_telefono"]
                est = r["estado"]; obs = r["observacion"] or ""
                ci = r.get("ci", "") or ""; tut_ci = r.get("tutor_ci", "") or ""
                icono_estado = ft.Icons.CHECK_CIRCLE
                color_icono = ft.Colors.GREEN_600
                if est == "AUSENTE":
                    icono_estado = ft.Icons.CANCEL; color_icono = ft.Colors.RED_600
                elif est == "PERMISO":
                    icono_estado = ft.Icons.ASSIGNMENT_TURNED_IN; color_icono = ft.Colors.BLUE_600
                elif est == "ATRASO":
                    icono_estado = ft.Icons.ACCESS_TIME_FILLED; color_icono = ft.Colors.ORANGE_600
                btn_presente = ft.IconButton(
                    icon=ft.Icons.CHECK,
                    icon_color=ft.Colors.WHITE if est == "PRESENTE" else ft.Colors.GREEN_700,
                    bgcolor=ft.Colors.GREEN_600 if est == "PRESENTE" else ft.Colors.GREY_200,
                    icon_size=18, tooltip="Marcar Presente",
                    on_click=lambda e, a=aid, n=nom, t=tut, p=tel: cambiar_estado_asistencia(a, "PRESENTE", n, t, p))
                btn_ausente = ft.IconButton(
                    icon=ft.Icons.CLOSE,
                    icon_color=ft.Colors.WHITE if est == "AUSENTE" else ft.Colors.RED_700,
                    bgcolor=ft.Colors.RED_600 if est == "AUSENTE" else ft.Colors.GREY_200,
                    icon_size=18, tooltip="Marcar Falta / Ausente",
                    on_click=lambda e, a=aid, n=nom, t=tut, p=tel: cambiar_estado_asistencia(a, "AUSENTE", n, t, p))
                btn_permiso = ft.IconButton(
                    icon=ft.Icons.NOTE_ALT_OUTLINED,
                    icon_color=ft.Colors.WHITE if est == "PERMISO" else ft.Colors.BLUE_700,
                    bgcolor=ft.Colors.BLUE_600 if est == "PERMISO" else ft.Colors.GREY_200,
                    icon_size=18, tooltip="Marcar Permiso Justificado",
                    on_click=lambda e, a=aid, n=nom, t=tut, p=tel: cambiar_estado_asistencia(a, "PERMISO", n, t, p))
                btn_atraso = ft.IconButton(
                    icon=ft.Icons.SCHEDULE,
                    icon_color=ft.Colors.WHITE if est == "ATRASO" else ft.Colors.ORANGE_700,
                    bgcolor=ft.Colors.ORANGE_600 if est == "ATRASO" else ft.Colors.GREY_200,
                    icon_size=18, tooltip="Marcar Atraso",
                    on_click=lambda e, a=aid, n=nom, t=tut, p=tel: cambiar_estado_asistencia(a, "ATRASO", n, t, p))
                btn_wa = ft.IconButton(
                    icon=ft.Icons.CHAT, icon_color=ft.Colors.GREEN_700, tooltip="Notificar por WhatsApp",
                    on_click=lambda e, n=nom, t=tut, p=tel, a=aid: abrir_whatsapp_estudiante(n, t, p, a))
                fila_card = ft.Card(
                    elevation=2, shape=ft.RoundedRectangleBorder(radius=12),
                    content=ft.Container(
                        padding=10,
                        content=ft.Column([
                            ft.Row([
                                ft.Icon(icono_estado, color=color_icono, size=20),
                                ft.Container(
                                    content=ft.Column([
                                        ft.Text(nom, weight=ft.FontWeight.BOLD, size=15, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                        ft.Text(f"CI: {ci or '—'}", size=11, color=ft.Colors.GREY_600),
                                        ft.Text(f"Tutor: {tut} (CI: {tut_ci or '—'})", size=12, color=ft.Colors.GREY_600, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                        ft.Text(f"Tel: +591 {tel}", size=12, color=ft.Colors.GREY_600),
                                        ft.Text(f"Nota: {obs}", size=11, italic=True, color=ft.Colors.BLUE_GREY_700, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS) if obs else ft.Container()
                                    ], spacing=1), expand=True),
                                btn_wa
                            ]),
                            ft.Divider(height=1, color=ft.Colors.GREY_200),
                            ft.Row([
                                ft.Text(f"Estado: {est}", size=12, weight=ft.FontWeight.W_600, color=color_icono),
                                ft.Row([btn_presente, btn_ausente, btn_permiso, btn_atraso], spacing=6)
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                        ], spacing=6)
                    )
                )
                lista_alumnos_col.controls.append(fila_card)
            page.update()

        def notificar_todos_los_ausentes(e):
            curso_id = estado_app["curso_id_seleccionado"]
            fecha = estado_app["fecha_seleccionada"]
            registros = db.cargar_o_iniciar_asistencia_dia(curso_id, fecha)
            ausentes = [r for r in registros if r["estado"] == "AUSENTE"]
            if not ausentes:
                mostrar_snack("¡Excelente! No hay alumnos ausentes en esta fecha.")
                return

            def abrir_siguiente(index=0):
                if index >= len(ausentes):
                    mostrar_snack("Notificaciones de ausencias completadas.")
                    recargar_pase_lista()
                    return
                r = ausentes[index]
                abrir_whatsapp_estudiante(r["nombre_completo"], r["tutor_nombre"],
                                          r["tutor_telefono"], r["asistencia_id"])
            abrir_siguiente(0)

        btn_notificar_ausentes_masivo = ft.Button(
            content="Avisar Ausencias por WhatsApp", icon=ft.Icons.SEND,
            bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE,
            on_click=notificar_todos_los_ausentes)

        vista_asistencia = ft.Container(
            padding=12, expand=True,
            content=ft.Column([
                ft.Row([dropdown_cursos, txt_fecha, btn_calendario]),
                ft.Container(content=txt_busqueda_asistencia, padding=ft.Padding(left=0, top=0, right=0, bottom=2)),
                ft.Container(content=resumen_dia_row, padding=ft.Padding(left=0, top=0, right=0, bottom=5)),
                ft.Row([ft.Text("Pase de Lista (Por defecto: Todos Asistieron)",
                                size=12, italic=True, color=ft.Colors.GREY_700)],
                       alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                lista_alumnos_col,
                ft.Container(content=btn_notificar_ausentes_masivo, alignment=ft.Alignment.CENTER, padding=5)
            ], expand=True, spacing=6, horizontal_alignment=ft.CrossAxisAlignment.START))

        txt_nuevo_estudiante = ft.TextField(label="Nombre del Estudiante", dense=True)
        txt_ci_estudiante = ft.TextField(label="CI del Estudiante", dense=True)
        txt_nuevo_tutor = ft.TextField(label="Nombre del Padre o Tutor", dense=True)
        txt_ci_tutor = ft.TextField(label="CI del Tutor", dense=True)
        txt_nuevo_telefono = ft.TextField(label="WhatsApp / Celular del Tutor",
                                           prefix=ft.Text("+591 "), dense=True,
                                           keyboard_type=ft.KeyboardType.PHONE)
        dropdown_curso_estudiante = ft.Dropdown(
            label="Asignar al Curso", dense=True,
            options=[ft.dropdown.Option(str(c["id"]), c["nombre"]) for c in cursos_lista])
        txt_busqueda_estudiantes = ft.TextField(
            hint_text="Buscar por nombre o CI...", dense=True,
            prefix_icon=ft.Icons.SEARCH,
            on_change=lambda e: recargar_lista_estudiantes_admin())
        mostrar_inactivos_est = {"valor": False}

        def guardar_estudiante(e):
            if not txt_nuevo_estudiante.value or not txt_nuevo_tutor.value or not txt_nuevo_telefono.value or not dropdown_curso_estudiante.value:
                mostrar_snack("Completa nombre, tutor y teléfono.", ft.Colors.RED_700)
                return
            try:
                db.crear_estudiante(
                    curso_id=int(dropdown_curso_estudiante.value),
                    nombre=txt_nuevo_estudiante.value,
                    ci=txt_ci_estudiante.value,
                    tutor=txt_nuevo_tutor.value,
                    tutor_ci=txt_ci_tutor.value,
                    telefono=txt_nuevo_telefono.value)
                txt_nuevo_estudiante.value = ""; txt_ci_estudiante.value = ""
                txt_nuevo_tutor.value = ""; txt_ci_tutor.value = ""; txt_nuevo_telefono.value = ""
                mostrar_snack("¡Estudiante guardado!")
                recargar_pase_lista()
                recargar_lista_estudiantes_admin()
            except Exception as ex:
                mostrar_snack(f"Error: {ex}", ft.Colors.RED_700)

        lista_estudiantes_admin_col = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)

        def recargar_lista_estudiantes_admin():
            lista_estudiantes_admin_col.controls.clear()
            filtro = txt_busqueda_estudiantes.value or ""
            alumnos = db.buscar_estudiantes(
                estado_app["curso_id_seleccionado"], filtro,
                incluir_inactivos=mostrar_inactivos_est["valor"])

            for al in alumnos:
                eid = al["id"]
                inactivo = (al["activo"] == 0) if "activo" in al.keys() else False

                def editar(e, a=al):
                    dialogo_editar(
                        "Editar Estudiante",
                        [
                            ("Nombre completo", a["nombre_completo"], "nombre"),
                            ("CI", a["ci"], "ci"),
                            ("Tutor / Apoderado", a["tutor_nombre"], "tutor"),
                            ("CI del Tutor", a["tutor_ci"], "tutor_ci"),
                            ("WhatsApp del Tutor", a["tutor_telefono"], "telefono"),
                        ],
                        lambda d: (
                            db.actualizar_estudiante(
                                a["id"], a["curso_id"], d["nombre"], d["ci"],
                                d["tutor"], d["tutor_ci"], d["telefono"]),
                            recargar_lista_estudiantes_admin(),
                            recargar_pase_lista()
                        ) and None
                    )

                def eliminar(e, i=eid, n=al["nombre_completo"]):
                    def confirmar():
                        db.eliminar_estudiante(i)
                        mostrar_snack(f"Estudiante '{n}' desactivado (eliminación lógica).")
                        recargar_lista_estudiantes_admin()
                        recargar_pase_lista()
                    dialogo_confirmar_eliminar(n, confirmar, es_reactivar=False)

                def reactivar(e, i=eid, n=al["nombre_completo"]):
                    def confirmar():
                        db.reactivar_estudiante(i)
                        mostrar_snack(f"Estudiante '{n}' reactivado.")
                        recargar_lista_estudiantes_admin()
                        recargar_pase_lista()
                    dialogo_confirmar_eliminar(n, confirmar, es_reactivar=True)

                acciones = ft.Row([
                    ft.IconButton(ft.Icons.EDIT, icon_color=ft.Colors.INDIGO_600,
                                  tooltip="Editar", on_click=editar),
                    ft.IconButton(
                        ft.Icons.RESTORE if inactivo else ft.Icons.DELETE_OUTLINE,
                        icon_color=ft.Colors.GREEN_600 if inactivo else ft.Colors.RED_400,
                        tooltip="Reactivar" if inactivo else "Desactivar (eliminación lógica)",
                        on_click=reactivar if inactivo else eliminar),
                ], spacing=0)

                lista_estudiantes_admin_col.controls.append(
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.PERSON_OFF if inactivo else ft.Icons.PERSON,
                                        color=ft.Colors.GREY_400 if inactivo else None),
                        title=ft.Column([
                            ft.Text(al["nombre_completo"],
                                    weight=ft.FontWeight.BOLD,
                                    color=ft.Colors.GREY_500 if inactivo else None,
                                    max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(
                                f"CI: {al['ci'] or '—'} | Tutor: {al['tutor_nombre']} "
                                f"(CI: {al['tutor_ci'] or '—'}) - Tel: +591 {al['tutor_telefono']}",
                                size=11, color=ft.Colors.GREY_600,
                                max_lines=2, overflow=ft.TextOverflow.ELLIPSIS)
                        ], spacing=2, expand=True),
                        trailing=ft.Container(
                            content=acciones,
                            width=85
                        ),
                        bgcolor=ft.Colors.GREY_100 if inactivo else None,
                    ))
            page.update()

        switch_inactivos_est = ft.Switch(
            label="Ver inactivos", value=False,
            on_change=lambda e: (mostrar_inactivos_est.update({"valor": e.control.value}),
                                 recargar_lista_estudiantes_admin()))

        vista_estudiantes = ft.Container(
            padding=15, expand=True,
            content=ft.Column([
                ft.Text("Registrar Nuevo Estudiante", size=17, weight=ft.FontWeight.BOLD),
                dropdown_curso_estudiante,
                txt_nuevo_estudiante, txt_ci_estudiante,
                txt_nuevo_tutor, txt_ci_tutor,
                txt_nuevo_telefono,
                ft.Button(content="Guardar Estudiante", icon=ft.Icons.PERSON_ADD,
                          on_click=guardar_estudiante),
                ft.Divider(),
                ft.Row([ft.Text("Alumnos Registrados:", weight=ft.FontWeight.BOLD),
                        switch_inactivos_est],
                       alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                txt_busqueda_estudiantes,
                lista_estudiantes_admin_col
            ], expand=True, spacing=8, scroll=ft.ScrollMode.AUTO))

        dropdown_alumno_permiso = ft.Dropdown(label="Seleccionar Estudiante", dense=True)
        txt_fecha_permiso = ft.TextField(label="Fecha de Permiso (YYYY-MM-DD)",
                                          value=estado_app["fecha_seleccionada"], dense=True)
        txt_motivo_permiso = ft.TextField(label="Motivo (ej. Cita médica, Familiar)",
                                           multiline=True, min_lines=2, dense=True)
        txt_busqueda_permisos = ft.TextField(
            hint_text="Buscar por nombre o CI...", dense=True,
            prefix_icon=ft.Icons.SEARCH,
            on_change=lambda e: recargar_permisos_lista())

        def guardar_permiso(e):
            if not dropdown_alumno_permiso.value or not txt_motivo_permiso.value:
                mostrar_snack("Selecciona el alumno e ingresa el motivo.", ft.Colors.RED_700)
                return
            db.registrar_permiso(int(dropdown_alumno_permiso.value),
                                 txt_fecha_permiso.value.strip(),
                                 txt_motivo_permiso.value.strip())
            txt_motivo_permiso.value = ""
            mostrar_snack("Permiso registrado correctamente.")
            recargar_permisos_lista()
            recargar_pase_lista()

        lista_permisos_col = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)

        def recargar_permisos_lista():
            cid = estado_app["curso_id_seleccionado"]
            if cid:
                alumnos = db.obtener_estudiantes_curso(cid)
                dropdown_alumno_permiso.options = [
                    ft.dropdown.Option(str(a["id"]), f"{a['nombre_completo']} (CI: {a['ci'] or '—'})")
                    for a in alumnos]
            lista_permisos_col.controls.clear()
            permisos = db.obtener_permisos(txt_busqueda_permisos.value or "")
            for p in permisos:
                pid = p["id"]

                def editar_permiso(e, per=p):
                    dialogo_editar(
                        "Editar Permiso",
                        [
                            ("Fecha (YYYY-MM-DD)", per["fecha"], "fecha"),
                            ("Motivo", per["motivo"], "motivo"),
                        ],
                        lambda d: (
                            db.actualizar_permiso(per["id"], d["fecha"], d["motivo"]),
                            recargar_permisos_lista(),
                            recargar_pase_lista()
                        ) and None
                    )

                def eliminar_permiso(e, i=pid, n=p["nombre_completo"]):
                    def confirmar():
                        db.eliminar_permiso(i)
                        mostrar_snack(f"Permiso de '{n}' desactivado.")
                        recargar_permisos_lista()
                        recargar_pase_lista()
                    dialogo_confirmar_eliminar(f"permiso de {n}", confirmar, es_reactivar=False)

                lista_permisos_col.controls.append(
                    ft.Card(content=ft.Container(padding=10, content=ft.Column([
                        ft.Row([
                            ft.Icon(ft.Icons.EVENT_AVAILABLE, color=ft.Colors.BLUE_700),
                            ft.Text(p["nombre_completo"], weight=ft.FontWeight.BOLD, expand=True, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(p["fecha"], size=12, color=ft.Colors.GREY_600),
                            ft.IconButton(ft.Icons.EDIT, icon_size=18,
                                          icon_color=ft.Colors.INDIGO_600,
                                          tooltip="Editar", on_click=editar_permiso),
                            ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_size=18,
                                          icon_color=ft.Colors.RED_400,
                                          tooltip="Desactivar", on_click=eliminar_permiso),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Text(f"CI: {p['ci'] or '—'}", size=11, color=ft.Colors.GREY_600),
                        ft.Text(f"Motivo: {p['motivo']}", italic=True, size=13),
                        ft.Text(f"Curso: {p['curso_nombre']}", size=11, color=ft.Colors.BLUE_GREY)
                    ], spacing=3))))
            page.update()

        vista_permisos = ft.Container(
            padding=15, expand=True,
            content=ft.Column([
                ft.Text("Registrar Justificación / Permiso Previo", size=17, weight=ft.FontWeight.BOLD),
                dropdown_alumno_permiso, txt_fecha_permiso, txt_motivo_permiso,
                ft.Button(content="Registrar Permiso", icon=ft.Icons.CHECK_BOX, on_click=guardar_permiso),
                ft.Divider(),
                ft.Text("Historial de Permisos Registrados:", weight=ft.FontWeight.BOLD),
                txt_busqueda_permisos,
                lista_permisos_col
            ], scroll=ft.ScrollMode.AUTO))

        txt_periodo_mes = ft.TextField(label="Mes (YYYY-MM)",
                                        value=datetime.date.today().strftime("%Y-%m"),
                                        width=140, dense=True)
        txt_busqueda_reportes = ft.TextField(
            hint_text="Buscar por nombre o CI...", dense=True, expand=True,
            prefix_icon=ft.Icons.SEARCH,
            on_change=lambda e: generar_reporte_mensual(None))
        col_reportes_resultados = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)

        def generar_reporte_mensual(e):
            col_reportes_resultados.controls.clear()
            cid = estado_app["curso_id_seleccionado"]
            mes = txt_periodo_mes.value.strip()
            if not cid or not mes:
                mostrar_snack("Verifica el curso y el periodo.")
                return
            datos = reports.obtener_resumen_mensual(cid, mes, txt_busqueda_reportes.value or "")
            if not datos:
                col_reportes_resultados.controls.append(
                    ft.Text("No hay datos de asistencia para este periodo.", italic=True))
                page.update()
                return
            for d in datos:
                color_porc = ft.Colors.GREEN_700 if d["porcentaje"] >= 80 else ft.Colors.RED_700
                alerta_badge = ft.Container(
                    content=ft.Text("EN RIESGO", color=ft.Colors.WHITE, size=10, weight=ft.FontWeight.BOLD),
                    bgcolor=ft.Colors.RED_600, border_radius=5, padding=4) if d["en_riesgo"] else ft.Container()
                item = ft.Card(content=ft.Container(padding=10, content=ft.Column([
                    ft.Row([ft.Text(d["nombre"], weight=ft.FontWeight.BOLD, size=14, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS), alerta_badge],
                           alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Text(f"CI: {d.get('ci','') or '—'}", size=11, color=ft.Colors.GREY_600),
                    ft.Text(f"Presentes: {d['presentes']} | Faltas: {d['ausentes']} | Permisos: {d['permisos']}", size=12),
                    ft.Row([ft.Text("Porcentaje de Asistencia:", size=12),
                            ft.Text(f"{d['porcentaje']}%", weight=ft.FontWeight.BOLD, color=color_porc, size=14)],
                           alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                ], spacing=4)))
                col_reportes_resultados.controls.append(item)
            page.update()

        def exportar_csv(e):
            cid = estado_app["curso_id_seleccionado"]
            mes = txt_periodo_mes.value.strip()
            cursos = db.obtener_cursos()
            curso_actual = next((c for c in cursos if c["id"] == cid), None)
            nombre_c = curso_actual["nombre"] if curso_actual else "Curso"
            datos = reports.obtener_resumen_mensual(cid, mes, txt_busqueda_reportes.value or "")
            if not datos:
                mostrar_snack("No hay datos que exportar.")
                return
            cfg = db.obtener_configuracion()
            ruta = reports.exportar_reporte_csv(
                nombre_c, mes, datos,
                institucion=cfg.get("institucion", "Colegio"),
                docente=cfg.get("docente", "Profesor(a)"),
                materia=cfg.get("materia", "Clase General"),
                nivel=cfg.get("nivel_educativo", "Secundaria"))
            mostrar_snack(f"Reporte exportado: {os.path.basename(ruta)}")

        cfg = estado_app["config"]
        txt_cfg_colegio = ft.TextField(label="Nombre de la Institución",
                                        value=cfg.get("institucion", ""), dense=True)
        txt_cfg_prefijo = ft.TextField(label="Código de País WhatsApp",
                                        value=cfg.get("codigo_pais", "+591"), dense=True)
        txt_cfg_mensaje = ft.TextField(
            label="Mensaje WhatsApp (usa {tutor}, {estudiante}, {fecha}, {institucion})",
            value=cfg.get("mensaje_whatsapp", ""), multiline=True, min_lines=3, dense=True)

        def guardar_ajustes(e):
            db.guardar_configuracion("institucion", txt_cfg_colegio.value.strip())
            db.guardar_configuracion("codigo_pais", txt_cfg_prefijo.value.strip())
            db.guardar_configuracion("mensaje_whatsapp", txt_cfg_mensaje.value.strip())
            estado_app["config"] = db.obtener_configuracion()
            mostrar_snack("Configuración guardada.")

        vista_reportes = ft.Container(
            padding=15, expand=True,
            content=ft.Column([
                ft.Text("Reporte de Asistencia por Mes", size=17, weight=ft.FontWeight.BOLD),
                ft.Row([txt_periodo_mes,
                        ft.Button(content="Consultar", icon=ft.Icons.SEARCH, on_click=generar_reporte_mensual),
                        ft.IconButton(icon=ft.Icons.DOWNLOAD, tooltip="Exportar CSV", on_click=exportar_csv)]),
                txt_busqueda_reportes,
                col_reportes_resultados,
                ft.Divider(),
                ft.Text("Configuración de Notificaciones", size=16, weight=ft.FontWeight.BOLD),
                txt_cfg_colegio, txt_cfg_prefijo, txt_cfg_mensaje,
                ft.Button(content="Guardar Configuración", icon=ft.Icons.SAVE, on_click=guardar_ajustes)
            ], scroll=ft.ScrollMode.AUTO))

        txt_doc_nombre = ft.TextField(label="Nombre completo del Docente", dense=True)
        txt_doc_ci = ft.TextField(label="CI del Docente", dense=True)
        txt_doc_materia = ft.TextField(label="Materia que regenta", dense=True)
        txt_doc_telefono = ft.TextField(label="Teléfono (opcional)", prefix=ft.Text("+591 "),
                                         dense=True, keyboard_type=ft.KeyboardType.PHONE)
        txt_doc_email = ft.TextField(label="Email (opcional)", dense=True,
                                      keyboard_type=ft.KeyboardType.EMAIL)
        txt_busqueda_docentes = ft.TextField(
            hint_text="Buscar por nombre, CI o materia...", dense=True,
            prefix_icon=ft.Icons.SEARCH,
            on_change=lambda e: recargar_lista_docentes())
        lista_docentes_col = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)

        def dialogo_asignar_cursos_docente(docente):
            cursos_disponibles = [dict(c) for c in extra.obtener_cursos_extendido()]
            if not cursos_disponibles:
                cursos_disponibles = [dict(c) for c in db.obtener_cursos()]
            if not cursos_disponibles:
                mostrar_snack("No hay cursos registrados para asignar.", ft.Colors.RED_700)
                return

            cursos_asignados = obtener_cursos_de_docente(docente["id"])
            ids_asignados = {c["id"] for c in cursos_asignados}

            checks = []
            for curso in cursos_disponibles:
                checks.append(ft.Checkbox(
                    label=f"{curso['nombre']} {curso.get('seccion') or ''}".strip(),
                    value=curso["id"] in ids_asignados,
                    data=curso["id"]
                ))

            col_checks = ft.Column(checks, spacing=4, tight=True, scroll=ft.ScrollMode.AUTO)

            def guardar_asignaciones(e):
                nuevos_ids = {ch.data for ch in checks if ch.value}
                for c in cursos_asignados:
                    if c["id"] not in nuevos_ids:
                        desasignar_curso_de_docente(docente["id"], c["id"])
                for cid in nuevos_ids:
                    if cid not in ids_asignados:
                        asignar_curso_a_docente(docente["id"], cid)
                page.pop_dialog()
                page.update()
                recargar_lista_docentes()
                mostrar_snack("Asignación de cursos actualizada.")

            dlg = ft.AlertDialog(
                modal=True,
                title=ft.Row([
                    ft.Icon(ft.Icons.ASSIGNMENT, color=ft.Colors.INDIGO_700),
                    ft.Text(f"Cursos de {docente['nombre_completo']}",
                            weight=ft.FontWeight.BOLD, size=16)
                ]),
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("Marca los cursos que este docente impartirá:",
                                size=12, color=ft.Colors.GREY_700),
                        ft.Divider(height=1),
                        col_checks
                    ], spacing=6, tight=True),
                    width=380, padding=10
                ),
                actions=[
                    ft.TextButton("Cancelar", on_click=lambda e: (page.pop_dialog(), page.update())),
                    ft.Button("Guardar", icon=ft.Icons.SAVE, on_click=guardar_asignaciones),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            page.show_dialog(dlg)
            page.update()

        def guardar_docente(e):
            if not txt_doc_nombre.value or not txt_doc_ci.value or not txt_doc_materia.value:
                mostrar_snack("Completa nombre, CI y materia.", ft.Colors.RED_700)
                return
            try:
                db.crear_docente(txt_doc_nombre.value, txt_doc_ci.value,
                                 txt_doc_materia.value, txt_doc_telefono.value, txt_doc_email.value)
                txt_doc_nombre.value = ""; txt_doc_ci.value = ""; txt_doc_materia.value = ""
                txt_doc_telefono.value = ""; txt_doc_email.value = ""
                mostrar_snack("Docente registrado.")
                recargar_lista_docentes()
            except Exception as ex:
                mostrar_snack(f"Error: {ex}", ft.Colors.RED_700)

        def recargar_lista_docentes():
            lista_docentes_col.controls.clear()
            docs = db.obtener_docentes(True, txt_busqueda_docentes.value or "")
            for d in docs:
                did = d["id"]
                cursos_asig = obtener_cursos_de_docente(did)
                if cursos_asig:
                    cursos_txt = ", ".join(
                        [f"{c['nombre']} {c['seccion'] or ''}".strip() for c in cursos_asig]
                    )
                else:
                    cursos_txt = "Sin cursos asignados"

                def asignar_cursos(e, doc=d):
                    dialogo_asignar_cursos_docente(doc)

                def editar(e, doc=d):
                    dialogo_editar(
                        "Editar Docente",
                        [
                            ("Nombre completo", doc["nombre_completo"], "nombre"),
                            ("CI", doc["ci"], "ci"),
                            ("Materia", doc["materia"], "materia"),
                            ("Teléfono", doc["telefono"], "telefono"),
                            ("Email", doc["email"], "email"),
                        ],
                        lambda dat: (
                            db.actualizar_docente(
                                doc["id"], dat["nombre"], dat["ci"], dat["materia"],
                                dat["telefono"], dat["email"]),
                            recargar_lista_docentes()
                        ) and None
                    )

                def eliminar(e, i=did, n=d["nombre_completo"]):
                    def confirmar():
                        db.eliminar_docente(i)
                        mostrar_snack(f"Docente '{n}' desactivado.")
                        recargar_lista_docentes()
                    dialogo_confirmar_eliminar(n, confirmar, es_reactivar=False)

                lista_docentes_col.controls.append(
                    ft.Card(
                        elevation=1,
                        content=ft.Container(
                            padding=10,
                            content=ft.Column([
                                ft.Row([
                                    ft.Icon(ft.Icons.SCHOOL, color=ft.Colors.INDIGO_700),
                                    ft.Column([
                                        ft.Text(d["nombre_completo"], weight=ft.FontWeight.BOLD,
                                                size=15, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                        ft.Text(f"CI: {d['ci'] or '—'}  |  Materia: {d['materia']}",
                                                size=11, color=ft.Colors.GREY_700,
                                                max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                        ft.Text(f"Tel: +591 {d['telefono'] or '—'}",
                                                size=11, color=ft.Colors.GREY_600),
                                    ], spacing=2, expand=True),
                                ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.START),
                                ft.Container(
                                    content=ft.Row([
                                        ft.Icon(ft.Icons.ASSIGNMENT, size=14, color=ft.Colors.INDIGO_600),
                                        ft.Text(f"Cursos: {cursos_txt}", size=11,
                                                color=ft.Colors.INDIGO_800, italic=True,
                                                max_lines=2, overflow=ft.TextOverflow.ELLIPSIS,
                                                expand=True),
                                    ], spacing=4),
                                    padding=ft.Padding(left=4, top=2, bottom=2, right=4),
                                    border=ft.Border(
                                        left=ft.BorderSide(1, ft.Colors.INDIGO_100),
                                        top=ft.BorderSide(1, ft.Colors.INDIGO_100),
                                        right=ft.BorderSide(1, ft.Colors.INDIGO_100),
                                        bottom=ft.BorderSide(1, ft.Colors.INDIGO_100),
                                    ),
                                    border_radius=6,
                                    bgcolor=ft.Colors.INDIGO_50,
                                ),
                                ft.Row([
                                    ft.IconButton(ft.Icons.ASSIGNMENT, icon_color=ft.Colors.BLUE_600,
                                                  tooltip="Asignar / Editar cursos",
                                                  on_click=asignar_cursos),
                                    ft.IconButton(ft.Icons.EDIT, icon_color=ft.Colors.INDIGO_600,
                                                  tooltip="Editar docente", on_click=editar),
                                    ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color=ft.Colors.RED_400,
                                                  tooltip="Desactivar docente", on_click=eliminar),
                                ], alignment=ft.MainAxisAlignment.END, spacing=0)
                            ], spacing=6)
                        )
                    ))
            page.update()

        vista_docentes = ft.Container(
            padding=15, expand=True,
            content=ft.Column([
                ft.Text("Registrar Nuevo Docente", size=17, weight=ft.FontWeight.BOLD),
                txt_doc_nombre, txt_doc_ci, txt_doc_materia, txt_doc_telefono, txt_doc_email,
                ft.Button(content="Guardar Docente", icon=ft.Icons.PERSON_ADD, on_click=guardar_docente),
                ft.Divider(),
                ft.Text("Docentes Registrados:", weight=ft.FontWeight.BOLD),
                txt_busqueda_docentes,
                lista_docentes_col
            ], expand=True, spacing=8, scroll=ft.ScrollMode.AUTO))

        txt_mat_nombre = ft.TextField(label="Nombre de la Materia", dense=True)
        txt_mat_descripcion = ft.TextField(label="Descripción (opcional)", dense=True)
        txt_busqueda_materias = ft.TextField(
            hint_text="Buscar materia...", dense=True, prefix_icon=ft.Icons.SEARCH,
            on_change=lambda e: recargar_lista_materias())
        lista_materias_col = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)

        def guardar_materia(e):
            if not txt_mat_nombre.value.strip():
                mostrar_snack("Escribe el nombre de la materia.", ft.Colors.RED_700)
                return
            try:
                db.crear_materia(txt_mat_nombre.value, "Secundaria", txt_mat_descripcion.value)
                txt_mat_nombre.value = ""; txt_mat_descripcion.value = ""
                mostrar_snack("Materia registrada.")
                recargar_lista_materias()
            except Exception as ex:
                mostrar_snack(f"Error (¿ya existe?): {ex}", ft.Colors.RED_700)

        def recargar_lista_materias():
            lista_materias_col.controls.clear()
            mats = db.obtener_materias(True, txt_busqueda_materias.value or "")
            for m in mats:
                mid = m["id"]

                def editar(e, mat=m):
                    dialogo_editar(
                        "Editar Materia",
                        [
                            ("Nombre", mat["nombre"], "nombre"),
                            ("Nivel", mat["nivel"], "nivel"),
                            ("Descripción", mat["descripcion"], "descripcion"),
                        ],
                        lambda dat: (
                            db.actualizar_materia(
                                mat["id"], dat["nombre"], dat["nivel"], dat["descripcion"]),
                            recargar_lista_materias()
                        ) and None
                    )

                def eliminar(e, i=mid, n=m["nombre"]):
                    def confirmar():
                        db.eliminar_materia(i)
                        mostrar_snack(f"Materia '{n}' desactivada.")
                        recargar_lista_materias()
                    dialogo_confirmar_eliminar(n, confirmar, es_reactivar=False)

                lista_materias_col.controls.append(
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.BOOK),
                        title=ft.Column([
                            ft.Text(m["nombre"], weight=ft.FontWeight.BOLD, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(m["descripcion"] or "—", size=11, color=ft.Colors.GREY_600, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)
                        ], spacing=2, expand=True),
                        trailing=ft.Container(
                            content=ft.Row([
                                ft.IconButton(ft.Icons.EDIT, icon_color=ft.Colors.INDIGO_600,
                                              tooltip="Editar", on_click=editar),
                                ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color=ft.Colors.RED_400,
                                              tooltip="Desactivar", on_click=eliminar),
                            ], spacing=0),
                            width=85
                        )
                    ))
            page.update()

        vista_materias = ft.Container(
            padding=15, expand=True,
            content=ft.Column([
                ft.Text("Registrar Nueva Materia", size=17, weight=ft.FontWeight.BOLD),
                txt_mat_nombre, txt_mat_descripcion,
                ft.Button(content="Guardar Materia", icon=ft.Icons.ADD, on_click=guardar_materia),
                ft.Divider(),
                ft.Text("Materias Registradas:", weight=ft.FontWeight.BOLD),
                txt_busqueda_materias,
                lista_materias_col
            ], expand=True, spacing=8))

        txt_colegio_nombre = ft.TextField(label="Nombre del colegio", dense=True)
        txt_colegio_direccion = ft.TextField(label="Dirección", dense=True)
        txt_colegio_telefono = ft.TextField(label="Teléfono", dense=True)
        txt_turno_nombre = ft.TextField(label="Nombre del turno", dense=True)
        txt_turno_inicio = ft.TextField(label="Hora de inicio (HH:MM)", dense=True)
        txt_turno_fin = ft.TextField(label="Hora de finalización (HH:MM)", dense=True)
        dropdown_colegio_curso = ft.Dropdown(
            label="Colegio", dense=True,
            options=[ft.dropdown.Option(str(x["id"]), x["nombre"]) for x in extra.listar_colegios()]
        )
        dropdown_turno_curso = ft.Dropdown(
            label="Turno", dense=True,
            options=[ft.dropdown.Option(str(x["id"]), x["nombre"]) for x in extra.listar_turnos()]
        )
        dropdown_curso_config = ft.Dropdown(
            label="Curso al que asignar colegio y turno", dense=True,
            options=[ft.dropdown.Option(str(c["id"]), f"{c['nombre']} {c['seccion'] or ''}".strip())
                     for c in cursos_lista]
        )
        estado_archivos = {"csv": None, "restore": None}
        txt_csv_ruta = ft.TextField(label="Archivo CSV seleccionado", read_only=True, dense=True, expand=True)
        dropdown_curso_importacion = ft.Dropdown(
            label="Curso donde importar estudiantes", dense=True,
            options=[ft.dropdown.Option(str(c["id"]), f"{c['nombre']} {c['seccion'] or ''}".strip())
                     for c in cursos_lista]
        )
        txt_backup_ruta = ft.TextField(label="Destino de la copia", read_only=True, dense=True, expand=True)
        txt_restaurar_ruta = ft.TextField(label="Archivo de respaldo seleccionado", read_only=True, dense=True, expand=True)
        lista_colegios_ui = ft.Column(spacing=3)
        lista_turnos_ui = ft.Column(spacing=3)

        def actualizar_opciones_administracion():
            colegios = extra.listar_colegios()
            turnos = extra.listar_turnos()
            dropdown_colegio_curso.options = [ft.dropdown.Option(str(x["id"]), x["nombre"]) for x in colegios]
            dropdown_turno_curso.options = [ft.dropdown.Option(str(x["id"]), x["nombre"]) for x in turnos]

            lista_colegios_ui.controls.clear()
            for colegio in colegios:
                cid_col = colegio["id"]

                def editar_col(e, c=colegio):
                    dialogo_editar(
                        "Editar Colegio",
                        [("Nombre", c["nombre"], "nombre"),
                         ("Dirección", c["direccion"], "direccion"),
                         ("Teléfono", c["telefono"], "telefono")],
                        lambda d: (
                            extra.guardar_colegio(d["nombre"], d["direccion"], d["telefono"],
                                                  colegio_id=c["id"]),
                            actualizar_opciones_administracion()
                        ) and None
                    )

                def eliminar_col(e, i=cid_col, n=colegio["nombre"]):
                    def confirmar():
                        extra.desactivar_colegio(i)
                        mostrar_snack(f"Colegio '{n}' desactivado.")
                        actualizar_opciones_administracion()
                    dialogo_confirmar_eliminar(n, confirmar, es_reactivar=False)

                lista_colegios_ui.controls.append(
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.BUSINESS),
                        title=ft.Column([
                            ft.Text(colegio["nombre"], max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(colegio["direccion"] or "Sin dirección registrada", size=11, color=ft.Colors.GREY_600, max_lines=1)
                        ], spacing=2, expand=True),
                        trailing=ft.Container(
                            content=ft.Row([
                                ft.IconButton(ft.Icons.EDIT, icon_size=18,
                                              icon_color=ft.Colors.INDIGO_600, on_click=editar_col),
                                ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_size=18,
                                              icon_color=ft.Colors.RED_400, on_click=eliminar_col),
                            ], spacing=0),
                            width=80
                        )
                    )
                )

            lista_turnos_ui.controls.clear()
            for turno in turnos:
                tid = turno["id"]

                def editar_tur(e, t=turno):
                    dialogo_editar(
                        "Editar Turno",
                        [("Nombre", t["nombre"], "nombre"),
                         ("Hora inicio", t["hora_inicio"], "hora_inicio"),
                         ("Hora fin", t["hora_fin"], "hora_fin")],
                        lambda d: (
                            extra.guardar_turno(d["nombre"], d["hora_inicio"],
                                                d["hora_fin"], turno_id=t["id"]),
                            actualizar_opciones_administracion()
                        ) and None
                    )

                def eliminar_tur(e, i=tid, n=turno["nombre"]):
                    def confirmar():
                        extra.desactivar_turno(i)
                        mostrar_snack(f"Turno '{n}' desactivado.")
                        actualizar_opciones_administracion()
                    dialogo_confirmar_eliminar(n, confirmar, es_reactivar=False)

                horario = f"{turno['hora_inicio'] or '--:--'} a {turno['hora_fin'] or '--:--'}"
                lista_turnos_ui.controls.append(
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.ACCESS_TIME),
                        title=ft.Column([
                            ft.Text(turno["nombre"], max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(horario, size=11, color=ft.Colors.GREY_600, max_lines=1)
                        ], spacing=2, expand=True),
                        trailing=ft.Container(
                            content=ft.Row([
                                ft.IconButton(ft.Icons.EDIT, icon_size=18,
                                              icon_color=ft.Colors.INDIGO_600, on_click=editar_tur),
                                ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_size=18,
                                              icon_color=ft.Colors.RED_400, on_click=eliminar_tur),
                            ], spacing=0),
                            width=80
                        )
                    )
                )
            page.update()

        def guardar_colegio_ui(e):
            try:
                extra.guardar_colegio(
                    txt_colegio_nombre.value or "",
                    txt_colegio_direccion.value or "",
                    txt_colegio_telefono.value or ""
                )
                txt_colegio_nombre.value = ""
                txt_colegio_direccion.value = ""
                txt_colegio_telefono.value = ""
                actualizar_opciones_administracion()
                mostrar_snack("Colegio registrado correctamente.")
            except Exception as ex:
                mostrar_snack(f"No se pudo guardar el colegio: {ex}", ft.Colors.RED_700)

        def guardar_turno_ui(e):
            try:
                nombre_turno = (txt_turno_nombre.value or "").strip()
                existente = next((t for t in extra.listar_turnos()
                                  if t["nombre"].strip().casefold() == nombre_turno.casefold()), None)
                extra.guardar_turno(
                    nombre_turno, txt_turno_inicio.value or "", txt_turno_fin.value or "",
                    turno_id=existente["id"] if existente else None
                )
                txt_turno_nombre.value = ""
                txt_turno_inicio.value = ""
                txt_turno_fin.value = ""
                actualizar_opciones_administracion()
                mostrar_snack("Turno registrado correctamente.")
            except Exception as ex:
                mostrar_snack(f"No se pudo guardar el turno: {ex}", ft.Colors.RED_700)

        def asignar_colegio_turno_ui(e):
            if not dropdown_curso_config.value:
                mostrar_snack("Selecciona un curso.", ft.Colors.RED_700)
                return
            try:
                extra.asignar_colegio_turno_curso(
                    int(dropdown_curso_config.value),
                    int(dropdown_colegio_curso.value) if dropdown_colegio_curso.value else None,
                    int(dropdown_turno_curso.value) if dropdown_turno_curso.value else None
                )
                mostrar_snack("Colegio y turno asignados al curso.")
            except Exception as ex:
                mostrar_snack(f"No se pudo asignar: {ex}", ft.Colors.RED_700)

        async def seleccionar_csv_ui(e):
            archivos = await file_picker.pick_files(
                dialog_title="Seleccionar archivo CSV de alumnos",
                allow_multiple=False,
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["csv"]
            )
            if archivos:
                estado_archivos["csv"] = archivos[0].path
                txt_csv_ruta.value = archivos[0].name
                page.update()

        async def exportar_plantilla_csv_ui(e):
            ruta = await file_picker.save_file(
                dialog_title="Guardar plantilla CSV",
                file_name="plantilla_estudiantes.csv",
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["csv"]
            )
            if not ruta:
                return
            with open(ruta, "w", newline="", encoding="utf-8-sig") as archivo:
                escritor = csv.writer(archivo)
                escritor.writerow(["nombre_completo", "ci", "tutor_nombre", "tutor_ci", "tutor_telefono"])
                escritor.writerow(["Nombre del estudiante", "", "Nombre del tutor", "", "70000000"])
            mostrar_snack("Plantilla CSV exportada correctamente.")

        def importar_csv_ui(e):
            ruta = estado_archivos.get("csv")
            if not ruta or not dropdown_curso_importacion.value:
                mostrar_snack("Selecciona el archivo CSV y el curso.", ft.Colors.RED_700)
                return
            try:
                resultado = extra.importar_estudiantes_csv(ruta, int(dropdown_curso_importacion.value))
                detalle = (f"Agregados: {resultado['insertados']} | Duplicados: {resultado['duplicados']} | "
                           f"Errores: {len(resultado['errores'])}")
                if resultado["errores"]:
                    print("Errores de importación:\n" + "\n".join(resultado["errores"]))
                mostrar_snack(detalle, ft.Colors.GREEN_700 if not resultado["errores"] else ft.Colors.ORANGE_700)
                recargar_lista_estudiantes_admin()
                recargar_pase_lista()
            except Exception as ex:
                mostrar_snack(f"Error al importar CSV: {ex}", ft.Colors.RED_700)

        async def crear_backup_ui(e):
            nombre = f"backup_asistencia_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            ruta = await file_picker.save_file(
                dialog_title="Guardar copia de seguridad",
                file_name=nombre,
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["db"]
            )
            if not ruta:
                return
            try:
                creada = extra.crear_backup(ruta)
                txt_backup_ruta.value = os.path.basename(creada)
                page.update()
                mostrar_snack(f"Copia creada: {os.path.basename(creada)}")
            except Exception as ex:
                mostrar_snack(f"Error al crear respaldo: {ex}", ft.Colors.RED_700)

        async def seleccionar_backup_ui(e):
            archivos = await file_picker.pick_files(
                dialog_title="Seleccionar copia de seguridad",
                allow_multiple=False,
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["db", "sqlite", "sqlite3"]
            )
            if archivos:
                estado_archivos["restore"] = archivos[0].path
                txt_restaurar_ruta.value = archivos[0].name
                page.update()

        def restaurar_backup_ui(e):
            ruta = estado_archivos.get("restore")
            if not ruta:
                mostrar_snack("Busca y selecciona primero el archivo de respaldo.", ft.Colors.RED_700)
                return
            try:
                preventivo = extra.restaurar_backup(ruta)
                mostrar_snack("Respaldo restaurado. Reinicia la aplicación para actualizar los datos.")
                if preventivo:
                    print(f"Copia preventiva creada: {preventivo}")
            except Exception as ex:
                mostrar_snack(f"No se pudo restaurar: {ex}", ft.Colors.RED_700)

        panel_admin_contenido = ft.Container(expand=True)

        def volver_menu_admin(e=None):
            panel_admin_contenido.content = menu_admin
            page.update()

        def abrir_panel_admin(titulo, contenido):
            panel_admin_contenido.content = ft.Column([
                ft.Row([
                    ft.IconButton(icon=ft.Icons.ARROW_BACK, tooltip="Volver al menú Más",
                                  on_click=volver_menu_admin),
                    ft.Text(titulo, size=18, weight=ft.FontWeight.BOLD, expand=True)
                ]),
                ft.Divider(),
                contenido
            ], expand=True, scroll=ft.ScrollMode.AUTO, spacing=10)
            page.update()

        panel_presentacion = ft.Container(
            padding=15,
            expand=True,
            content=ft.Column([
                ft.Icon(ft.Icons.SCHOOL, size=64, color=ft.Colors.INDIGO_700),
                ft.Text("Asistencia Escolar Móvil", size=21, weight=ft.FontWeight.BOLD,
                        text_align=ft.TextAlign.CENTER),
                ft.Text("Control de asistencia, estudiantes, docentes y reportes en una sola aplicación.",
                        size=13, color=ft.Colors.GREY_700, text_align=ft.TextAlign.CENTER),
                ft.Divider(),
                ft.Text("Desarrollado con Python, Flet y SQLite.", size=12, italic=True,
                        text_align=ft.TextAlign.CENTER),
                ft.Text("Aplicación de gestión escolar.", size=12, color=ft.Colors.GREY_600,
                        text_align=ft.TextAlign.CENTER),
                ft.Container(expand=True),
                ft.Divider(height=1, color=ft.Colors.GREY_300),
                ft.Text("Debeloped by: J_C_CH_Q", size=10, italic=True,
                        color=ft.Colors.INDIGO_700, text_align=ft.TextAlign.CENTER),
                ft.Divider()
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=12)
        )

        panel_colegios = ft.Container(
            padding=10,
            content=ft.Column([
                ft.Text("Registrar colegio", weight=ft.FontWeight.BOLD),
                txt_colegio_nombre, txt_colegio_direccion, txt_colegio_telefono,
                ft.Button(content="Guardar colegio", icon=ft.Icons.ADD_BUSINESS,
                          on_click=guardar_colegio_ui),
                ft.Divider(),
                ft.Text("Colegios registrados", weight=ft.FontWeight.BOLD),
                lista_colegios_ui
            ], spacing=9, scroll=ft.ScrollMode.AUTO)
        )

        panel_turnos = ft.Container(
            padding=10,
            content=ft.Column([
                ft.Text("Registrar turno", weight=ft.FontWeight.BOLD),
                txt_turno_nombre, txt_turno_inicio, txt_turno_fin,
                ft.Button(content="Guardar turno", icon=ft.Icons.ACCESS_TIME,
                          on_click=guardar_turno_ui),
                ft.Divider(),
                ft.Text("Turnos registrados", weight=ft.FontWeight.BOLD),
                lista_turnos_ui
            ], spacing=9, scroll=ft.ScrollMode.AUTO)
        )

        panel_asignacion = ft.Container(
            padding=10,
            content=ft.Column([
                ft.Text("Vincular un colegio y un turno con un curso.",
                        size=13, color=ft.Colors.GREY_700),
                dropdown_curso_config, dropdown_colegio_curso, dropdown_turno_curso,
                ft.Button(content="Asignar al curso", icon=ft.Icons.SAVE,
                          on_click=asignar_colegio_turno_ui)
            ], spacing=12, scroll=ft.ScrollMode.AUTO)
        )

        panel_importacion = ft.Container(
            padding=10,
            content=ft.Column([
                ft.Text("Importación masiva de estudiantes", weight=ft.FontWeight.BOLD, size=16),
                ft.Text("El CSV debe incluir nombre_completo, tutor_nombre y tutor_telefono. "
                        "CI y tutor_ci son opcionales.", size=12, color=ft.Colors.GREY_700),
                dropdown_curso_importacion,
                ft.Row([txt_csv_ruta, ft.IconButton(icon=ft.Icons.FOLDER_OPEN,
                    tooltip="Buscar archivo CSV", on_click=seleccionar_csv_ui)]),
                ft.Button(content="Exportar plantilla CSV", icon=ft.Icons.DOWNLOAD,
                          on_click=exportar_plantilla_csv_ui),
                ft.Button(content="Importar estudiantes CSV",
                          icon=ft.Icons.UPLOAD_FILE, on_click=importar_csv_ui)
            ], spacing=12, scroll=ft.ScrollMode.AUTO)
        )

        panel_respaldos = ft.Container(
            padding=10,
            content=ft.Column([
                ft.Text("Crear copia de seguridad", weight=ft.FontWeight.BOLD),
                txt_backup_ruta,
                ft.Button(content="Elegir ubicación y crear copia",
                          icon=ft.Icons.FOLDER_OPEN, on_click=crear_backup_ui),
                ft.Divider(),
                ft.Text("Restaurar copia de seguridad", weight=ft.FontWeight.BOLD),
                txt_restaurar_ruta,
                ft.Button(content="Buscar archivo de respaldo",
                          icon=ft.Icons.FOLDER_OPEN, on_click=seleccionar_backup_ui),
                ft.Button(content="Restaurar copia de seguridad", icon=ft.Icons.RESTORE,
                          bgcolor=ft.Colors.ORANGE_700, color=ft.Colors.WHITE,
                          on_click=restaurar_backup_ui),
                ft.Text("Antes de restaurar, cierra otras operaciones que utilicen la base de datos. "
                        "La aplicación crea una copia preventiva.",
                        size=11, color=ft.Colors.RED_700)
            ], spacing=12, scroll=ft.ScrollMode.AUTO)
        )

        def crear_acceso_admin(icono, titulo, descripcion, contenido):
            return ft.Card(
                elevation=1,
                content=ft.ListTile(
                    leading=ft.Icon(icono, color=ft.Colors.INDIGO_700, size=27),
                    title=ft.Text(titulo, weight=ft.FontWeight.BOLD),
                    subtitle=ft.Text(descripcion, size=11),
                    trailing=ft.Icon(ft.Icons.CHEVRON_RIGHT),
                    on_click=lambda e: abrir_panel_admin(titulo, contenido)
                )
            )

        menu_admin = ft.Column([
            ft.Card(content=ft.Container(
                padding=15,
                content=ft.Row([
                    ft.Icon(ft.Icons.ADMIN_PANEL_SETTINGS, color=ft.Colors.INDIGO_700, size=32),
                    ft.Column([
                        ft.Text("Administración", size=19, weight=ft.FontWeight.BOLD),
                        ft.Text("Selecciona el panel que deseas abrir.", size=12, color=ft.Colors.GREY_700)
                    ], spacing=3, expand=True)
                ])
            )),
            crear_acceso_admin(ft.Icons.SWAP_HORIZ, "Cambiar colegio/cursos",
                               "Volver al selector de colegio y cursos.",
                               ft.Container(
                                   padding=15,
                                   content=ft.Column([
                                       ft.Text("¿Deseas cambiar el colegio o los cursos activos?", size=14),
                                       ft.Container(height=10),
                                       ft.Button("Sí, cambiar ahora", icon=ft.Icons.SWAP_HORIZ,
                                                 on_click=lambda e: mostrar_selector_colegio())
                                   ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
                               )),
            crear_acceso_admin(ft.Icons.BUSINESS, "Colegios",
                               "Registrar y consultar colegios.", panel_colegios),
            crear_acceso_admin(ft.Icons.ACCESS_TIME, "Turnos",
                               "Registrar horarios y turnos.", panel_turnos),
            crear_acceso_admin(ft.Icons.ASSIGNMENT, "Asignación de cursos",
                               "Asignar colegio y turno a cada curso.", panel_asignacion),
            crear_acceso_admin(ft.Icons.UPLOAD_FILE, "Importar alumnos",
                               "Cargar estudiantes desde un archivo CSV.", panel_importacion),
            crear_acceso_admin(ft.Icons.BACKUP, "Copias de seguridad",
                               "Crear o restaurar respaldos de la base de datos.", panel_respaldos),
            crear_acceso_admin(ft.Icons.INFO_OUTLINE, "Presentación",
                                 "Información general de la aplicación.", panel_presentacion),
        ], spacing=8, scroll=ft.ScrollMode.AUTO)

        panel_admin_contenido.content = menu_admin
        vista_mas = ft.Container(padding=12, expand=True, content=panel_admin_contenido)

        contenedor_vistas = ft.Container(content=vista_asistencia, expand=True)

        def cambiar_tab(e):
            idx = e.control.selected_index
            if idx == 0:
                contenedor_vistas.content = vista_asistencia; recargar_pase_lista()
            elif idx == 1:
                contenedor_vistas.content = vista_estudiantes; recargar_lista_estudiantes_admin()
            elif idx == 2:
                contenedor_vistas.content = vista_permisos; recargar_permisos_lista()
            elif idx == 3:
                contenedor_vistas.content = vista_reportes; generar_reporte_mensual(None)
            elif idx == 4:
                contenedor_vistas.content = vista_docentes; recargar_lista_docentes()
            elif idx == 5:
                contenedor_vistas.content = vista_materias; recargar_lista_materias()
            elif idx == 6:
                contenedor_vistas.content = vista_mas
                actualizar_opciones_administracion()
            page.update()

        barra_navegacion = ft.NavigationBar(
            destinations=[
                ft.NavigationBarDestination(icon=ft.Icons.FACT_CHECK_OUTLINED, selected_icon=ft.Icons.FACT_CHECK, label="Lista"),
                ft.NavigationBarDestination(icon=ft.Icons.PEOPLE_OUTLINE, selected_icon=ft.Icons.PEOPLE, label="Estudiantes"),
                ft.NavigationBarDestination(icon=ft.Icons.ASSIGNMENT_OUTLINED, selected_icon=ft.Icons.ASSIGNMENT, label="Permisos"),
                ft.NavigationBarDestination(icon=ft.Icons.ANALYTICS_OUTLINED, selected_icon=ft.Icons.ANALYTICS, label="Reportes"),
                ft.NavigationBarDestination(icon=ft.Icons.SCHOOL_OUTLINED, selected_icon=ft.Icons.SCHOOL, label="Docentes"),
                ft.NavigationBarDestination(icon=ft.Icons.BOOK_OUTLINED, selected_icon=ft.Icons.BOOK, label="Materias"),
                ft.NavigationBarDestination(icon=ft.Icons.MORE_HORIZ, selected_icon=ft.Icons.MORE, label="Más"),
            ],
            on_change=cambiar_tab, selected_index=0)

        def accion_actualizar(e):
            idx = barra_navegacion.selected_index
            if idx == 0:
                recargar_pase_lista()
            elif idx == 1:
                recargar_lista_estudiantes_admin()
            elif idx == 2:
                recargar_permisos_lista()
            elif idx == 3:
                generar_reporte_mensual(None)
            elif idx == 4:
                recargar_lista_docentes()
            elif idx == 5:
                recargar_lista_materias()
            elif idx == 6:
                actualizar_opciones_administracion()
            mostrar_snack("Actualizado ✓")

        page.appbar = ft.AppBar(
            leading=ft.Icon(ft.Icons.SCHOOL, color=ft.Colors.WHITE),
            title=ft.Text("Asistencia Escolar", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
            center_title=False, bgcolor=ft.Colors.INDIGO_700,
            actions=[
                ft.IconButton(ft.Icons.SWAP_HORIZ, icon_color=ft.Colors.WHITE,
                              tooltip="Cambiar colegio/cursos",
                              on_click=lambda e: mostrar_selector_colegio()),
                ft.IconButton(ft.Icons.REFRESH, icon_color=ft.Colors.WHITE,
                              tooltip="Actualizar",
                              on_click=accion_actualizar)])
        page.navigation_bar = barra_navegacion
        page.add(contenedor_vistas)
        recargar_pase_lista()

    mostrar_presentacion()


if __name__ == "__main__":
    ft.run(main)