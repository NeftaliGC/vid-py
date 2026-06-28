import time
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, MofNCompleteColumn

from src.core.download import YTDLP
from src.usb.db import (
    get_playlist,
    get_downloaded_count,
    get_sync_offset,
    set_sync_offset,
    insert_track,
    update_last_synced,
)

console = Console()

PAGE_SIZE        = 50
SLEEP_BETWEEN_BLOCKS = (15, 30)   # segundos entre bloques para no martillar la API


def sync_usb(db_path: Path) -> None:
    """
    Sincroniza la playlist registrada en la DB contra la USB.

    Estrategia:
    - Pide la playlist en bloques de PAGE_SIZE usando playlist_items
    - Descarga cada bloque con throttle + sleep aleatorio entre canciones
    - Guarda sync_offset en DB al terminar cada bloque (resume-safe)
    - Para cuando un bloque regresa vacío (fin de playlist)
    """
    playlist_row = get_playlist(db_path)

    if playlist_row is None:
        console.print("[red]No se encontró una playlist registrada en esta USB.[/]")
        return

    url      = playlist_row["url"]
    title    = playlist_row["title"]
    usb_root = db_path.parent

    ytdlp = YTDLP(outtmpl=str(usb_root / "%(title)s.%(ext)s"))

    # Retomar desde donde quedó (por defecto 1)
    start_offset    = get_sync_offset(db_path)
    total_before    = get_downloaded_count(db_path)
    total_this_sync = 0

    console.rule(f"[bold]{title}[/]")
    console.print(f"[dim]Descargadas hasta ahora: {total_before}[/]")

    if start_offset > 1:
        console.print(f"[yellow]Reanudando desde bloque en índice {start_offset}...[/]")

    offset = start_offset

    while True:
        console.print(f"\n[bold cyan]Bloque {offset}–{offset + PAGE_SIZE - 1}[/] — obteniendo metadata...")

        try:
            page = ytdlp.get_playlist_page(url, start=offset, page_size=PAGE_SIZE)
        except Exception as e:
            console.print(f"[red]Error al obtener bloque: {e}[/]")
            console.print("[yellow]Guardando offset y abortando. Se reanudará en el próximo sync.[/]")
            set_sync_offset(db_path, offset)
            return

        entries = page.get("entries", [])

        if not entries:
            console.print("[green]Playlist completamente sincronizada.[/]")
            update_last_synced(db_path)
            return

        ids = [e["id"] for e in entries if e.get("id")]

        if not ids:
            console.print("[dim]Bloque sin IDs válidos, saltando...[/]")
            offset += PAGE_SIZE
            set_sync_offset(db_path, offset)
            continue

        console.print(f"[dim]{len(ids)} canciones en este bloque[/]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TaskProgressColumn(),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task(f"Descargando bloque {offset}...", total=len(ids))

            def on_track_finished(d: dict) -> None:
                if d["status"] != "finished":
                    return

                info = d.get("info_dict", {})
                insert_track(db_path, {
                    "id":       info.get("id", ""),
                    "title":    info.get("title", ""),
                    "duration": info.get("duration"),
                })
                progress.advance(task)

            try:
                ytdlp.download_audio_playlist_usb(
                    playlist=ids,
                    output_dir=str(usb_root),
                    quality="192",
                    extra_hooks=[on_track_finished],
                    sleep_range=(2, 8),
                    throttle_rate="2M",
                    concurrent=2,
                )
            except Exception as e:
                console.print(f"[red]Error durante descarga del bloque: {e}[/]")
                console.print("[yellow]Guardando offset. Se reanudará aquí en el próximo sync.[/]")
                set_sync_offset(db_path, offset)
                return

        total_this_sync += len(ids)
        offset += PAGE_SIZE
        set_sync_offset(db_path, offset)

        console.print(
            f"[green]✓ Bloque completo.[/] "
            f"Total descargadas esta sesión: {total_this_sync}"
        )

        # Pausa entre bloques para no saturar la API
        sleep_secs = __import__('random').randint(*SLEEP_BETWEEN_BLOCKS)
        console.print(f"[dim]Esperando {sleep_secs}s antes del próximo bloque...[/]")
        time.sleep(sleep_secs)