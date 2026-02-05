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

class DownloadCancelledError(Exception):
    pass

class MyLogger:
    def __init__(self, status_callback=None):
        self.status_callback = status_callback

    def debug(self, msg):
        pass

    def info(self, msg):
        pass

    def warning(self, msg):

        if "unavailable" in msg or "hidden" in msg:
            print(f"DEBUG WARNING (Ignorado): {msg}")
        else:
            print(f"DEBUG Internal Warning: {msg}")

    def error(self, msg):
        if self.status_callback:
            self.status_callback(f"Error detectado: {msg}")

class FFmpegManager:
    FFMPEG_URL = "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
    
    def __init__(self):
        self.bin_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bin')
        self.ffmpeg_exe = os.path.join(self.bin_dir, 'ffmpeg.exe')
        self.ffprobe_exe = os.path.join(self.bin_dir, 'ffprobe.exe')

    def get_ffmpeg_path(self):
        if os.path.exists(self.ffmpeg_exe):
            return self.bin_dir
        return None

    def is_installed(self):
        local_check = os.path.exists(self.ffmpeg_exe)
        system_check = shutil.which("ffmpeg") is not None
        return local_check or system_check

    def install_ffmpeg(self, status_callback=None):
        try:
            if not os.path.exists(self.bin_dir):
                os.makedirs(self.bin_dir)
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
        self.total_playlist_videos = 0
        self.playlist_title = ""
        self.ffmpeg_manager = FFmpegManager()
        self.last_path = self.cargar_configuracion()

    def _emit_status(self, msg):
        if self.on_status_change: self.on_status_change(msg)
    
    def _emit_progress(self, val):
        if self.on_progress: self.on_progress(val)

    def _emit_error(self, msg):
        if self.on_error: self.on_error(msg)
        
    def cargar_configuracion(self):
        config.read(CONFIG_FILE)
        if 'Settings' in config and 'last_download_path' in config['Settings']:
            return config['Settings']['last_download_path']
        return ""

    def guardar_configuracion(self, path):
        if 'Settings' not in config: config['Settings'] = {}
        config['Settings']['last_download_path'] = path
        with open(CONFIG_FILE, 'w') as f: config.write(f)

    def get_user_videos_dir(self):
        home = os.path.expanduser("~")
        candidates = [os.path.join(home, "Videos"), os.path.join(home, "Vídeos")]
        for c in candidates:
            if os.path.isdir(c): return c
        return home

    def _clean_ansi(self, text):
        return ANSI_ESCAPE.sub('', text)

    def _limpiar_archivos_temporales(self, carpeta_destino, es_playlist=False, playlist_title=""):
        try:
            target_dir = os.path.join(carpeta_destino, playlist_title) if es_playlist and playlist_title else carpeta_destino
            if os.path.exists(target_dir):
                for filename in os.listdir(target_dir):
                    if filename.endswith(".part") or filename.endswith(".ytdl"):
                        try: os.remove(os.path.join(target_dir, filename))
                        except: pass
            if es_playlist and playlist_title and os.path.exists(target_dir) and not os.listdir(target_dir):
                try: os.rmdir(target_dir)
                except: pass
        except Exception: pass

    def check_url_type_blocking(self, url):
        self._emit_status("Analizando link (Modo Rápido)...")
        print("DEBUG: Iniciando check_url_type_blocking...")

        my_logger = MyLogger(status_callback=None)
        
        # Variables para guardar el resultado y procesarlo DESPUÉS de cerrar yt-dlp
        result_info = None
        
        try:
            ydl_opts = {
                'quiet': True,
                'extract_flat': True,
                'ignoreerrors': True,
                'logger': my_logger,
                'no_warnings': True,
                'socket_timeout': 10,
            }
            
            print(f"DEBUG: Ejecutando YoutubeDL...")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                result_info = ydl.extract_info(url, download=False)
            
            print("DEBUG: YoutubeDL cerrado correctamente. Procesando datos...") 

            # --- PROCESAMIENTO (Ya fuera del motor) ---
            if not result_info:
                print("DEBUG: Info vacía.")
                return False, 0

            if result_info.get('_type') == 'playlist' or 'entries' in result_info:
                print("DEBUG: Es Playlist.")
                
                # Conteo seguro
                count = result_info.get('playlist_count') or result_info.get('n_entries')
                if not count:
                    entries = result_info.get('entries', [])
                    try:
                        if not isinstance(entries, list): entries = list(entries)
                        count = len(entries)
                    except: count = 0

                print(f"DEBUG: Conteo final: {count}")
                
                self.total_playlist_videos = count
                self.playlist_title = self._clean_ansi(result_info.get('title', 'Playlist')).replace('/', '_')
                
                return True, self.total_playlist_videos
            else:
                print("DEBUG: Es Video único.")
                self.total_playlist_videos = 0
                self.playlist_title = ""
                return False, 0
                    
        except Exception as e:
            print(f"DEBUG ERROR: {str(e)}")
            self._emit_error(f"Error verificando: {str(e)}")
            return False, 0

    def hook_progreso(self, d):
        try:
            if self.cancel_event and self.cancel_event.is_set():
                raise DownloadCancelledError("Cancelado")
            
            if d['status'] == 'downloading':
                total = d.get('total_bytes') or d.get('total_bytes_estimate')
                downloaded = d.get('downloaded_bytes')
                if total and downloaded: self._emit_progress(downloaded / total)
                
                p_str = self._clean_ansi(d.get('_percent_str', ''))
                clean_title = self._clean_ansi(d.get('info_dict', {}).get('title', 'Video'))
                if len(clean_title) > 30: clean_title = clean_title[:27] + "..."

                info = d.get('info_dict', {})
                current = info.get('playlist_index')
                total_v = self.total_playlist_videos or info.get('n_entries')
                
                prefix = f"[{current}/{total_v}] " if current and total_v else ""
                self._emit_status(f"{prefix}Descargando: {p_str} - {clean_title}")
                
            elif d['status'] == 'finished':
                self._emit_progress(1.0)
                self._emit_status("Procesando conversión...")

        except DownloadCancelledError: raise 
        except Exception: pass

    def descargar(self, url, path, es_playlist=False, pl_start=None, pl_end=None):
        if not url or not path: return self._emit_error("Faltan datos")
        if not self.ffmpeg_manager.is_installed():
            ok, msg = self.ffmpeg_manager.install_ffmpeg(self._emit_status)
            if not ok: return self._emit_error(msg)
        
        self._emit_status("Iniciando motor...")
        self._emit_progress(0.0)
        
        # Opciones ROBUSTAS para descarga
        ydl_opts = {
            'outtmpl': os.path.join(path, '%(title)s.%(ext)s'),
            'progress_hooks': [self.hook_progreso],
            'restrictfilenames': True,
            'noplaylist': not es_playlist,
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best',
            'merge_output_format': 'mp4',
            'ignoreerrors': True,
            'logger': MyLogger(self._emit_status),
            'socket_timeout': 15,
            'retries': 5,
        }
        
        ffmpeg_loc = self.ffmpeg_manager.get_ffmpeg_path()
        if ffmpeg_loc: ydl_opts['ffmpeg_location'] = ffmpeg_loc

        if es_playlist:
            ydl_opts['outtmpl'] = os.path.join(path, self.playlist_title, '%(title)s.%(ext)s')

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            self._emit_status("¡Completado!")
            self.guardar_configuracion(path)
            if self.on_finish: self.on_finish()
        except DownloadCancelledError:
            self._emit_status("Cancelado.")
        except Exception as e:
            self._emit_error(f"Error crítico: {str(e)}")
        finally:
            self._limpiar_archivos_temporales(path, es_playlist, self.playlist_title)