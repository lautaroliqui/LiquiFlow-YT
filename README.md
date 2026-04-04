# Librería Maestra YT (Python / Tkinter)

Una aplicación de escritorio robusta y autónoma para descargar, organizar y auditar videos y playlists de YouTube. Diseñada con un motor de procesos desacoplado para garantizar la longevidad del software evadiendo el estrangulamiento de resolución (DRM).

## 🚀 Características Arquitectónicas

* **Orquestador Autónomo (Zero-Maintenance):** El programa no depende de librerías de Python estáticas. Cuenta con un `DependencyManager` que descarga y auto-actualiza el motor `yt-dlp` desde los repositorios oficiales de GitHub en cada ejecución, garantizando inmunidad a largo plazo contra los bloqueos de YouTube.
* **Degradación Grácil de Resolución:** Permite establecer un "techo" de calidad (ej. 1080p). El motor extraerá y fusionará las mejores pistas de video y audio disponibles hasta ese límite. Si un video antiguo no alcanza el techo, el sistema bajará automáticamente al siguiente escalón disponible sin interrumpir la descarga masiva.
* **Modo "Librería Estricta":** Indexa las descargas nombrando los archivos con sus IDs criptográficos únicos, evitando colisiones con caracteres prohibidos por Windows. Genera automáticamente listas de reproducción `.m3u8` con metadatos limpios para reproductores móviles.
* **Auditoría Forense de Playlists:** Verifica físicamente la existencia de los archivos en el disco duro antes de incluirlos en el catálogo, detectando y omitiendo silenciosamente los "Ghost Links" (videos privados o eliminados).
* **Exportación a Móvil Zero-Copy:** Preparar listas para el teléfono consume 0 bytes extra. El motor utiliza enlaces duros nativos (`os.link`) para crear carpetas de exportación en milisegundos sin desgaste de disco.
* **Interfaz Nativa y Asíncrona:** GUI construida en Tkinter puro, impulsada por el motor `sv_ttk` (Sun Valley Dark Theme) con componentes `Accent`. Implementa válvulas de control (Throttle) y un escáner Regex en tiempo real para extraer la telemetría del subproceso sin congelar la ventana.

## 🛠️ Tecnologías Usadas

* **Python 3.10+**
* **Tkinter + sv_ttk** (Interfaz Gráfica nativa)
* **Subprocess & Regex** (Orquestación de binarios y telemetría)
* **yt-dlp** (Motor de extracción web dinámico)
* **FFmpeg** (Fusión y post-procesamiento multimedia)

## 📦 Instalación y Uso

1.  **Clonar el repositorio:**
    ```bash
    git clone [https://github.com/lautaroliqui/simple-youtube-downloader.git](https://github.com/lautaroliqui/simple-youtube-downloader.git)
    cd simple-youtube-downloader
    ```

2.  **Instalar dependencias visuales y de red:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Ejecutar la aplicación:**
    *(El software se encargará de crear la carpeta `/bin` y descargar los motores pesados automáticamente en el primer inicio).*
    ```bash
    python main.py
    ```

## ⚠️ Nota Legal

Herramienta creada exclusivamente con fines educativos sobre desarrollo de software, orquestación de subprocesos, expresiones regulares y manipulación de sistemas de archivos nativos en Python. El usuario es responsable de respetar los Términos de Servicio de YouTube.

## 👤 Autor

**LiquiDev**