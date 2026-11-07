# Asistencia Escolar Móvil (Flet + SQLite + Android 14)

Aplicación móvil moderna desarrollada en **Python con Flet** y base de datos local **SQLite**, optimizada para Android 14 (API 34) y diseñada específicamente para el trabajo ágil del docente en aula.

---

## 🎯 Características Principales

1. **Pase de Lista Inteligente y Rápido**:
   - Al abrir la fecha y curso, **todos los alumnos aparecen marcados como "PRESENTE" por defecto**.
   - El docente únicamente desmarca a aquellos que no asistieron.
2. **Notificación Directa a Padres/Tutores por WhatsApp**:
   - Al marcar a un alumno como **AUSENTE**, la aplicación activa un diálogo o enlace directo a WhatsApp con un mensaje formal precargado con el nombre del tutor, del alumno y la fecha.
   - También dispone de un botón masivo: *"Avisar Ausencias por WhatsApp"*.
3. **Gestión de Permisos y Justificaciones**:
   - Registro de licencias médicas o motivos familiares previos.
   - Si un alumno tiene permiso aprobado para hoy, el sistema lo marca automáticamente como **"PERMISO"** en lugar de falta injustificada.
4. **Reportes y Detección Temprana de Riesgo**:
   - Estadísticas diarias (% asistencia, presentes, faltas, retrasos).
   - Reporte mensual con cálculo automático de porcentaje de asistencia.
   - **Indicador de Riesgo**: Alerta automática si un alumno acumula 3 o más faltas o cae por debajo del 80% de asistencia.
   - Exportación a formato CSV (compatible con Excel).
5. **Configuración Personalizable**:
   - Nombre de la escuela/institución educativa.
   - Código de país para WhatsApp (+54, +52, +57, +591, etc.).
   - Plantilla de mensaje editable.

---

## 🚀 Paso a Paso: Ejecución y Desarrollo

### 1. Requisitos Previos
- Python 3.10 o superior instalado.
- Conexión a internet para instalar las dependencias.

### 2. Instalación de Dependencias
Abre una terminal o PowerShell en la carpeta del proyecto y ejecuta:

```bash
pip install -r requirements.txt
```
*(O directamente `pip install flet`)*

### 3. Probar en la Computadora (Simulando Pantalla Móvil)
Para probar la interfaz y la lógica de inmediato:

```bash
python main.py
```
Se abrirá una ventana adaptada al tamaño estándar de una pantalla móvil (412x840 px).

---

## 📱 Compilación para Android 14 (Paso a Paso)

Flet utiliza **Flutter** internamente para compilar aplicaciones nativas para Android.

### Requisitos para compilar APK:
1. Tener instalado el **Android SDK** con soporte para **API 34 (Android 14)** y Java JDK 17 o 21.
2. Flet CLI (`pip install flet`).

### Pasos de compilación:

1. **Crear archivo de configuración `flet.toml`** en la raíz del proyecto (ya configurado para Android 14):

```toml
[app]
name = "AsistenciaEscolar"
org = "com.docente.asistencia"
version = "1.0.0"

[android]
package = "com.docente.asistencia"
min_sdk_version = 34
target_sdk_version = 34
permissions = [
    "INTERNET"
]
```

2. **Compilar el APK con Flet Build**:
```bash
flet build apk --project-name "AsistenciaEscolar" --org "com.docente.asistencia"
```

El instalador `.apk` resultante se generará en la carpeta `build/apk/` listo para instalar en cualquier dispositivo con Android 14+.

---

## 💡 Propuestas Adicionales Incluidas para el Docente

- **Estados Ampliados**: Además de Presente y Ausente, cuenta con *Permiso* y *Atraso* (tardanza).
- **Notificación sin Costo**: El uso del protocolo `https://wa.me/` aprovecha la app nativa de WhatsApp instalada en Android sin requerir suscripciones pagas ni servidores intermedios.
- **Funcionamiento 100% Offline**: Los datos se guardan en la base de datos SQLite interna del dispositivo, no dependiendo de internet en el aula excepto al enviar los mensajes por WhatsApp.
- **Exportación Abierta**: Reportes descargables en CSV para entregar a dirección o secretaría académica.
