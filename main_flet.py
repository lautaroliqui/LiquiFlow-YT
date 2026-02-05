import flet as ft
import threading
from app_logic import AppLogic

def main(page: ft.Page):
    # --- Configuración de la Ventana ---
    page.title = "YouTube Downloader (Flet v0.28.3)"
    page.window_width = 700
    page.window_height = 600
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    
    # Referencias globales
    current_path = ""
    # Guardamos datos temporales de la playlist aquí
    temp_playlist_data = {"url": "", "path": ""}

    # --- CALLBACKS DE LA LÓGICA ---
    def actualizar_estado(msg):
        txt_estado.value = msg
        txt_estado.update()

    def actualizar_progreso(val):
        progress_bar.value = val
        progress_bar.update()

    def reportar_error(msg):
        page.snack_bar = ft.SnackBar(ft.Text(f"ERROR: {msg}"), bgcolor=ft.Colors.RED)
        page.snack_bar.open = True
        page.update()
        reset_ui()

    def finalizar_descarga():
        page.snack_bar = ft.SnackBar(ft.Text("¡Descarga completada!"), bgcolor=ft.Colors.GREEN)
        page.snack_bar.open = True
        reset_ui()
        page.update()

    def reset_ui():
        # 1. Restaurar botones principales
        fila_botones_principales.visible = True
        panel_confirmacion.visible = False
        
        btn_descargar.disabled = False
        btn_descargar.text = "DESCARGAR"
        
        btn_cancelar.disabled = True
        btn_cancelar.bgcolor = "#500000"

        progress_bar.value = 0
        
        page.update()

    # Instancia de la lógica
    cancel_event = threading.Event()
    logic = AppLogic(
        on_status_change=actualizar_estado,
        on_progress=actualizar_progreso,
        on_error=reportar_error,
        on_finish=finalizar_descarga,
        cancel_event=cancel_event
    )

    config_path = logic.last_path or logic.get_user_videos_dir()

    # --- MANEJADORES DE EVENTOS UI ---

    def al_seleccionar_carpeta(e: ft.FilePickerResultEvent):
        if e.path:
            input_ruta.value = e.path
            input_ruta.update()
            nonlocal current_path
            current_path = e.path

    def abrir_selector(e):
        selector_archivos.get_directory_path()

    def iniciar_proceso(e):
        url = input_url.value
        path = input_ruta.value
        
        if not url:
            reportar_error("Falta la URL")
            return
        if not path:
            reportar_error("Falta la carpeta de destino")
            return

        # Bloquear botones mientras verificamos
        btn_descargar.disabled = True
        btn_descargar.text = "Verificando..."
        btn_descargar.update()
        
        btn_cancelar.disabled = False
        btn_cancelar.bgcolor = ft.Colors.RED
        btn_cancelar.update()
        
        cancel_event.clear()

        threading.Thread(target=verificar_y_descargar, args=(url, path), daemon=True).start()

    def cancelar_proceso(e):
        cancel_event.set()
        actualizar_estado("Cancelando... espera un momento.")
        btn_cancelar.disabled = True
        btn_cancelar.bgcolor = "#500000"
        btn_cancelar.update()
        
        if panel_confirmacion.visible:
            reset_ui()

    def verificar_y_descargar(url, path):

        is_playlist, num_videos = logic.check_url_type_blocking(url)
        
        if cancel_event.is_set():
            actualizar_estado("Operación cancelada.")
            reset_ui()
            return

        if is_playlist:
            # --- MODO PLAYLIST DETECTADO ---
            
            temp_playlist_data["url"] = url
            temp_playlist_data["path"] = path
            
            lbl_confirmacion.value = f"¡Playlist detectada! ¿Descargar los {num_videos} videos?"
            
            fila_botones_principales.visible = False
            panel_confirmacion.visible = True
            page.update()
            
        else:
            # --- MODO VIDEO ÚNICO ---
            logic.descargar(url, path, es_playlist=False)
            reset_ui()

    def confirmar_playlist_si(e):
        # El usuario dijo SÍ en el panel
        panel_confirmacion.visible = False
        fila_botones_principales.visible = True
        btn_descargar.text = "Descargando Playlist..."
        page.update()
        
        url = temp_playlist_data["url"]
        path = temp_playlist_data["path"]
        
        threading.Thread(target=lambda: logic.descargar(url, path, es_playlist=True), daemon=True).start()

    def confirmar_playlist_no(e):
        reset_ui()
        actualizar_estado("Descarga de playlist cancelada.")

    # --- COMPONENTES VISUALES ---

    lbl_titulo = ft.Text("YouTube Downloader", size=30, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE)
    
    input_url = ft.TextField(
        label="URL del Video", 
        hint_text="https://youtube.com/watch?v=...",
        prefix_icon=ft.Icons.LINK,
        width=500
    )
    
    selector_archivos = ft.FilePicker(on_result=al_seleccionar_carpeta)
    page.overlay.append(selector_archivos)

    input_ruta = ft.TextField(
        value=config_path,
        label="Carpeta de Destino",
        prefix_icon=ft.Icons.FOLDER,
        width=400,
        read_only=True
    )
    
    btn_carpeta = ft.ElevatedButton("Examinar", icon=ft.Icons.FOLDER_OPEN, on_click=abrir_selector)

    # --- GRUPO 1: Botones Principales (Normales) ---
    btn_descargar = ft.ElevatedButton(
        "DESCARGAR", 
        icon=ft.Icons.DOWNLOAD, 
        on_click=iniciar_proceso,
        bgcolor=ft.Colors.BLUE,
        color=ft.Colors.WHITE,
        width=200,
        height=50
    )

    btn_cancelar = ft.ElevatedButton(
        "CANCELAR",
        icon=ft.Icons.CANCEL,
        on_click=cancelar_proceso,
        bgcolor="#500000",
        color=ft.Colors.WHITE,
        width=150,
        height=50,
        disabled=True
    )
    
    fila_botones_principales = ft.Row(
        [btn_descargar, btn_cancelar], 
        alignment=ft.MainAxisAlignment.CENTER, 
        spacing=20
    )

    # --- GRUPO 2: Panel de Confirmación Playlist (Oculto al inicio) ---
    lbl_confirmacion = ft.Text("¿Descargar playlist?", size=16, weight=ft.FontWeight.BOLD)
    
    btn_si_playlist = ft.ElevatedButton(
        "Sí, descargar todo", 
        bgcolor=ft.Colors.GREEN, 
        color=ft.Colors.WHITE,
        on_click=confirmar_playlist_si
    )
    
    btn_no_playlist = ft.TextButton(
        "No, cancelar", 
        style=ft.ButtonStyle(color=ft.Colors.RED),
        on_click=confirmar_playlist_no
    )
    
    panel_confirmacion = ft.Column(
        [
            lbl_confirmacion,
            ft.Row([btn_si_playlist, btn_no_playlist], alignment=ft.MainAxisAlignment.CENTER)
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        visible=False
    )

    progress_bar = ft.ProgressBar(width=500, value=0)
    txt_estado = ft.Text("Listo para descargar.", color=ft.Colors.GREY)

    # --- ARMADO DEL LAYOUT ---
    page.add(
        ft.Column(
            [
                ft.Container(height=20),
                lbl_titulo,
                ft.Container(height=20),
                input_url,
                ft.Row([input_ruta, btn_carpeta], alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(height=20),
                
                fila_botones_principales,
                panel_confirmacion,
                
                ft.Container(height=20),
                progress_bar,
                txt_estado,
                ft.Container(height=20),
                ft.Text("Desarrollado con ❤️ por LiquiDev (Flet v0.28.3)", size=12, italic=True)
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )
    )

if __name__ == "__main__":
    ft.app(target=main)