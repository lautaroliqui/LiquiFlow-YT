import os
import configparser
import re
import shutil
import zipfile
import requests
import subprocess
import json
from io import BytesIO

CONFIG_FILE = "config.ini"
config = configparser.ConfigParser()
ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

class DownloadCancelledError(Exception): pass

# --- FASE 1: GESTOR DE BINARIOS INDEPENDIENTES (AUTO-UPDATER) ---
class DependencyManager:
    FFMPEG_URL = "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
    YTDLP_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
    
    def __init__(self):
        self.bin_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bin')
        self.ffmpeg_exe = os.path.join(self.bin_dir, 'ffmpeg.exe')
        self.ffprobe_exe = os.path.join(self.bin_dir, 'ffprobe.exe')
        self.ytdlp_exe = os.path.join(self.bin_dir, 'yt-dlp.exe')

    def get_ffmpeg_path(self):
        return self.bin_dir if os.path.exists(self.ffmpeg_exe) else None

    def check_and_update_all(self, status_callback=None):
        if not os.path.exists(self.bin_dir): 
            os.makedirs(self.bin_dir)

        # 1. Auditoría de yt-dlp.exe
        if not os.path.exists(self.ytdlp_exe):
            if status_callback: status_callback("Descargando motor principal yt-dlp.exe...")
            try:
                r = requests.get(self.YTDLP_URL, stream=True)
                r.raise_for_status()
                with open(self.ytdlp_exe, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            except Exception as e:
                return False, f"Error descargando motor: {str(e)}"
        else:
            if status_callback: status_callback("Buscando actualizaciones del motor de extracción...")
            try:
                # RIGOR: Forzamos la auto-actualización del binario para evadir parches de YouTube
                subprocess.run(
                    [self.ytdlp_exe, '-U'], 
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    capture_output=True,
                    timeout=15
                )
            except Exception:
                pass # Si no hay internet o falla el update, omitimos y usamos la versión local

        # 2. Auditoría de FFmpeg
        if not os.path.exists(self.ffmpeg_exe):
            if status_callback: status_callback("Descargando procesador FFmpeg...")
            try:
                response = requests.get(self.FFMPEG_URL, stream=True)
                response.raise_for_status()
                if status_callback: status_callback("Extrayendo FFmpeg...")
                with zipfile.ZipFile(BytesIO(response.content)) as zf:
                    for file in zf.namelist():
                        filename = os.path.basename(file)
                        if filename.lower() == "ffmpeg.exe":
                            with open(self.ffmpeg_exe, 'wb') as f_out: f_out.write(zf.read(file))
                        elif filename.lower() == "ffprobe.exe":
                            with open(self.ffprobe_exe, 'wb') as f_out: f_out.write(zf.read(file))
            except Exception as e:
                return False, f"Error descargando FFmpeg: {str(e)}"

        return True, "Dependencias listas."


class AppLogic:
    def __init__(self, on_status_change=None, on_progress=None, on_error=None, on_finish=None, cancel_event=None):
        self.on_status_change = on_status_change
        self.on_progress = on_progress
        self.on_error = on_error
        self.on_finish = on_finish
        self.cancel_event = cancel_event
        self.dep_manager = DependencyManager()
        self.last_path = self.cargar_configuracion()
        self.current_entries = [] 
        self.ruta_catalogo_actual = None 
        self.ids_en_ram = set()
        self.total_raw_videos = 0 

    def _emit_status(self, msg):
        if self.on_status_change: self.on_status_change(msg)
    def _emit_progress(self, val):
        if self.on_progress: self.on_progress(val)
    def _emit_error(self, msg):
        if self.on_error: self.on_error(msg)
        
    def cargar_configuracion(self):
        config.read(CONFIG_FILE)
        return config['Settings']['last_download_path'] if 'Settings' in config and 'last_download_path' in config['Settings'] else ""

    def guardar_configuracion(self, path):
        if 'Settings' not in config: config['Settings'] = {}
        config['Settings']['last_download_path'] = path
        with open(CONFIG_FILE, 'w') as f: config.write(f)

    def get_user_videos_dir(self):
        home = os.path.expanduser("~")
        for c in [os.path.join(home, "Videos"), os.path.join(home, "Vídeos")]:
            if os.path.isdir(c): return c
        return home

    def _clean_ansi(self, text):
        return ANSI_ESCAPE.sub('', text)

    def _cargar_catalogo_en_ram(self):
        self.ids_en_ram.clear()
        if self.ruta_catalogo_actual and os.path.exists(self.ruta_catalogo_actual):
            with open(self.ruta_catalogo_actual, 'r', encoding='utf-8') as f:
                for linea in f:
                    partes = linea.split(',', 1)
                    if partes: self.ids_en_ram.add(partes[0].strip())

    def _registrar_en_catalogo(self, vid_id, titulo):
        if not self.ruta_catalogo_actual: return
        if vid_id not in self.ids_en_ram:
            self.ids_en_ram.add(vid_id)
            with open(self.ruta_catalogo_actual, 'a', encoding='utf-8') as f:
                titulo_seguro = str(titulo).replace(',', ' -').replace('\n', ' ')
                f.write(f"{vid_id},{titulo_seguro}\n")

    # --- FASE 2: EXTRACCIÓN MEDIANTE SUBPROCESO ---
    def check_url_type_blocking(self, url):
        self._emit_status("Analizando link e inyectando dependencias...")
        
        ok, msg = self.dep_manager.check_and_update_all(self._emit_status)
        if not ok:
            self._emit_error(msg)
            return "error", 0, ""

        self._emit_status("Extrayendo Metadatos (Subproceso)...")
        self.current_entries = []
        
        try:
            # Ordenamos al binario que nos escupa un JSON gigante con la info
            cmd = [
                self.dep_manager.ytdlp_exe, 
                '-J', # Dump JSON
                '--flat-playlist', 
                '--no-warnings', 
                url
            ]
            
            process = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                creationflags=subprocess.CREATE_NO_WINDOW,
                encoding='utf-8'
            )

            if process.returncode != 0:
                # Filtramos el mensaje de error para que sea amigable
                err_msg = process.stderr
                if "Sign in" in err_msg or "Private video" in err_msg:
                    self._emit_error("El video es privado o tiene restricción de edad.")
                else:
                    self._emit_error(f"Error extrayendo datos del link.")
                return "error", 0, ""

            result_info = json.loads(process.stdout)

            if result_info.get('_type') == 'playlist' or 'entries' in result_info:
                entries = result_info.get('entries', [])
                self.total_raw_videos = len(entries)
                self.current_entries = [e for e in entries if e and e.get('title') and '[Private video]' not in e.get('title') and '[Deleted video]' not in e.get('title')]
                count = len(self.current_entries)
                playlist_title = self._clean_ansi(result_info.get('title', 'Playlist')).replace('/', '_').replace('\\', '_')
                return "playlist", count, playlist_title
            else:
                self.total_raw_videos = 1
                return "video", 0, result_info.get('title', 'Video')

        except Exception as e:
            self._emit_error(f"Error crítico en validación JSON: {str(e)}")
            return "error", 0, ""

    def _generar_m3u8(self, playlist_title, path, format_type):
        carpeta_playlists = os.path.join(path, "Playlists")
        ruta_m3u8 = os.path.join(carpeta_playlists, f"{playlist_title}.m3u8")
        ext = "mp4" if format_type == "video" else "m4a"
        libreria_maestra = os.path.join(path, "Libreria_Maestra")

        with open(ruta_m3u8, 'w', encoding='utf-8') as f:
            f.write("#EXTM3U\n")
            videos_exitosos = 0
            for entry in self.current_entries:
                vid_id = entry.get('id')
                title = entry.get('title', 'Unknown')
                ruta_fisica = os.path.join(libreria_maestra, f"{vid_id}.{ext}")
                
                if os.path.exists(ruta_fisica):
                    ruta_relativa = f"../Libreria_Maestra/{vid_id}.{ext}"
                    f.write(f"#EXTINF:-1,{title}\n")
                    f.write(f"{ruta_relativa}\n")
                    videos_exitosos += 1
            
            return videos_exitosos

    # --- FASE 3: DESCARGA AUTÓNOMA Y ESCÁNER REGEX ---
    def descargar(self, url, path, format_type="video", resolucion="max", es_playlist=False, playlist_title="", modo_estricto=True):
        if not url or not path: return self._emit_error("Faltan datos")
        
        # Doble check de dependencias
        ok, msg = self.dep_manager.check_and_update_all(self._emit_status)
        if not ok: return self._emit_error(msg)
        
        self._emit_progress(0.0)

        # Construcción del comando masivo
        cmd = [
            self.dep_manager.ytdlp_exe,
            '--newline',        # Vital para poder leer la terminal con Python
            '--ignore-errors',
            '--no-warnings',
            '--restrict-filenames',
            '--socket-timeout', '15',
            '--retries', '5',
            # RIGOR: Inyección de metadatos internos para reproductores rudimentarios
            '--embed-metadata',
            '--parse-metadata', 'title:%(title)s'
        ]

        if format_type == "audio":
            cmd.extend(['-f', 'bestaudio[ext=m4a]/bestaudio', '-x', '--audio-format', 'm4a', '--audio-quality', '192K'])
        else:
            if resolucion == "max":
                cmd.extend(['-f', 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best', '--merge-output-format', 'mp4'])
            else:
                # DEGRADACIÓN GRÁCIL SIEMPRE: Busca el tope máximo indicado, si no existe, baja al siguiente.
                selector = f'bestvideo[height<={resolucion}][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<={resolucion}]+bestaudio/best'
                cmd.extend(['-f', selector, '--merge-output-format', 'mp4'])

        ffmpeg_loc = self.dep_manager.get_ffmpeg_path()
        if ffmpeg_loc: 
            cmd.extend(['--ffmpeg-location', ffmpeg_loc])

        if modo_estricto:
            self._emit_status("Iniciando Modo Estricto (Optimizado)...")
            libreria_maestra = os.path.join(path, "Libreria_Maestra")
            carpeta_playlists = os.path.join(path, "Playlists")
            os.makedirs(libreria_maestra, exist_ok=True)
            os.makedirs(carpeta_playlists, exist_ok=True)
            self.ruta_catalogo_actual = os.path.join(libreria_maestra, "Indice_Auditoria.csv")
            
            self._cargar_catalogo_en_ram()
            if not es_playlist: cmd.append('--no-playlist')
            
            cmd.extend(['-o', os.path.join(libreria_maestra, '%(id)s.%(ext)s')])
            cmd.extend(['--download-archive', os.path.join(libreria_maestra, 'historial_descargas.txt')])
            destino_final_limpieza = libreria_maestra
            
        else:
            self.ruta_catalogo_actual = None 
            self._emit_status("Iniciando Modo Estándar...")
            if not es_playlist: cmd.append('--no-playlist')
            
            if es_playlist:
                carpeta_destino = os.path.join(path, playlist_title)
                cmd.extend(['-o', os.path.join(carpeta_destino, '%(title)s.%(ext)s')])
                destino_final_limpieza = carpeta_destino
            else:
                cmd.extend(['-o', os.path.join(path, '%(title)s.%(ext)s')])
                destino_final_limpieza = path

        # Añadimos la URL al final del comando
        cmd.append(url)

        try:
            # Ejecutamos la terminal invisible y la conectamos a nuestro código
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                text=True, 
                creationflags=subprocess.CREATE_NO_WINDOW,
                encoding='utf-8',
                errors='replace' 
            )

            # RIGOR: Variable para capturar el último grito de auxilio del motor
            ultimo_error_capturado = ""

            # ESCÁNER REGEX EN TIEMPO REAL
            for line in process.stdout:
                if self.cancel_event.is_set():
                    process.terminate()
                    raise DownloadCancelledError()

                line_clean = self._clean_ansi(line).strip()

                # --- 1. CAPTURA DE TELEMETRÍA DE ERRORES ---
                if "ERROR:" in line_clean:
                    ultimo_error_capturado = line_clean.replace("ERROR: ", "")
                    
                    # CORTACORRIENTES: Detección de Baneo de YouTube en la rama pública
                    err_lower = ultimo_error_capturado.lower()
                    if "bot" in err_lower or "429" in err_lower or "too many requests" in err_lower:
                        self._emit_status("¡ALERTA ROJA: Bloqueo de YouTube detectado! Abortando...")
                        process.terminate() 
                        break 
                        
                    continue 

                # --- 2. ESCÁNER DE PROGRESO ---
                match_progreso = re.search(r'\[download\]\s+([0-9\.]+)%', line_clean)
                if match_progreso:
                    porcentaje_texto = match_progreso.group(1)
                    self._emit_progress(float(porcentaje_texto) / 100.0)
                    self._emit_status(f"Descargando: {porcentaje_texto}%")
                
                # --- 3. EVENTOS DE CONVERSIÓN ---
                elif "Destination:" in line_clean and ".m4a" not in line_clean and ".mp4" not in line_clean:
                    pass 
                elif "Merging formats" in line_clean or "Extracting audio" in line_clean:
                    self._emit_status("Procesando conversión final con FFmpeg...")
                elif "has already been recorded in the archive" in line_clean:
                    self._emit_status("Omitiendo: El archivo ya existe en el disco.")
                elif "Sign in" in line_clean or "Private video" in line_clean:
                    self._emit_status("Aviso: Video omitido (Privado/Restringido).")
                elif "Requested format is not available" in line_clean:
                    self._emit_status("Aviso: Omitido (No alcanza la resolución exigida).")

                # Actualización de Catálogo si vemos el ID
                match_id = re.search(r'\[download\] Destination: .*\\(.*?)\.(mp4|m4a)', line_clean)
                if match_id and self.ruta_catalogo_actual:
                    vid_id = match_id.group(1)
                    self._registrar_en_catalogo(vid_id, f"Video_Extraido_{vid_id}")

            process.wait() # Esperamos a que la terminal invisible se cierre

            # --- ANÁLISIS FORENSE DEL CIERRE (VERSIÓN MAIN) ---
            es_baneo = ultimo_error_capturado and ("bot" in ultimo_error_capturado.lower() or "429" in ultimo_error_capturado or "too many requests" in ultimo_error_capturado.lower())

            if process.returncode != 0 and not self.cancel_event.is_set():
                if es_baneo:
                    self._emit_status("Iniciando protocolo de interrupción por bloqueo...")
                elif es_playlist:
                    if ultimo_error_capturado:
                        self._emit_status(f"Aviso: Algunos enlaces omitidos ({ultimo_error_capturado})")
                else:
                    if ultimo_error_capturado:
                        self._emit_error(f"Fallo en descarga: {ultimo_error_capturado}")
                    else:
                        self._emit_error("La terminal externa colapsó sin emitir un error legible.")
                    return 

            # --- CONSTRUCCIÓN DEL REPORTE ---
            if es_baneo:
                mensaje_final = "⚠️ PROCESO INTERRUMPIDO POR YOUTUBE ⚠️\n\nTu IP ha sido bloqueada temporalmente por exceso de descargas."
                if es_playlist:
                    mensaje_final += "\n\nLos videos descargados exitosamente hasta este punto han sido guardados."
            else:
                mensaje_final = "¡Descarga de video individual completada con éxito!"
            
            if es_playlist:
                if modo_estricto:
                    self._emit_status("Construyendo M3U8 basado en archivos reales...")
                    exitosos = self._generar_m3u8(playlist_title, path, format_type)
                    if not es_baneo:
                        mensaje_final = f"¡Playlist procesada!\n\nSe han extraído {exitosos} videos reales de un total de {self.total_raw_videos} videos listados."
                else:
                    if not es_baneo:
                        mensaje_final = f"¡Playlist procesada!\n\nSe procesó la lista de {self.total_raw_videos} videos listados originalmente en YouTube."
                
            self._emit_status("¡Proceso Finalizado!")
            self._emit_progress(1.0)
            self.guardar_configuracion(path)
            
            if self.on_finish: self.on_finish(mensaje_final)
            
        except DownloadCancelledError:
            self._emit_status("Operación abortada por el usuario.")
        except Exception as e:
            self._emit_error(f"Error crítico en subproceso: {str(e)}")
        finally:
            if os.path.exists(destino_final_limpieza):
                for archivo in os.listdir(destino_final_limpieza):
                    if archivo.endswith(".part") or archivo.endswith(".ytdl"):
                        try: os.remove(os.path.join(destino_final_limpieza, archivo))
                        except: pass

    # La función de exportación se mantiene intacta porque no interactúa con yt-dlp
    def exportar_playlist_a_staging(self, rutas_m3u8, ruta_base_destino):
        try:
            if not rutas_m3u8:
                return self._emit_error("No se seleccionaron playlists")

            self._emit_status("Analizando múltiples playlists...")

            libreria_origen = os.path.join(ruta_base_destino, "Libreria_Maestra")
            staging_root = os.path.join(ruta_base_destino, "Exportacion_Movil")
            staging_lib = os.path.join(staging_root, "Libreria_Maestra")
            staging_playlists = os.path.join(staging_root, "Playlists")

            os.makedirs(staging_lib, exist_ok=True)
            os.makedirs(staging_playlists, exist_ok=True)

            ids_unicos_a_exportar = set()
            
            for ruta in rutas_m3u8:
                with open(ruta, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip().startswith("../Libreria_Maestra/"):
                            nombre_archivo = os.path.basename(line.strip())
                            ids_unicos_a_exportar.add(nombre_archivo)

            lista_archivos = list(ids_unicos_a_exportar)
            total = len(lista_archivos)
            enlazados = 0
            copiados = 0

            self._emit_status(f"Procesando {total} archivos únicos sin redundancia...")

            for i, nombre_archivo in enumerate(lista_archivos):
                if self.cancel_event and self.cancel_event.is_set():
                    raise DownloadCancelledError()

                origen = os.path.join(libreria_origen, nombre_archivo)
                destino = os.path.join(staging_lib, nombre_archivo)

                if not os.path.exists(origen):
                    self._emit_status(f"Falta archivo físico: {nombre_archivo}")
                    continue

                if not os.path.exists(destino):
                    try:
                        os.link(origen, destino)
                        enlazados += 1
                    except OSError:
                        shutil.copy2(origen, destino)
                        copiados += 1

                self._emit_progress((i + 1) / total)

            for ruta in rutas_m3u8:
                nombre_playlist = os.path.basename(ruta)
                destino_playlist = os.path.join(staging_playlists, nombre_playlist)
                shutil.copy2(ruta, destino_playlist)

            self._emit_status("¡Exportación completa!")
            self._emit_progress(1.0)
            
            mensaje_exportacion = f"¡Exportación a Móvil Completada!\n\nSe han preparado {total} archivos únicos.\n• {enlazados} enlazados instantáneamente (0 espacio extra).\n• {copiados} copiados."

            if self.on_finish:
                self.on_finish(mensaje_exportacion)

        except DownloadCancelledError:
            self._emit_status("Exportación abortada.")
        except Exception as e:
            self._emit_error(f"Error estructural en exportación: {str(e)}")