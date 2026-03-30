# Librería Maestra YT (Python / Tkinter)

Una aplicación de escritorio robusta y rigurosa para descargar, organizar y auditar videos y playlists de YouTube. Diseñada para mantener la máxima fidelidad de archivo y evitar el estrangulamiento de resolución (DRM) mediante el motor `yt-dlp`.

## 🚀 Características Arquitectónicas

* **Extracción de Calidad Absoluta:** Ignora las resoluciones pre-fusionadas de baja calidad de YouTube (360p/720p). Descarga independientemente las pistas de video (`bestvideo`) y audio de alta fidelidad (`bestaudio`) y las fusiona localmente a través de FFmpeg para garantizar 1080p y 4K reales.
* **Modo "Librería Estricta":** En lugar de arrojar archivos sueltos, indexa las descargas nombrando los archivos con sus IDs criptográficos únicos, evitando colisiones con caracteres prohibidos por Windows. Genera automáticamente listas de reproducción `.m3u8` con metadatos limpios para reproductores móviles.
* **Auditoría Forense de Playlists:** Verifica físicamente la existencia de los archivos en el disco duro antes de incluirlos en el catálogo, detectando y omitiendo silenciosamente los "Ghost Links" (videos privados o eliminados por YouTube) y entregando un reporte de exactitud al finalizar.
* **Exportación a Móvil Zero-Copy:** Preparar listas para el teléfono no consume espacio extra. El motor utiliza enlaces duros nativos del sistema operativo (`os.link`) para crear carpetas de exportación (Staging) en milisegundos y con 0 bytes de desgaste de disco.
* **Interfaz Nativa y Asíncrona:** GUI construida en Tkinter puro, impulsada por el motor de diseño `sv_ttk` (Sun Valley Dark Theme). Implementa válvulas de control de renderizado (Throttle) a ~5 FPS para evitar la saturación del hilo gráfico durante la lluvia de datos de descarga.
* **Autogestión de FFmpeg:** Detecta la ausencia de FFmpeg en el sistema y descarga automáticamente los binarios portables necesarios sin intervenir en las variables de entorno (`PATH`) del usuario.

## 🛠️ Tecnologías Usadas

* **Python 3.10+**
* **Tkinter + sv_ttk** (Interfaz Gráfica y motor de renderizado oscuro)
* **yt-dlp** (Motor de extracción web)
* **FFmpeg** (Fusión y post-procesamiento multimedia)

## 📦 Instalación y Uso

1.  **Clonar el repositorio:**
    ```bash
    git clone [https://github.com/lautaroliqui/simple-youtube-downloader.git](https://github.com/lautaroliqui/simple-youtube-downloader.git)
    cd simple-youtube-downloader
    ```

2.  **Instalar dependencias:**
    Se recomienda estrictamente el uso de un entorno virtual (`.venv`).
    ```bash
    pip install yt-dlp requests sv-ttk
    ```

3.  **Ejecutar la aplicación:**
    ```bash
    python main.py
    ```

## ⚠️ Nota Legal

Esta herramienta fue creada exclusivamente con fines educativos para el aprendizaje sobre desarrollo de software, concurrencia de hilos (threading), manipulación de sistemas de archivos nativos y gestión de flujos de datos en Python.

El usuario es responsable de respetar los Términos de Servicio de YouTube y las leyes de derechos de autor vigentes en su país. El autor no se hace responsable del mal uso de esta herramienta para vulnerar derechos de propiedad intelectual.

## 👤 Autor

**LiquiDev**