import random
import time
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, MofNCompleteColumn

from src.core.download import YTDLP
from src.usb.db import (
    get_playlist,
    get_downloaded_count,
    get_downloaded_ids,
    get_sync_offset,
    set_sync_offset,
    insert_track,
    update_last_synced,
)

console = Console()

PAGE_SIZE        = 50
SLEEP_BETWEEN_BLOCKS = (15, 30)   # segundos entre bloques para no martillar la API


def sync_usb(db_path: Path) -> bool:
    """
    Sincroniza la playlist registrada en la DB contra la USB.

    Estrategia:
    - Pide la playlist en bloques de PAGE_SIZE usando playlist_items
    - Descarga solo las canciones que no están en la tabla `tracks`
      (así un sync completo solo baja lo nuevo y reintenta lo que falló)
    - Registra cada canción cuando su .mp3 ya existe (hook de post-proceso)
    - Guarda sync_offset (índice 1-based de la playlist) por canción y por bloque
    - Para cuando un bloque regresa vacío (fin de playlist)

    Retorna True si llegó al final de la playlist (aunque algunas canciones
    hayan fallado: se reintentan en el próximo sync) y False si abortó antes.
    """
    playlist_row = get_playlist(db_path)

    if playlist_row is None:
        console.print("[red]No se encontró una playlist registrada en esta USB.[/]")
        return False

    url      = playlist_row["url"]
    title    = playlist_row["title"]
    usb_root = db_path.parent

    ytdlp = YTDLP(outtmpl=str(usb_root / "%(title)s-[%(id)s].%(ext)s"))

    # Retomar desde donde quedó (por defecto 1)
    start_offset    = get_sync_offset(db_path)
    total_before    = get_downloaded_count(db_path)
    total_this_sync = 0
    failed_total    = 0

    console.rule(f"[bold]{title}[/]")
    console.print(f"[dim]Cookies: {ytdlp.cookies_source}[/]")
    console.print(f"[dim]Descargadas hasta ahora: {total_before}[/]")

    if start_offset > 1:
        console.print(f"[yellow]Reanudando desde el índice {start_offset}...[/]")

    offset = start_offset

    while True:
        console.print(f"\n[bold cyan]Bloque {offset}–{offset + PAGE_SIZE - 1}[/] — obteniendo metadata...")

        try:
            page = ytdlp.get_playlist_page(url, start=offset, page_size=PAGE_SIZE)
        except Exception as e:
            console.print(f"[red]Error al obtener bloque: {e}[/]")
            console.print("[yellow]Guardando offset y abortando. Se reanudará en el próximo sync.[/]")
            set_sync_offset(db_path, offset)
            return False

        entries = page.get("entries", [])

        if not entries:
            if failed_total:
                console.print(
                    f"[yellow]Fin de la playlist. {failed_total} canciones no se pudieron descargar; "
                    f"se reintentarán en el próximo sync.[/]"
                )
            else:
                console.print("[green]Playlist completamente sincronizada.[/]")
            update_last_synced(db_path)
            return True

        # Posición real (1-based) de cada canción dentro de la playlist.
        # Las entradas nulas/no disponibles también ocupan índice.
        positions: dict[str, int] = {}
        for i, e in enumerate(entries):
            if e.get("id"):
                positions.setdefault(e["id"], e.get("index") or offset + i)

        block_end = offset + PAGE_SIZE   # siguiente índice tras este bloque (rango pedido)

        already = get_downloaded_ids(db_path)
        pending = [vid for vid in positions if vid not in already]

        if not pending:
            console.print("[dim]Todas las canciones de este bloque ya están en la USB.[/]")
            offset = block_end
            set_sync_offset(db_path, offset)
            continue

        console.print(
            f"[dim]{len(pending)} por descargar "
            f"({len(positions) - len(pending)} ya en la USB)[/]"
        )

        registered: set[str] = set()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TaskProgressColumn(),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task(f"Descargando bloque {offset}...", total=len(pending))

            def on_track_ready(d: dict) -> None:
                # MoveFiles (MoveFilesAfterDownloadPP) es el último post-proceso: aquí el .mp3 ya existe
                if d.get("status") != "finished" or d.get("postprocessor") != "MoveFiles":
                    return

                info = d.get("info_dict", {})
                vid  = info.get("id")
                if not vid or vid in registered:
                    return

                try:
                    insert_track(db_path, {
                        "id":       vid,
                        "title":    info.get("title", ""),
                        "duration": info.get("duration"),
                    })
                    if vid in positions:
                        # Siguiente índice tras esta canción (1-based, posición real)
                        set_sync_offset(db_path, positions[vid] + 1)
                except Exception as e:
                    # yt-dlp (ignoreerrors) se tragaría la excepción: la mostramos aquí
                    progress.console.print(f"[red]No se pudo registrar {vid} en la DB: {e}[/]")
                    return

                registered.add(vid)
                progress.advance(task)

            try:
                ytdlp.download_audio_playlist_usb(
                    playlist=pending,
                    output_dir=str(usb_root),
                    quality="192",
                    extra_pp_hooks=[on_track_ready],
                    sleep_range=(2, 8),
                    concurrent=2,
                )
            except Exception as e:
                console.print(f"[red]Error durante descarga del bloque: {e}[/]")
                console.print("[yellow]Offset guardado. Se reanudará en el próximo sync.[/]")
                return False

        failed = len(pending) - len(registered)
        failed_total    += failed
        total_this_sync += len(registered)
        offset = block_end
        set_sync_offset(db_path, offset)

        msg = f"[green]✓ Bloque completo.[/] Total descargadas esta sesión: {total_this_sync}"
        if failed:
            msg += f" [yellow]({failed} fallaron en este bloque)[/]"
        console.print(msg)

        # Pausa entre bloques para no saturar la API
        sleep_secs = random.randint(*SLEEP_BETWEEN_BLOCKS)
        console.print(f"[dim]Esperando {sleep_secs}s antes del próximo bloque...[/]")
        time.sleep(sleep_secs)
