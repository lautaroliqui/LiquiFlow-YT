import yt_dlp
import os
import configparser
import sys
import re
import shutil
import zipfile
import requests
from io import BytesIO
import threading

CONFIG_FILE = "config.ini"
config = configparser.ConfigParser()
ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

class DownloadCancelledError(Exception): pass

class MyLogger:
    def __init__(self, status_callback=None):
        self.status_callback = status_callback

    def debug(self, msg): pass
        
    def info(self, msg): pass
    
    def warning(self, msg): pass
        
    def error(self, msg):
        print(f"[YT-DLP ERROR] {msg}")
        if "Sign in" in msg or "Private video" in msg:
            if self.status_callback:
                self.status_callback("Aviso: Video omitido (Privado/Restringido).")
        elif self.status_callback:
            self.status_callback(f"Error de motor: {msg}")

class FFmpegManager:
    FFMPEG_URL = "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
    
    def __init__(self):
        self.bin_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bin')
        self.ffmpeg_exe = os.path.join(self.bin_dir, 'ffmpeg.exe')
        self.ffprobe_exe = os.path.join(self.bin_dir, 'ffprobe.exe')

    def get_ffmpeg_path(self):
        return self.bin_dir if os.path.exists(self.ffmpeg_exe) else None

    def is_installed(self):
        return os.path.exists(self.ffmpeg_exe) or shutil.which("ffmpeg") is not None

    def install_ffmpeg(self, status_callback=None):
        try:
            if not os.path.exists(self.bin_dir): os.makedirs(self.bin_dir)
            if status_callback: status_callback("Descargando FFmpeg...")
            response = requests.get(self.FFMPEG_URL, stream=True)
            response.raise_for_status()
            if status_callback: status_callback("Extrayendo archivos...")
            with zipfile.ZipFile(BytesIO(response.content)) as zf:
                for file in zf.namelist():
                    filename = os.path.basename(file)
                    if filename.lower() == "ffmpeg.exe":
                        with open(self.ffmpeg_exe, 'wb') as f_out: f_out.write(zf.read(file))
                    elif filename.lower() == "ffprobe.exe":
                        with open(self.ffprobe_exe, 'wb') as f_out: f_out.write(zf.read(file))
            return True, "Instalación completada."
        except Exception as e:
            return False, f"Error descargando componentes: {str(e)}"

class AppLogic:
    def __init__(self, on_status_change=None, on_progress=None, on_error=None, on_finish=None, cancel_event=None):
        self.on_status_change = on_status_change
        self.on_progress = on_progress
        self.on_error = on_error
        self.on_finish = on_finish
        self.cancel_event = cancel_event
        self.ffmpeg_manager = FFmpegManager()
        self.last_path = self.cargar_configuracion()
        self.current_entries = [] 
        self.ruta_catalogo_actual = None 
        self.ids_en_ram = set()
        self.total_raw_videos = 0 # RIGOR: Almacena el número absoluto reportado por YouTube

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

    def check_url_type_blocking(self, url):
        self._emit_status("Analizando link (Extrayendo Metadatos)...")
        my_logger = MyLogger(self._emit_status)
        self.current_entries = []
        
        try:
            ydl_opts = {
                'extract_flat': True, 'ignoreerrors': False,
                'logger': my_logger, 'no_warnings': True, 'socket_timeout': 10,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                result_info = ydl.extract_info(url, download=False)
            
            if not result_info: return "error", 0, ""

            if result_info.get('_type') == 'playlist' or 'entries' in result_info:
                entries = result_info.get('entries', [])
                
                # Capturamos el 100% de la playlist (incluyendo los borrados/ocultos)
                self.total_raw_videos = len(entries)
                
                # Filtramos los borrados para no estrellar el motor de descarga
                self.current_entries = [e for e in entries if e and e.get('title') and '[Private video]' not in e.get('title') and '[Deleted video]' not in e.get('title')]
                count = len(self.current_entries)
                playlist_title = self._clean_ansi(result_info.get('title', 'Playlist')).replace('/', '_').replace('\\', '_')
                return "playlist", count, playlist_title
            else:
                self.total_raw_videos = 1
                return "video", 0, result_info.get('title', 'Video')

        except Exception as e:
            self._emit_error(f"Error crítico en validación: {str(e)}")
            return "error", 0, ""

    def hook_progreso(self, d):
        if self.cancel_event and self.cancel_event.is_set():
            raise DownloadCancelledError("Cancelado")
        
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded = d.get('downloaded_bytes')
            if total and downloaded: self._emit_progress(downloaded / total)
            self._emit_status(f"Descargando: {self._clean_ansi(d.get('_percent_str', ''))}")
        elif d['status'] == 'finished':
            self._emit_status("Procesando conversión final...")
            
            info = d.get('info_dict', {})
            if info and 'id' in info and 'title' in info:
                self._registrar_en_catalogo(info['id'], info['title'])

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
            
            return videos_exitosos # Devolvemos el conteo exacto para el reporte final

    def descargar(self, url, path, format_type="video", es_playlist=False, playlist_title="", modo_estricto=True):
        if not url or not path: return self._emit_error("Faltan datos")
        if not self.ffmpeg_manager.is_installed():
            ok, msg = self.ffmpeg_manager.install_ffmpeg(self._emit_status)
            if not ok: return self._emit_error(msg)
        
        self._emit_progress(0.0)

        ydl_opts = {
            'progress_hooks': [self.hook_progreso],
            'restrictfilenames': True,
            'ignoreerrors': True, 
            'logger': MyLogger(self._emit_status),
            'socket_timeout': 15,
            'retries': 5,
        }

        if format_type == "audio":
            ydl_opts['format'] = 'bestaudio[ext=m4a]/bestaudio'
            ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'm4a', 'preferredquality': '192'}]
        else:
            ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best'
            ydl_opts['merge_output_format'] = 'mp4'

        ffmpeg_loc = self.ffmpeg_manager.get_ffmpeg_path()
        if ffmpeg_loc: ydl_opts['ffmpeg_location'] = ffmpeg_loc

        if modo_estricto:
            self._emit_status("Iniciando Modo Estricto (Optimizado)...")
            libreria_maestra = os.path.join(path, "Libreria_Maestra")
            carpeta_playlists = os.path.join(path, "Playlists")
            os.makedirs(libreria_maestra, exist_ok=True)
            os.makedirs(carpeta_playlists, exist_ok=True)
            self.ruta_catalogo_actual = os.path.join(libreria_maestra, "Indice_Auditoria.csv")
            
            self._cargar_catalogo_en_ram()
            ydl_opts['noplaylist'] = False if es_playlist else True
            ydl_opts['outtmpl'] = os.path.join(libreria_maestra, '%(id)s.%(ext)s')
            ydl_opts['download_archive'] = os.path.join(libreria_maestra, 'historial_descargas.txt')
            destino_final_limpieza = libreria_maestra
            
        else:
            self.ruta_catalogo_actual = None 
            self._emit_status("Iniciando Modo Estándar...")
            ydl_opts['noplaylist'] = False if es_playlist else True
            
            if es_playlist:
                carpeta_destino = os.path.join(path, playlist_title)
                ydl_opts['outtmpl'] = os.path.join(carpeta_destino, '%(title)s.%(ext)s')
                destino_final_limpieza = carpeta_destino
            else:
                ydl_opts['outtmpl'] = os.path.join(path, '%(title)s.%(ext)s')
                destino_final_limpieza = path

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                
            mensaje_final = "¡Descarga de video individual completada con éxito!"
            
            if es_playlist:
                if modo_estricto:
                    self._emit_status("Construyendo M3U8 basado en archivos reales...")
                    exitosos = self._generar_m3u8(playlist_title, path, format_type)
                    # RIGOR: Construcción del mensaje de reporte forense
                    mensaje_final = f"¡Playlist procesada!\n\nSe han extraído {exitosos} videos reales de un total de {self.total_raw_videos} videos listados originalmente en la playlist de YouTube."
                else:
                    mensaje_final = f"¡Playlist procesada!\n\nSe intentó descargar {len(self.current_entries)} videos válidos de los {self.total_raw_videos} listados originalmente en YouTube."
                
            self._emit_status("¡Proceso Finalizado!")
            self._emit_progress(1.0)
            self.guardar_configuracion(path)
            
            if self.on_finish: self.on_finish(mensaje_final)
            
        except DownloadCancelledError:
            self._emit_status("Operación abortada por el usuario.")
        except Exception as e:
            self._emit_error(f"Error crítico en motor: {str(e)}")
        finally:
            if os.path.exists(destino_final_limpieza):
                for archivo in os.listdir(destino_final_limpieza):
                    if archivo.endswith(".part") or archivo.endswith(".ytdl"):
                        try: os.remove(os.path.join(destino_final_limpieza, archivo))
                        except: pass

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