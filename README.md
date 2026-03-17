# YouTube Downloader (Python/CustomTkinter)

Una aplicación de escritorio moderna, rápida y estricta para descargar videos y playlists de YouTube. Construida en Python, utilizando [Flet](https://flet.dev/) para la interfaz gráfica y el motor de [yt-dlp](https://github.com/yt-dlp/yt-dlp) para la extracción de medios.

## 🚀 Características

* **Interfaz Gráfica Moderna (GUI):** UI limpia, responsiva y asíncrona, impulsada por Flet v0.82.2.
* **Gestión Autónoma de Dependencias:** Descarga y configura automáticamente los binarios de FFmpeg en una carpeta local (`/bin`), evitando que el usuario deba lidiar con las variables de entorno (`PATH`) de Windows.
* **Selección de Formato:** Permite elegir entre extracción de Video (MP4 optimizado a 1080p con audio fusionado) o Solo Audio (M4A a 192kbps).
* **Modo de Librería Estricta (Optimizado para Servidores Multimedia):**
  * Utiliza los IDs nativos de YouTube como nombre de archivo para evitar errores de longitud de ruta (`PathTooLongException`) en Windows.
  * Genera archivos de lista de reproducción `.m3u8` con rutas relativas, 100% compatibles con reproductores como VLC y sistemas Android.
  * Mantiene un catálogo optimizado en RAM (`Indice_Auditoria.csv`) que mapea los IDs criptográficos con los títulos legibles, evitando descargas duplicadas y minimizando el desgaste del disco duro (I/O).
  * Integración nativa del historial de descargas de `yt-dlp`.
* **Soporte de Playlists:** Detecta enlaces de listas de reproducción completas y permite descargas por lotes con un solo clic.

> **⚠️ Nota sobre Autenticación y Videos Privados:**
> Debido a las recientes actualizaciones de seguridad en Google Chrome para Windows (transición de DPAPI a *App-Bound Encryption*), la extracción automática de cookies locales está temporalmente deshabilitada para garantizar la estabilidad de la aplicación. Esta versión está optimizada exclusivamente para contenido y playlists de acceso público, asi que, si tienen playlists privadas deberan hacerlas publicas ("No listado" o "Publico").

## 🧱 Arquitectura del Proyecto

*  **main_flet.py**: Gestiona el layout de la interfaz, los eventos del usuario, los diálogos de confirmación y el manejo de hilos asíncronos para no bloquear la UI.
*  **app_logic.py**: Contiene el núcleo de descarga, la inyección dinámica de parámetros en yt-dlp, la lógica de I/O para el catálogo CSV y la gestión de FFmpeg.

## 🛠️ Requisitos/Tecnologías Usadas

* **Python 3.10+**
* **Flet** (Interfaz Gráfica)
* **yt-dlp** (Motor de descarga robusto)
* **FFmpeg** (Procesamiento multimedia)
* **Requests** (Gestión de descargas internas)

## 📦 Instalación y Uso

1.  **Clonar el repositorio:**
    ```bash
    git clone https://github.com/lautaroliqui/simple-youtube-downloader.git
    cd TU_REPO
    ```

2.  **Crea y activa un entorno virtual (Recomendado):
    ```bash
    python -m venv .venv
    source .venv/Scripts/activate  # En Windows Git Bash
    # o en CMD: .venv\Scripts\activate.bat
    ```
3.  **Instalar dependencias:**
    Se recomienda usar un entorno virtual.
    ```bash
    pip install -r requirements.txt
    ```

3.  **Ejecutar la aplicación:**
    ```bash
    python main_flet.py
    ```

## ⚠️ Nota Legal

Esta herramienta fue creada exclusivamente con fines educativos para el aprendizaje sobre desarrollo de software, manejo de hilos (threading), interfaces gráficas y gestión de archivos en Python.

El usuario es responsable de respetar los Términos de Servicio de YouTube y las leyes de derechos de autor vigentes en su país. El autor no se hace responsable del mal uso de esta herramienta.

## 👤 Autor

**LiquiDev**
