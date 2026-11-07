import flet as ft
import datetime
import os
import database as db
import whatsapp_helper as wa
import reports


def main(page: ft.Page):
    page.title = "Control de Asistencia Docente - Secundaria"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    page.window.width = 412
    page.window.height = 840
    page.window.resizable = True

    db.init_db()
    url_launcher = ft.UrlLauncher()

    def mostrar_snack(mensaje: str, color=ft.Colors.GREEN_700):
        snack = ft.SnackBar(
            content=ft.Text(mensaje, color=ft.Colors.WHITE, weight=ft.FontWeight.W_500),
            bgcolor=color, duration=3500
        )
        page.overlay.append(snack)
        snack.open = True
        page.update()

    # =========================================================================
    # PANTALLA DE REGISTRO INICIAL DEL DOCENTE
    # =========================================================================
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

    # =========================================================================
    # APP PRINCIPAL
    # =========================================================================
    def iniciar_app_principal():
        page.controls.clear()

        estado_app = {
            "fecha_seleccionada": datetime.date.today().strftime("%Y-%m-%d"),
            "curso_id_seleccionado": None,
            "config": db.obtener_configuracion()
        }

        cursos_lista = list(db.obtener_cursos())
        if cursos_lista:
            estado_app["curso_id_seleccionado"] = cursos_lista[0]["id"]

        # ---------- WHATSAPP ----------
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

        # =====================================================================
        # VISTA 1: PASE DE LISTA (con búsqueda por nombre/CI)
        # =====================================================================
        lista_alumnos_col = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=10, expand=True)
        resumen_dia_row = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_AROUND,
            vertical_alignment=ft.CrossAxisAlignment.START, # <-- Fuerza a pegarse arriba
            wrap=False
        )
        
        txt_busqueda_asistencia = ft.TextField(
            hint_text="Buscar por nombre o CI...", dense=True, #expand=True,
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

            # Aplicar filtro de búsqueda
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

                color_borde = ft.Colors.GREEN_400
                icono_estado = ft.Icons.CHECK_CIRCLE
                color_icono = ft.Colors.GREEN_600
                if est == "AUSENTE":
                    color_borde = ft.Colors.RED_400; icono_estado = ft.Icons.CANCEL; color_icono = ft.Colors.RED_600
                elif est == "PERMISO":
                    color_borde = ft.Colors.BLUE_400; icono_estado = ft.Icons.ASSIGNMENT_TURNED_IN; color_icono = ft.Colors.BLUE_600
                elif est == "ATRASO":
                    color_borde = ft.Colors.ORANGE_400; icono_estado = ft.Icons.ACCESS_TIME_FILLED; color_icono = ft.Colors.ORANGE_600

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
                                        ft.Text(nom, weight=ft.FontWeight.BOLD, size=15),
                                        ft.Text(f"CI: {ci or '—'}", size=11, color=ft.Colors.GREY_600),
                                        ft.Text(f"Tutor: {tut} (CI: {tut_ci or '—'})", size=12, color=ft.Colors.GREY_600),
                                        ft.Text(f"Tel: +591 {tel}", size=12, color=ft.Colors.GREY_600),
                                        ft.Text(f"Nota: {obs}", size=11, italic=True, color=ft.Colors.BLUE_GREY_700) if obs else ft.Container()
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
                abrir_whatsapp_estudiante(r["nombre_completo"], r["tutor_nombre"], r["tutor_telefono"], r["asistencia_id"])
            abrir_siguiente(0)

        btn_notificar_ausentes_masivo = ft.Button(
            content="Avisar Ausencias por WhatsApp", icon=ft.Icons.SEND,
            bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE,
            on_click=notificar_todos_los_ausentes)

        vista_asistencia = ft.Container(
        padding=12, expand=True,
        content=ft.Column([
            ft.Row([dropdown_cursos, txt_fecha, btn_calendario]),
            
            # Envolvemos el buscador para darle un margen controlado
            ft.Container(content=txt_busqueda_asistencia, padding=ft.Padding(left=0, top=0, right=0, bottom=2)),
            
            # Resumen de tarjetas
            ft.Container(content=resumen_dia_row, padding=ft.Padding(left=0, top=0, right=0, bottom=5)),
            
            ft.Row([ft.Text("Pase de Lista (Por defecto: Todos Asistieron)",
                            size=12, italic=True, color=ft.Colors.GREY_700)],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                
            lista_alumnos_col, # Este mantiene expand=True
            
            ft.Container(content=btn_notificar_ausentes_masivo, alignment=ft.Alignment.CENTER, padding=5)
        ], 
        expand=True, 
        spacing=6, # Mantén un espaciado pequeño entre elementos
        horizontal_alignment=ft.CrossAxisAlignment.START
        ))

        # =====================================================================
        # VISTA 2: GESTIÓN DE ESTUDIANTES (con CI y búsqueda)
        # =====================================================================
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
            alumnos = db.buscar_estudiantes(estado_app["curso_id_seleccionado"], filtro)
            for al in alumnos:
                eid = al["id"]
                lista_estudiantes_admin_col.controls.append(
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.PERSON),
                        title=ft.Text(al["nombre_completo"], weight=ft.FontWeight.BOLD),
                        subtitle=ft.Text(
                            f"CI: {al['ci'] or '—'} | Tutor: {al['tutor_nombre']} "
                            f"(CI: {al['tutor_ci'] or '—'}) - Tel: +591 {al['tutor_telefono']}"),
                        trailing=ft.IconButton(
                            icon=ft.Icons.DELETE_OUTLINE, icon_color=ft.Colors.RED_400,
                            on_click=lambda e, i=eid: borrar_estudiante(i))
                    ))
            page.update()

        def borrar_estudiante(eid):
            db.eliminar_estudiante(eid)
            mostrar_snack("Estudiante eliminado.")
            recargar_pase_lista()
            recargar_lista_estudiantes_admin()

        vista_estudiantes = ft.Container(
            padding=15, expand=True,
            content=ft.Column([
                ft.Text("Registrar Nuevo Estudiante", size=17, weight=ft.FontWeight.BOLD),
                dropdown_curso_estudiante,
                txt_nuevo_estudiante, txt_ci_estudiante,
                txt_nuevo_tutor, txt_ci_tutor,
                txt_nuevo_telefono,
                ft.Button(content="Guardar Estudiante", icon=ft.Icons.PERSON_ADD, on_click=guardar_estudiante),
                ft.Divider(),
                ft.Text("Alumnos Registrados en este Curso:", weight=ft.FontWeight.BOLD),
                txt_busqueda_estudiantes,
                lista_estudiantes_admin_col
            ], expand=True, spacing=8))

        # =====================================================================
        # VISTA 3: PERMISOS (con búsqueda)
        # =====================================================================
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
                lista_permisos_col.controls.append(
                    ft.Card(content=ft.Container(padding=10, content=ft.Column([
                        ft.Row([
                            ft.Icon(ft.Icons.EVENT_AVAILABLE, color=ft.Colors.BLUE_700),
                            ft.Text(p["nombre_completo"], weight=ft.FontWeight.BOLD),
                            ft.Text(p["fecha"], size=12, color=ft.Colors.GREY_600)
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

        # =====================================================================
        # VISTA 4: REPORTES (con búsqueda + CSV con CI)
        # =====================================================================
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
                page.update(); return
            for d in datos:
                color_porc = ft.Colors.GREEN_700 if d["porcentaje"] >= 80 else ft.Colors.RED_700
                alerta_badge = ft.Container(
                    content=ft.Text("EN RIESGO", color=ft.Colors.WHITE, size=10, weight=ft.FontWeight.BOLD),
                    bgcolor=ft.Colors.RED_600, border_radius=5, padding=4) if d["en_riesgo"] else ft.Container()
                item = ft.Card(content=ft.Container(padding=10, content=ft.Column([
                    ft.Row([ft.Text(d["nombre"], weight=ft.FontWeight.BOLD, size=14), alerta_badge],
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
                mostrar_snack("No hay datos que exportar."); return
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

        # =====================================================================
        # VISTA 5: DOCENTES (con CI y búsqueda)
        # =====================================================================
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

        def guardar_docente(e):
            if not txt_doc_nombre.value or not txt_doc_ci.value or not txt_doc_materia.value:
                mostrar_snack("Completa nombre, CI y materia.", ft.Colors.RED_700); return
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
                lista_docentes_col.controls.append(
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.SCHOOL),
                        title=ft.Text(d["nombre_completo"], weight=ft.FontWeight.BOLD),
                        subtitle=ft.Text(f"CI: {d['ci'] or '—'} | Materia: {d['materia']} | Tel: +591 {d['telefono'] or '—'}"),
                        trailing=ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, icon_color=ft.Colors.RED_400,
                                                on_click=lambda e, i=did: borrar_docente(i))))
            page.update()

        def borrar_docente(did):
            db.eliminar_docente(did)
            mostrar_snack("Docente desactivado.")
            recargar_lista_docentes()

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
            ], expand=True, spacing=8))

        # =====================================================================
        # VISTA 6: MATERIAS (con búsqueda)
        # =====================================================================
        txt_mat_nombre = ft.TextField(label="Nombre de la Materia", dense=True)
        txt_mat_descripcion = ft.TextField(label="Descripción (opcional)", dense=True)
        txt_busqueda_materias = ft.TextField(
            hint_text="Buscar materia...", dense=True, prefix_icon=ft.Icons.SEARCH,
            on_change=lambda e: recargar_lista_materias())
        lista_materias_col = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)

        def guardar_materia(e):
            if not txt_mat_nombre.value.strip():
                mostrar_snack("Escribe el nombre de la materia.", ft.Colors.RED_700); return
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
                lista_materias_col.controls.append(
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.BOOK),
                        title=ft.Text(m["nombre"], weight=ft.FontWeight.BOLD),
                        subtitle=ft.Text(m["descripcion"] or "—"),
                        trailing=ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, icon_color=ft.Colors.RED_400,
                                                on_click=lambda e, i=mid: borrar_materia(i))))
            page.update()

        def borrar_materia(mid):
            db.eliminar_materia(mid)
            mostrar_snack("Materia desactivada.")
            recargar_lista_materias()

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

        # =====================================================================
        # NAVEGACIÓN PRINCIPAL
        # =====================================================================
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
            page.update()

        barra_navegacion = ft.NavigationBar(
            destinations=[
                ft.NavigationBarDestination(icon=ft.Icons.FACT_CHECK_OUTLINED, selected_icon=ft.Icons.FACT_CHECK, label="Lista"),
                ft.NavigationBarDestination(icon=ft.Icons.PEOPLE_OUTLINE, selected_icon=ft.Icons.PEOPLE, label="Alumnos"),
                ft.NavigationBarDestination(icon=ft.Icons.ASSIGNMENT_OUTLINED, selected_icon=ft.Icons.ASSIGNMENT, label="Permisos"),
                ft.NavigationBarDestination(icon=ft.Icons.ANALYTICS_OUTLINED, selected_icon=ft.Icons.ANALYTICS, label="Reportes"),
                ft.NavigationBarDestination(icon=ft.Icons.SCHOOL_OUTLINED, selected_icon=ft.Icons.SCHOOL, label="Docentes"),
                ft.NavigationBarDestination(icon=ft.Icons.BOOK_OUTLINED, selected_icon=ft.Icons.BOOK, label="Materias"),
            ],
            on_change=cambiar_tab, selected_index=0)

        page.appbar = ft.AppBar(
            leading=ft.Icon(ft.Icons.SCHOOL, color=ft.Colors.WHITE),
            title=ft.Text("Asistencia Escolar", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
            center_title=False, bgcolor=ft.Colors.INDIGO_700,
            actions=[ft.IconButton(ft.Icons.REFRESH, icon_color=ft.Colors.WHITE, tooltip="Actualizar",
                                    on_click=lambda e: recargar_pase_lista())])

        page.navigation_bar = barra_navegacion
        page.add(contenedor_vistas)
        recargar_pase_lista()

    # =========================================================================
    # ARRANQUE: setup si es primera vez, si no, app principal
    # =========================================================================
    if not db.setup_completado():
        mostrar_pantalla_setup()
    else:
        iniciar_app_principal()


if __name__ == "__main__":
    ft.run(main)