# LiquiFlow YT (Python / Tkinter)

Una aplicación de escritorio robusta y autónoma para descargar, organizar y auditar videos y playlists de YouTube. Diseñada con un motor de procesos desacoplado para garantizar la longevidad del software evadiendo el estrangulamiento de resolución y los bloqueos de red.

## 🚀 Características Principales

* **Orquestador Autónomo (Zero-Maintenance):** El programa no depende de librerías de Python estáticas. Un `DependencyManager` descarga y auto-actualiza el motor `yt-dlp` desde GitHub en cada ejecución, garantizando inmunidad a largo plazo.
* **Descarga Masiva con Degradación Grácil:** Extrae playlists enteras estableciendo un "techo" de calidad (ej. 1080p). Si un video no alcanza esa resolución, el motor baja automáticamente al siguiente escalón disponible sin interrumpir el proceso.
* **Cortacorrientes Antibaneos (Kill Switch):** Si YouTube bloquea temporalmente tu IP (Rate Limit/Error 429), el sistema intercepta la anomalía en tiempo real, decapita el subproceso para proteger tu red y guarda el progreso exacto de los videos logrados.
* **Tolerancia a Fallos y Auditoría Forense:** Verifica la disponibilidad de los enlaces. Ignora silenciosamente los "Ghost Links" (videos privados, bloqueados o eliminados por copyright), garantizando que la playlist se genere intacta con los sobrevivientes.
* **Librería Estricta e Inyección de Metadatos:** Nombra los archivos físicos con sus IDs criptográficos para evitar colisiones en Windows. Simultáneamente, inyecta los títulos originales dentro del archivo `.mp4/.m4a` (ID3 Tags) para una lectura perfecta en reproductores como VLC o Windows Media Player.
* **Exportación a Móvil Zero-Copy:** Preparar listas para dispositivos externos consume 0 bytes extra. Utiliza enlaces duros nativos (`os.link`) para crear carpetas de exportación en milisegundos sin desgaste de disco.
* **Interfaz Nativa y Asíncrona:** Interfaz gráfica construida en Tkinter con el motor `sv_ttk` (Dark Theme). Implementa un escáner Regex que lee la terminal en segundo plano para mostrar métricas en tiempo real sin congelar la ventana.

## 🛠️ Tecnologías Usadas

* **Python 3.10+**
* **Tkinter + sv_ttk** (Interfaz Gráfica nativa)
* **Subprocess & Regex** (Orquestación de binarios y telemetría)
* **yt-dlp** (Motor de extracción web dinámico)
* **FFmpeg** (Fusión y post-procesamiento multimedia)

## 📦 Instalación y Uso

1.  **Clonar el repositorio:**
    ```bash
    git clone [https://github.com/lautaroliqui/LiquiFlow-YT.git](https://github.com/lautaroliqui/LiquiFlow-YT.git)
    cd LiquiFlow-YT
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