from src.core.download import YTDLP
from src.usb.manager import register_usb, auto_sync_all
import time
from rich.live import Live
from rich.text import Text
from rich.console import Console
from rich.prompt import Prompt
from pathlib import Path

console = Console()

def menu():
    console.clear()
    console.rule("[bold]Vid-Py CLI Youtube Downloader[/]")
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

def main():

    cwd = Path.cwd()
    ytdlp = YTDLP(outtmpl=f'{cwd}/%(title)s.%(ext)s')

    while True:
        opt =  menu()

        if(opt == "1"):

            link = input("Escribe el link de la cancion: ")
            
            with console.status("[bold]Descargando canción...[/]"):
                ytdlp.download_audio_mp3(link, quality='192')

            console.print("[green]Cancion descargada con exito.[/]")
            countdown(3)

        elif(opt == "2"):
            link = input("Escribe el link del video: ")

            with console.status("[bold]Obteniendo información del video...[/]"):
                info = ytdlp.get_info(link)
                title = info.get('title', 'Video')
                console.print(f"\n[bold]Título del video:[/] {title}\n")
                resolutions = info.get('resolutions', [])

            res = Prompt.ask(
                "¿Qué resolución deseas descargar?",
                choices=[f'{str(r)}p' for r in resolutions if r > 100 and r != 180]
            )

            if int(res.split('p')[0]) > 720:
                console.print("[yellow]Nota: Se detectó alta resolución, el formato de descarga será MKV.[/]")
                preset = 'mkv_4k'
            else:
                preset = 'mp4_compat'
            
            with console.status("[bold]Descargando video...[/]"):
                ytdlp.download_video_mp4(link, resolution=res, preset=preset)

            console.print("[green]Video descargada con exito.[/]")
            countdown(3)

        elif(opt == "3"):
            link = input("Escribe el link de la playlist de musica: ")

            with console.status("[bold]Obteniendo información de la playlist...[/]"):
                playlist = ytdlp.get_playlist_info(link, to_db=True)
                console.print(f"\n[bold]{playlist['title']}[/]")
                console.print(f"[bold]Cantidad de canciones:[/] {len(playlist['entries'])}\n")
                ids = [entry['id'] for entry in playlist['entries']]

            index = Prompt.ask(
                "¿Deseas descargar toda la playlist o solo desde un indice en adelante?",
                choices=["1", "2"]
            )

            if index == "2":
                start_index = input("Escribe el indice desde donde deseas descargar (Ejemplo: 3): ")
                ids = ids[int(start_index)-1:]

            with console.status("[bold]Descargando playlist[/], [yellow]esto puede tardar dependiendo del tamaño de la lista[/]"):
                ytdlp.download_audio_playlist(ids, output_dir=f'{cwd}/{playlist["title"]}', quality='192')
                
            console.print("[green]Playlist descargada con exito.[/]")

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
    main()