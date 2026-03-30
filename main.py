import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time
import sv_ttk
from app_logic import AppLogic

class YtDownloaderApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Librería Maestra YT")
        self.geometry("750x600")
        self.configure(padx=25, pady=25)
        sv_ttk.set_theme("dark")

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

        # Estilo general
        style = ttk.Style()

        # Título
        lbl_titulo = tk.Label(self, text="Librería Maestra YT", font=("Segoe UI", 22, "bold"), fg="#0052cc")
        lbl_titulo.pack(pady=(0, 25))

        # Fila URL
        frame_url = ttk.Frame(self)
        frame_url.pack(fill=tk.X, pady=8)
        ttk.Label(frame_url, text="URL de YouTube:", width=15, font=("Segoe UI", 10)).pack(side=tk.LEFT)
        self.var_url = tk.StringVar()
        ttk.Entry(frame_url, textvariable=self.var_url, font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # Fila Directorio
        frame_dir = ttk.Frame(self)
        frame_dir.pack(fill=tk.X, pady=8)
        ttk.Label(frame_dir, text="Directorio Raíz:", width=15, font=("Segoe UI", 10)).pack(side=tk.LEFT)
        self.var_ruta = tk.StringVar(value=self.config_path)
        ttk.Entry(frame_dir, textvariable=self.var_ruta, state='readonly', font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(frame_dir, text="Examinar", command=self.examinar_carpeta).pack(side=tk.LEFT)

        # Fila Opciones
        frame_ops = ttk.Frame(self)
        frame_ops.pack(fill=tk.X, pady=20)
        
        ttk.Label(frame_ops, text="Formato:", font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0, 5))
        self.var_formato = tk.StringVar(value="audio")
        combo = ttk.Combobox(frame_ops, textvariable=self.var_formato, values=["audio", "video"], state="readonly", width=15, font=("Segoe UI", 10))
        combo.pack(side=tk.LEFT, padx=5)
        
        self.var_estricto = tk.BooleanVar(value=False)
        ttk.Checkbutton(frame_ops, text="Librería Estricta (Carpetas Ordenadas)", variable=self.var_estricto).pack(side=tk.LEFT, padx=30)

        # Fila Botones Principales
        self.frame_botones = tk.Frame(self)
        self.frame_botones.pack(pady=20)
        
        self.btn_descargar = tk.Button(self.frame_botones, text="DESCARGAR", bg="#0078D7", fg="white", font=("Segoe UI", 10, "bold"), width=16, height=2, relief=tk.FLAT, command=self.iniciar_proceso)
        self.btn_descargar.pack(side=tk.LEFT, padx=10)
        
        self.btn_exportar = tk.Button(self.frame_botones, text="EXPORTAR A MÓVIL", bg="#D83B01", fg="white", font=("Segoe UI", 10, "bold"), width=20, height=2, relief=tk.FLAT, command=self.exportar_m3u8)
        self.btn_exportar.pack(side=tk.LEFT, padx=10)
        
        self.btn_cancelar = tk.Button(self.frame_botones, text="CANCELAR", bg="#A6A6A6", fg="white", font=("Segoe UI", 10, "bold"), width=14, height=2, relief=tk.FLAT, state=tk.DISABLED, command=self.cancelar_proceso)
        self.btn_cancelar.pack(side=tk.LEFT, padx=10)

        # Panel Confirmación Playlist (Oculto al inicio)
        self.frame_confirmacion = tk.Frame(self)
        
        self.lbl_confirmacion = tk.Label(self.frame_confirmacion, text="", font=("Segoe UI", 11, "bold"), justify=tk.CENTER)
        self.lbl_confirmacion.pack(pady=10)
        
        frame_btns_conf = tk.Frame(self.frame_confirmacion)
        frame_btns_conf.pack()
        tk.Button(frame_btns_conf, text="Sí, integrar", bg="#107C10", fg="white", font=("Segoe UI", 10, "bold"), width=15, relief=tk.FLAT, command=self.confirmar_si).pack(side=tk.LEFT, padx=10)
        tk.Button(frame_btns_conf, text="No, cancelar", bg="#E81123", fg="white", font=("Segoe UI", 10, "bold"), width=15, relief=tk.FLAT, command=self.confirmar_no).pack(side=tk.LEFT, padx=10)

        # Barra de Progreso y Estado
        self.var_progreso = tk.DoubleVar(value=0)
        self.barra_progreso = ttk.Progressbar(self, variable=self.var_progreso, maximum=1.0, length=650)
        self.barra_progreso.pack(pady=(25, 10))
        
        self.var_estado = tk.StringVar(value="Listo.")
        tk.Label(self, textvariable=self.var_estado, font=("Segoe UI", 10), fg="#666666").pack()

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
        self.frame_botones.pack(pady=20)
        
        self.btn_descargar.config(state=tk.NORMAL, text="DESCARGAR")
        self.btn_cancelar.config(state=tk.DISABLED, bg="#A6A6A6")
        self.btn_exportar.config(state=tk.NORMAL, text="EXPORTAR A MÓVIL")
        
        self.var_progreso.set(0)

    # --- Controladores de Procesos ---
    def iniciar_proceso(self):
        url = self.var_url.get().strip()
        path = self.var_ruta.get().strip()
        
        if not url or not path:
            messagebox.showwarning("Faltan Datos", "Por favor, ingresa una URL y selecciona una ruta de destino.")
            return

        self.btn_descargar.config(state=tk.DISABLED, text="Verificando...")
        self.btn_exportar.config(state=tk.DISABLED)
        self.btn_cancelar.config(state=tk.NORMAL, bg="#E81123")
        
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
                    format_type=self.var_formato.get(), 
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
                self.temp_playlist_data["url"], 
                self.temp_playlist_data["path"], 
                self.var_formato.get(), 
                True, 
                self.temp_playlist_data["title"], 
                self.var_estricto.get()
            ), daemon=True
        ).start()

    def confirmar_no(self):
        self.reset_ui()
        self.actualizar_estado("Operación cancelada por el usuario.")

if __name__ == "__main__":
    app = YtDownloaderApp()
    app.mainloop()