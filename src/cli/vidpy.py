from src.core.download import YTDLP
from src.usb.manager import register_usb, auto_sync_all
import time
from rich.live import Live
from rich.text import Text
from rich.console import Console
from rich.prompt import Prompt, IntPrompt
from pathlib import Path

console = Console()

# Mensajes de validación de Rich en español (por defecto vienen en inglés)
Prompt.illegal_choice_message = "[prompt.invalid.choice]Selecciona una de las opciones disponibles"
IntPrompt.validate_error_message = "[prompt.invalid]Escribe un número entero"

def menu(cookies_source: str | None = None):
    console.clear()
    console.rule("[bold]Vid-Py CLI Youtube Downloader[/]")
    if cookies_source:
        console.print(f"[dim]Cookies: {cookies_source}[/]")
    console.print("")
    console.print("1- Solo audio")
    console.print("2- Video")
    console.print("3- Descargar playlist de musica completa")
    console.print("4- Instrucciones")
    console.print("")
    console.print("[bold cyan]--- USB ---[/]")
    console.print("5- Registrar USB con playlist")
    console.print("6- Sincronizar USBs conectadas")
    console.print("")
    console.print("0- Salir")

    return Prompt.ask(
        "\nSelecciona una opción",
        choices=["1", "2", "3", "4", "5", "6", "0"]
    )

def countdown(segundos=3):
    with Live(refresh_per_second=4) as live:
        for i in range(segundos, 0, -1):
            live.update(
                Text(f"Volviendo al menú en {i}...", style="dim")
            )
            time.sleep(1)

def esperar_usuario():
    console.print("\n[green]Presiona Enter para volver al menú...[/]")
    input()

def pedir_indice(total: int) -> int:
    """
    Pide un índice 1-based entre 1 y `total`, repitiendo hasta que sea válido.
    (Con int() directo: texto => ValueError, 0 => solo la última canción,
    negativos => desde el final, mayor al total => 0 canciones.)
    """
    while True:
        n = IntPrompt.ask(f"Escribe el número de la canción desde donde descargar (1-{total})")
        if 1 <= n <= total:
            return n
        console.print(f"[red]Debe ser un número entre 1 y {total}.[/]")

def informar_resultado(ret: int, ok_msg: str, error_msg: str, warning: bool = False) -> None:
    """
    Muestra el resultado de una descarga según el código de yt-dlp (0 = éxito).
    Con error se espera Enter para que el usuario alcance a leer el mensaje.
    """
    if ret == 0:
        console.print(f"[green]{ok_msg}[/]")
        countdown(3)
    else:
        color = "yellow" if warning else "red"
        console.print(f"\n[{color}]{error_msg}[/]")
        esperar_usuario()

def main():

    cwd = Path.cwd()
    ytdlp = YTDLP(outtmpl=f'{cwd}/%(title)s-[%(id)s].%(ext)s', cookies_from_browser='firefox')

    while True:
        opt =  menu(ytdlp.cookies_source)

        if(opt == "1"):

            link = input("Escribe el link de la cancion: ")
            
            with console.status("[bold]Descargando canción...[/]"):
                ret = ytdlp.download_audio_mp3(link, quality='192')

            informar_resultado(
                ret,
                "Cancion descargada con exito.",
                "No se pudo descargar la canción. Revisa el link o las cookies.",
            )

        elif(opt == "2"):
            link = input("Escribe el link del video: ")

            try:
                with console.status("[bold]Obteniendo información del video...[/]"):
                    info = ytdlp.get_info(link)
            except ValueError as e:
                console.print(f"\n[red]{e}[/]")
                esperar_usuario()
                continue

            console.print(f"\n[bold]Título del video:[/] {info.get('title', 'Video')}\n")
            choices = [f'{r}p' for r in info.get('resolutions', []) if r > 100 and r != 180]

            if not choices:
                console.print("[red]El video no tiene resoluciones de video disponibles para descargar.[/]")
                esperar_usuario()
                continue

            res = Prompt.ask("¿Qué resolución deseas descargar?", choices=choices)

            height = int(res.removesuffix('p'))

            if height > 720:
                console.print("[yellow]Nota: Se detectó alta resolución, el formato de descarga será MKV.[/]")
                preset = 'mkv_4k'
            else:
                preset = 'mp4_compat'
            
            with console.status("[bold]Descargando video...[/]"):
                ret = ytdlp.download_video_mp4(link, resolution=height, preset=preset)

            informar_resultado(
                ret,
                "Video descargado con exito.",
                "No se pudo descargar el video. Revisa el link o las cookies.",
            )

        elif(opt == "3"):
            link = input("Escribe el link de la playlist de musica: ")

            try:
                with console.status("[bold]Obteniendo información de la playlist...[/]"):
                    playlist = ytdlp.get_playlist_info(link, to_db=True)
            except ValueError as e:
                console.print(f"\n[red]{e}[/]")
                esperar_usuario()
                continue

            console.print(f"\n[bold]{playlist['title']}[/]")
            console.print(f"[bold]Cantidad de canciones:[/] {len(playlist['entries'])}\n")
            ids = [entry['id'] for entry in playlist['entries'] if entry.get('id')]

            index = Prompt.ask(
                "¿Qué deseas descargar? [bold]1[/] = toda la playlist, "
                "[bold]2[/] = desde una canción en adelante",
                choices=["1", "2"]
            )

            if index == "2":
                start_index = pedir_indice(len(ids))
                ids = ids[start_index - 1:]
                if len(ids) == 1:
                    console.print(f"[dim]Se descargará 1 canción (la {start_index}).[/]")
                else:
                    console.print(f"[dim]Se descargarán {len(ids)} canciones (de la {start_index} a la {start_index + len(ids) - 1}).[/]")

            with console.status("[bold]Descargando playlist[/], [yellow]esto puede tardar dependiendo del tamaño de la lista[/]"):
                ret = ytdlp.download_audio_playlist(ids, output_dir=f'{cwd}/{playlist["title"]}', quality='192')

            # En una playlist, ret != 0 significa que AL MENOS una canción falló
            informar_resultado(
                ret,
                "Playlist descargada con exito.",
                "Algunas canciones de la playlist no se pudieron descargar (revisa los errores de arriba).",
                warning=True,
            )

        elif(opt == "4"):
            console.print("\n[bold]Instrucciones de uso:[/]")
            console.print("""
                1. Selecciona la opción deseada en el menú principal.
                2. Proporciona el enlace del video o canción cuando se te solicite.
                3. Selecciona la resolución que desees descargar.
                4. Espera a que la descarga se complete.
                5. Los archivos descargados se guardarán en el directorio actual.
                6. ¡Disfruta de tu contenido descargado!
            """)
            console.print("-----------------------------------------------------------------")

            esperar_usuario()

        elif opt == "5":
            register_usb()
            esperar_usuario()

        elif opt == "6":
            auto_sync_all()
            esperar_usuario()

        elif(opt == "0"):
            console.print("\n[green]Gracias por usar el programa...[/]")
            break

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "sync":
        # Modo no-interactivo para systemd/udev: sincroniza todas las USBs sin menú
        auto_sync_all()
    else:
        main()