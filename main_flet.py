import flet as ft
import threading
import tkinter as tk
from tkinter import filedialog
from app_logic import AppLogic

def main(page: ft.Page):
    page.title = "Librería Maestra YT"
    page.window_width = 750 
    page.window_height = 650 
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    
    temp_playlist_data = {"url": "", "path": "", "title": ""}

    def actualizar_estado(msg):
        txt_estado.value = msg
        txt_estado.update()

    def actualizar_progreso(val):
        progress_bar.value = val
        progress_bar.update()

    def reportar_error(msg):
        page.snack_bar = ft.SnackBar(ft.Text(f"AVISO: {msg}"), bgcolor=ft.Colors.RED, duration=8000)
        page.snack_bar.open = True
        page.update()
        reset_ui()

    def finalizar_descarga():
        page.snack_bar = ft.SnackBar(ft.Text("¡Descarga y procesamiento completados!"), bgcolor=ft.Colors.GREEN)
        page.snack_bar.open = True
        reset_ui()
        page.update()

    def reset_ui():
        fila_botones_principales.visible = True
        panel_confirmacion.visible = False
        btn_descargar.disabled = False
        btn_descargar.text = "DESCARGAR"
        btn_cancelar.disabled = True
        btn_cancelar.bgcolor = "#500000"
        progress_bar.value = 0
        dropdown_formato.disabled = False
        switch_modo.disabled = False
        btn_exportar.disabled = False
        page.update()

    cancel_event = threading.Event()
    logic = AppLogic(
        on_status_change=actualizar_estado,
        on_progress=actualizar_progreso,
        on_error=reportar_error,
        on_finish=finalizar_descarga,
        cancel_event=cancel_event
    )

    config_path = logic.last_path or logic.get_user_videos_dir()

    # --- BYPASS NATIVO DE WINDOWS ---
    def abrir_selector_carpeta(e):
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        ruta = filedialog.askdirectory(parent=root, title="Seleccionar Directorio Raíz")
        root.destroy()
        
        if ruta:
            input_ruta.value = ruta
            input_ruta.update()

    def abrir_selector_m3u8(e):
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        archivo = filedialog.askopenfilename(
            parent=root,
            title="Seleccionar playlist (.m3u8)",
            filetypes=[("M3U8 Playlist", "*.m3u8")]
        )
        root.destroy()
    
        if archivo:
            exportar_playlist(archivo)
    
    def exportar_playlist(ruta_m3u8):
        if not ruta_m3u8:
            reportar_error("No se seleccionó ninguna playlist")
            return

        btn_exportar.disabled = True
        btn_exportar.text = "Exportando..."
        progress_bar.value = 0
        page.update()

        cancel_event.clear()

        threading.Thread(
            target=lambda: logic.exportar_playlist_a_staging(ruta_m3u8),
            daemon=True
        ).start()

    # --- Lógica de Procesamiento ---
    def iniciar_proceso(e):
        url = input_url.value
        path = input_ruta.value
        
        if not url or not path:
            reportar_error("Faltan datos de URL o Ruta Principal")
            return

        btn_descargar.disabled = True
        dropdown_formato.disabled = True
        switch_modo.disabled = True
        btn_descargar.text = "Verificando Metadatos..."
        page.update()
        
        btn_cancelar.disabled = False
        btn_cancelar.bgcolor = ft.Colors.RED
        btn_cancelar.update()
        
        cancel_event.clear()
        threading.Thread(target=verificar_y_descargar, args=(url, path), daemon=True).start()

    def cancelar_proceso(e):
        cancel_event.set()
        actualizar_estado("Cancelando descargas...")
        btn_cancelar.disabled = True
        btn_cancelar.update()
        if panel_confirmacion.visible: reset_ui()

    def verificar_y_descargar(url, path):
        try:
            tipo, num_videos, pl_title = logic.check_url_type_blocking(url)
            
            if cancel_event.is_set():
                reset_ui()
                return

            if tipo == "error":
                reset_ui()
                return
                
            elif tipo == "playlist":
                temp_playlist_data["url"] = url
                temp_playlist_data["path"] = path
                temp_playlist_data["title"] = pl_title
                
                modo_actual = "Librería Estricta" if switch_modo.value else "Carpetas Normales"
                lbl_confirmacion.value = f"Playlist: {pl_title}\n{num_videos} videos. Modo: {modo_actual}. ¿Descargar?"
                
                fila_botones_principales.visible = False
                panel_confirmacion.visible = True
                page.update()
            else:
                logic.descargar(
                    url=url, 
                    path=path, 
                    format_type=dropdown_formato.value, 
                    es_playlist=False, 
                    modo_estricto=switch_modo.value
                )
                reset_ui()

        except Exception as e:
            reportar_error(str(e))

    def confirmar_playlist_si(e):
        panel_confirmacion.visible = False
        fila_botones_principales.visible = True
        btn_descargar.text = "Procesando Playlist..."
        page.update()
        
        url = temp_playlist_data["url"]
        path = temp_playlist_data["path"]
        title = temp_playlist_data["title"]
        formato = dropdown_formato.value
        es_estricto = switch_modo.value 
        
        threading.Thread(
            target=lambda: logic.descargar(url, path, formato, True, title, es_estricto), 
            daemon=True
        ).start()

    def confirmar_playlist_no(e):
        reset_ui()
        actualizar_estado("Operación cancelada.")

    # --- Construcción de la UI ---
    lbl_titulo = ft.Text("Librería Maestra YT", size=30, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE)
    
    input_url = ft.TextField(label="URL de YouTube", prefix_icon=ft.Icons.LINK, width=500)
    
    input_ruta = ft.TextField(value=config_path, label="Directorio Raíz", prefix_icon=ft.Icons.FOLDER, width=400, read_only=True)
    btn_carpeta = ft.Button("Examinar", icon=ft.Icons.FOLDER_OPEN, on_click=abrir_selector_carpeta)

    dropdown_formato = ft.Dropdown(
        label="Formato",
        width=150,
        options=[
            ft.dropdown.Option("video", text="Video (MP4)"),
            ft.dropdown.Option("audio", text="Audio (M4A)")
        ],
        value="audio"
    )

    switch_modo = ft.Switch(
        label="Librería Estricta",
        value=False,
        label_position=ft.LabelPosition.RIGHT,
    )

    btn_descargar = ft.Button("DESCARGAR", icon=ft.Icons.DOWNLOAD, on_click=iniciar_proceso, bgcolor=ft.Colors.BLUE, color=ft.Colors.WHITE, width=200, height=50)
    btn_cancelar = ft.Button("CANCELAR", icon=ft.Icons.CANCEL, on_click=cancelar_proceso, bgcolor="#500000", color=ft.Colors.WHITE, width=150, height=50, disabled=True)
    btn_exportar = ft.Button(
        "EXPORTAR A MÓVIL",
        icon=ft.Icons.PHONE_ANDROID,
        on_click=abrir_selector_m3u8,
        bgcolor=ft.Colors.ORANGE,
        color=ft.Colors.WHITE,
        width=220,
        height=50
    )
    
    fila_botones_principales = ft.Row(
        [btn_descargar, btn_exportar, btn_cancelar],
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=20
    )
    
    lbl_confirmacion = ft.Text("", size=16, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)
    btn_si_playlist = ft.Button("Sí, integrar", bgcolor=ft.Colors.GREEN, color=ft.Colors.WHITE, on_click=confirmar_playlist_si)
    btn_no_playlist = ft.Button("No, cancelar", style=ft.ButtonStyle(color=ft.Colors.RED), on_click=confirmar_playlist_no)
    
    panel_confirmacion = ft.Column([lbl_confirmacion, ft.Row([btn_si_playlist, btn_no_playlist], alignment=ft.MainAxisAlignment.CENTER)], horizontal_alignment=ft.CrossAxisAlignment.CENTER, visible=False)

    progress_bar = ft.ProgressBar(width=500, value=0)
    txt_estado = ft.Text("Listo.", color=ft.Colors.GREY)

    page.add(
        ft.Column([
            ft.Container(height=20),
            lbl_titulo, ft.Container(height=20),
            input_url,
            ft.Row([input_ruta, btn_carpeta], alignment=ft.MainAxisAlignment.CENTER),
            ft.Container(height=10),
            ft.Row([dropdown_formato, switch_modo], alignment=ft.MainAxisAlignment.CENTER, spacing=30),
            ft.Container(height=20),
            fila_botones_principales, panel_confirmacion, ft.Container(height=20),
            progress_bar, txt_estado
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    )

if __name__ == "__main__":
    ft.run(main)