import os
import sys
import webbrowser
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time
import sv_ttk
from PIL import Image, ImageTk
from app_logic import AppLogic

class YtDownloaderApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("LiquiFlow YT - Descargador de YouTube Simple y Eficiente")
        self.geometry("800x600")
        self.configure(padx=25, pady=25)
        sv_ttk.set_theme("dark")

        # --- INYECCIÓN DE Icon---
        if hasattr(sys, '_MEIPASS'):
            icon_path = os.path.join(sys._MEIPASS, 'LiquiFlow-YT.ico')
            self.gh_img_path = os.path.join(sys._MEIPASS, 'github.png')
        else:
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'LiquiFlow-YT.ico')
            self.gh_img_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'github.png')

        if os.path.exists(icon_path):
            try:
                img = Image.open(icon_path)
                img_suavizada = img.resize((32, 32), Image.Resampling.LANCZOS)
                self._icon_photo = ImageTk.PhotoImage(img_suavizada) 
                self.iconphoto(False, self._icon_photo)
            except Exception as e:
                print(f"Error crítico cargando icono de ventana: {e}")

        # Variables de estado
        self.temp_playlist_data = {"url": "", "path": "", "title": ""}
        self.ultimo_refresco = 0.0
        self.cancel_event = threading.Event()
        
        # Conectamos con lógica de aplicación
        self.logic = AppLogic(
            on_status_change=self.actualizar_estado,
            on_progress=self.actualizar_progreso,
            on_error=self.reportar_error_desde_hilo,
            on_finish=self.finalizar_descarga_desde_hilo,
            cancel_event=self.cancel_event
        )

        self.config_path = self.logic.last_path or self.logic.get_user_videos_dir()
        
        self.crear_interfaz()

    def crear_interfaz(self):
        # Título
        lbl_titulo = tk.Label(self, text="LiquiFlow YT", font=("Segoe UI", 24, "bold"), fg="#4da6ff", bg=self.cget('bg'))
        lbl_titulo.pack(pady=(10, 25))

        # Contenedor principal con márgenes internos
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20)

        # Fila URL
        frame_url = ttk.Frame(main_frame)
        frame_url.pack(fill=tk.X, pady=10)
        ttk.Label(frame_url, text="URL de YouTube:", width=16, font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
        self.var_url = tk.StringVar()
        ttk.Entry(frame_url, textvariable=self.var_url, font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # Fila Directorio
        frame_dir = ttk.Frame(main_frame)
        frame_dir.pack(fill=tk.X, pady=10)
        ttk.Label(frame_dir, text="Directorio Raíz:", width=16, font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
        self.var_ruta = tk.StringVar(value=self.config_path)
        ttk.Entry(frame_dir, textvariable=self.var_ruta, state='readonly', font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(frame_dir, text="Examinar", command=self.examinar_carpeta).pack(side=tk.LEFT)

        # Fila Opciones
        frame_ops = ttk.Frame(main_frame)
        frame_ops.pack(fill=tk.X, pady=20)
        
        ttk.Label(frame_ops, text="Formato:", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=(0, 5))
        self.var_formato = tk.StringVar(value="Video")
        combo_formato = ttk.Combobox(frame_ops, textvariable=self.var_formato, values=["Audio", "Video"], state="readonly", width=10, font=("Segoe UI", 10))
        combo_formato.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(frame_ops, text="Calidad Max:", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=(25, 5))
        self.var_resolucion = tk.StringVar(value="MAX")
        combo_res = ttk.Combobox(frame_ops, textvariable=self.var_resolucion, values=["MAX", "2160", "1440", "1080", "720", "480"], state="readonly", width=8, font=("Segoe UI", 10))
        combo_res.pack(side=tk.LEFT, padx=5)
        
        self.var_estricto = tk.BooleanVar(value=False)
        ttk.Checkbutton(frame_ops, text="Librería Estricta (Avanzado)", variable=self.var_estricto).pack(side=tk.LEFT, padx=30)

        # Separador visual
        ttk.Separator(main_frame, orient='horizontal').pack(fill=tk.X, pady=15)

        # Fila Botones Principales (AHORA USANDO TTK PURO Y ESTILOS)
        self.frame_botones = ttk.Frame(main_frame)
        self.frame_botones.pack(pady=10)
        
        # Usamos Accent.TButton para que brille con el color del SO
        self.btn_descargar = ttk.Button(self.frame_botones, text="DESCARGAR", style="Accent.TButton", command=self.iniciar_proceso, width=18)
        self.btn_descargar.pack(side=tk.LEFT, padx=10)
        
        self.btn_exportar = ttk.Button(self.frame_botones, text="EXPORTAR A MÓVIL", command=self.exportar_m3u8, width=22)
        self.btn_exportar.pack(side=tk.LEFT, padx=10)
        
        self.btn_cancelar = ttk.Button(self.frame_botones, text="CANCELAR", command=self.cancelar_proceso, width=15, state=tk.DISABLED)
        self.btn_cancelar.pack(side=tk.LEFT, padx=10)

        # Panel Confirmación Playlist (Oculto al inicio)
        self.frame_confirmacion = ttk.Frame(main_frame)
        
        self.lbl_confirmacion = tk.Label(self.frame_confirmacion, text="", font=("Segoe UI", 11), fg="#e6e6e6", bg=self.cget('bg'), justify=tk.CENTER)
        self.lbl_confirmacion.pack(pady=10)
        
        frame_btns_conf = ttk.Frame(self.frame_confirmacion)
        frame_btns_conf.pack()
        ttk.Button(frame_btns_conf, text="Sí, integrar", style="Accent.TButton", command=self.confirmar_si, width=15).pack(side=tk.LEFT, padx=10)
        ttk.Button(frame_btns_conf, text="No, cancelar", command=self.confirmar_no, width=15).pack(side=tk.LEFT, padx=10)

        # Barra de Progreso y Estado
        self.var_progreso = tk.DoubleVar(value=0)
        self.barra_progreso = ttk.Progressbar(main_frame, variable=self.var_progreso, maximum=1.0)
        self.barra_progreso.pack(fill=tk.X, pady=(30, 10))
        
        self.var_estado = tk.StringVar(value="Sistema en espera...")
        tk.Label(main_frame, textvariable=self.var_estado, font=("Segoe UI", 10, "italic"), fg="#a6a6a6", bg=self.cget('bg')).pack()

       # --- NUEVO FOOTER (CRÉDITOS Y GITHUB) ---
        frame_footer = ttk.Frame(main_frame)
        frame_footer.pack(side=tk.BOTTOM, fill=tk.X, pady=(20, 0))

        lbl_creditos = tk.Label(frame_footer, text="Desarrollado con ❤️ por LiquiDev", font=("Segoe UI", 9, "italic"), fg="#7f8c8d", bg=self.cget('bg'))
        lbl_creditos.pack(side=tk.LEFT)

        # Carga del PNG de GitHub para el botón (con manejo de errores)
        self.gh_icon = None
        if os.path.exists(self.gh_img_path):
            try:
                self.gh_icon = tk.PhotoImage(file=self.gh_img_path)
            except Exception as e:
                print(f"Error cargando logo de GitHub: {e}")

        # Botón con imagen inyectada a la izquierda del texto
        btn_github = ttk.Button(
            frame_footer, 
            text=" Ver Código en GitHub", 
            image=self.gh_icon, 
            compound=tk.LEFT, 
            command=lambda: webbrowser.open("https://github.com/lautaroliqui/LiquiFlow-YT")
        )
        btn_github.pack(side=tk.RIGHT)

    # --- Lógica de Interacción ---
    def examinar_carpeta(self):
        ruta = filedialog.askdirectory(title="Seleccionar Directorio Raíz")
        if ruta:
            self.var_ruta.set(ruta)

    def exportar_m3u8(self):
        archivos = filedialog.askopenfilenames(
            title="Seleccionar playlists (.m3u8)", 
            filetypes=[("M3U8 Playlist", "*.m3u8")]
        )
        if archivos:
            self.btn_exportar.config(state=tk.DISABLED, text="Exportando...")
            self.var_progreso.set(0)
            self.cancel_event.clear()
            
            ruta_base = self.var_ruta.get().strip()
            
            threading.Thread(
                target=self.logic.exportar_playlist_a_staging, 
                args=(archivos, ruta_base), 
                daemon=True
            ).start()

    # --- Actualización Segura desde Hilos ---
    def actualizar_progreso(self, val):
        self.var_progreso.set(val)

    def actualizar_estado(self, msg):
        tiempo_actual = time.time()

        if "Descargando:" not in msg:
            self.var_estado.set(msg)
            self.update_idletasks()
        elif tiempo_actual - self.ultimo_refresco > 0.15:
            self.var_estado.set(msg)
            self.update_idletasks()
            self.ultimo_refresco = tiempo_actual

    def reportar_error_desde_hilo(self, msg):
        self.after(0, self._mostrar_error_y_reset, msg)
        
    def _mostrar_error_y_reset(self, msg):
        messagebox.showerror("Aviso del Sistema", msg)
        self.reset_ui()

    # RIGOR: Modificado para recibir y mostrar el reporte de éxito detallado
    def finalizar_descarga_desde_hilo(self, msg="¡Descarga y procesamiento completados!"):
        self.after(0, self._mostrar_exito_y_reset, msg)
        
    def _mostrar_exito_y_reset(self, msg):
        messagebox.showinfo("Reporte Final", msg)
        self.reset_ui()

    def reset_ui(self):
        self.frame_confirmacion.pack_forget()
        self.frame_botones.pack(pady=10)
        
        self.btn_descargar.config(state=tk.NORMAL, text="DESCARGAR")
        self.btn_cancelar.config(state=tk.DISABLED)
        self.btn_exportar.config(state=tk.NORMAL, text="EXPORTAR A MÓVIL")
        
        self.var_progreso.set(0)

    # --- Controladores de Procesos ---
    def iniciar_proceso(self):
        url = self.var_url.get().strip()
        path = self.var_ruta.get().strip()
        
        if not url or not path:
            messagebox.showwarning("Faltan Datos", "Por favor, ingresa una URL y selecciona una ruta de destino.")
            return

        self.btn_descargar.config(state=tk.DISABLED, text="Procesando...")
        self.btn_exportar.config(state=tk.DISABLED)
        self.btn_cancelar.config(state=tk.NORMAL)
        
        self.cancel_event.clear()
        threading.Thread(target=self.verificar_y_descargar, args=(url, path), daemon=True).start()

    def cancelar_proceso(self):
        self.cancel_event.set()
        self.actualizar_estado("Cancelando descargas...")
        self.btn_cancelar.config(state=tk.DISABLED)
        if self.frame_confirmacion.winfo_ismapped():
            self.reset_ui()

    def verificar_y_descargar(self, url, path):
        try:
            tipo, num_videos, pl_title = self.logic.check_url_type_blocking(url)
            
            if self.cancel_event.is_set() or tipo == "error":
                self.after(0, self.reset_ui)
                return
                
            if tipo == "playlist":
                self.temp_playlist_data = {"url": url, "path": path, "title": pl_title}
                modo_actual = "Librería Estricta" if self.var_estricto.get() else "Carpetas Normales"
                texto = f"Playlist detectada: {pl_title}\nContiene {num_videos} videos válidos (de {self.logic.total_raw_videos} totales).\nModo: {modo_actual}.\n\n¿Deseas proceder con la descarga masiva?"
                
                self.after(0, self.mostrar_confirmacion, texto)
            else:
                self.logic.descargar(
                    url=url, 
                    path=path, 
                    format_type=self.var_formato.get().lower(),
                    resolucion=self.var_resolucion.get().lower(),
                    es_playlist=False, 
                    modo_estricto=self.var_estricto.get()
                )

        except Exception as e:
            self.reportar_error_desde_hilo(str(e))

    def mostrar_confirmacion(self, texto):
        self.lbl_confirmacion.config(text=texto)
        self.frame_botones.pack_forget()
        self.frame_confirmacion.pack(pady=20)

    def confirmar_si(self):
        self.frame_confirmacion.pack_forget()
        self.frame_botones.pack(pady=20)
        self.btn_descargar.config(text="Procesando Playlist...")
        
        threading.Thread(
            target=lambda: self.logic.descargar(
                url=self.temp_playlist_data["url"], 
                path=self.temp_playlist_data["path"], 
                format_type=self.var_formato.get().lower(),
                resolucion=self.var_resolucion.get().lower(),
                es_playlist=True, 
                playlist_title=self.temp_playlist_data["title"], 
                modo_estricto=self.var_estricto.get()
            ), daemon=True
        ).start()

    def confirmar_no(self):
        self.reset_ui()
        self.actualizar_estado("Operación cancelada por el usuario.")

if __name__ == "__main__":
    app = YtDownloaderApp()
    app.mainloop()