import errno
import fcntl
import os
import random
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, MofNCompleteColumn

from yt_dlp.utils import DownloadCancelled

from src.core.download import YTDLP
from src.usb import space
from src.usb.db import (
    ensure_schema,
    get_average_duration,
    set_pending,
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


class SyncEnCurso(Exception):
    """Ya hay otro proceso sincronizando esta USB."""


class USBDesconectada(DownloadCancelled):
    """
    La USB se desconectó durante el sync.
    Hereda de DownloadCancelled para que yt-dlp NO la ignore (ignoreerrors) y
    aborte toda la descarga en vez de seguir con las demás canciones.

    El mensaje va en la clase: cuando se lanza desde match_filter, yt-dlp la vuelve
    a lanzar SIN argumentos (`raise break_err()`) y un mensaje propio se perdería.
    """
    msg = "La USB se desconectó durante el sync. El progreso quedó guardado; se reanudará al volver a conectarla."


class USBLlena(DownloadCancelled):
    """
    No queda espacio en la USB para la siguiente canción.
    Igual que USBDesconectada: hereda de DownloadCancelled para abortar la descarga
    y el mensaje va en la clase porque yt-dlp la relanza sin argumentos.
    """
    msg = "La USB está llena: no hay espacio para la siguiente canción."


class _USBWatch:
    """
    Detecta si la USB sigue conectada.

    Guarda la identidad (st_dev, st_ino) de la carpeta de la USB al empezar. Si la
    carpeta desaparece, o se recrea como carpeta normal en otro disco (yt-dlp crea
    los directorios de salida que falten), o falta el .db, la USB ya no está.
    """

    def __init__(self, usb_root: Path, db_path: Path):
        self.usb_root = usb_root
        self.db_path = db_path
        st = os.stat(usb_root)
        self._id = (st.st_dev, st.st_ino)

    def disponible(self) -> bool:
        try:
            st = os.stat(self.usb_root)
        except OSError:
            return False
        return (st.st_dev, st.st_ino) == self._id and self.db_path.is_file()

    def verificar(self) -> None:
        if not self.disponible():
            raise USBDesconectada()


@contextmanager
def _sync_lock(db_path: Path):
    """
    Lock exclusivo por USB con flock sobre el propio .db (no crea archivos extra).

    - Es independiente de los locks POSIX (fcntl) que usa SQLite: no interfiere.
    - El kernel lo libera si el proceso muere: nunca queda "trabado".
    - No bloqueante: si otro proceso lo tiene, lanza SyncEnCurso.
    """
    f = open(db_path, "rb")
    try:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SyncEnCurso(f"Ya hay un sync en curso para {db_path.parent.name}") from None
        yield
    finally:
        f.close()  # cerrar el descriptor libera el flock


def sync_usb(db_path: Path) -> bool:
    """
    Sincroniza la USB con un lock exclusivo: dos syncs simultáneos sobre la misma
    USB (udev disparando dos veces, opción 6 + servicio...) no pueden pisarse.
    Lanza SyncEnCurso si otro proceso ya la está sincronizando.
    """
    with _sync_lock(db_path):
        watch = _USBWatch(db_path.parent, db_path)
        try:
            ensure_schema(db_path)
            ok = _sync_usb(db_path, watch)
            _resumen_espacio(db_path)
            return ok
        except USBLlena:
            _avisar_llena(db_path)
            raise
        except (OSError, sqlite3.Error) as e:
            # Errores de I/O o de SQLite con la USB ausente: es una desconexión
            if not watch.disponible():
                raise USBDesconectada() from e
            # ENOSPC / "database or disk is full" con poco espacio: USB llena
            if _sin_espacio(db_path.parent, e):
                _avisar_llena(db_path)
                raise USBLlena() from e
            raise


def _sin_espacio(usb_root: Path, error: Exception) -> bool:
    """¿El error se debe a falta de espacio en la USB?"""
    if isinstance(error, OSError) and error.errno == errno.ENOSPC:
        return True
    try:
        libre, _ = space.espacio(usb_root)
    except OSError:
        return False
    return "full" in str(error).lower() and libre < space.RESERVA * 2


def _avisar_llena(db_path: Path) -> None:
    """Informa que la USB se llenó, guarda los pendientes y muestra el espacio."""
    console.print(f"\n[red]{USBLlena.msg} El sync se detuvo.[/]")
    _registrar_pendientes(db_path)
    _resumen_espacio(db_path, llena=True)


def _registrar_pendientes(db_path: Path) -> None:
    """
    Calcula cuántas canciones faltan (respetando max_tracks) y su tamaño estimado,
    y lo guarda en la BD para mostrarlo en el menú. Pide la playlist "plana"
    (sin descargar nada); si falla (sin red), lo deja como desconocido.
    """
    try:
        row = get_playlist(db_path)
        info = YTDLP().get_playlist_info(row["url"], to_db=True)
        max_tracks = row["max_tracks"]
        ya = get_downloaded_ids(db_path)
        faltan = [
            e for i, e in enumerate(info["entries"], 1)
            if e.get("id") and e["id"] not in ya and (not max_tracks or i <= max_tracks)
        ]
        size = space.estimar_total(e.get("duration") for e in faltan)
        set_pending(db_path, len(faltan), size)
        console.print(
            f"[yellow]Faltan {space.plural(len(faltan), 'canción', 'canciones')} (~{space.humano(size)}). "
            f"Libera espacio en la USB y vuelve a sincronizar.[/]"
        )
    except Exception as e:
        console.print(f"[dim]No se pudo calcular cuántas canciones faltan: {e}[/]")


def _resumen_espacio(db_path: Path, llena: bool = False) -> None:
    """
    Muestra el espacio libre al terminar y avisa si queda poco.
    Con `llena=True` no muestra "≈ N canciones más" (contradiría el aviso de USB llena).
    """
    try:
        libre, total = space.espacio(db_path.parent)
        promedio = get_average_duration(db_path)
    except (OSError, sqlite3.Error):
        return
    mas = space.canciones_mas(libre, promedio)
    nv = space.nivel(libre, total)
    color = space.COLOR_NIVEL[nv]
    estimacion = "" if llena else f" (≈ {space.plural(mas, 'canción más', 'canciones más')})"
    console.print(
        f"[{color}]Espacio libre en la USB: {space.humano(libre)} de {space.humano(total)}{estimacion}[/]"
    )
    if nv != "ok" and not llena:
        console.print("[yellow]⚠ Queda poco espacio en la USB.[/]")


def _sync_usb(db_path: Path, watch: _USBWatch) -> bool:
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

    url        = playlist_row["url"]
    title      = playlist_row["title"]
    max_tracks = playlist_row["max_tracks"]
    usb_root   = db_path.parent

    ytdlp = YTDLP(outtmpl=str(usb_root / "%(title)s-[%(id)s].%(ext)s"))

    # Retomar desde donde quedó (por defecto 1)
    start_offset    = get_sync_offset(db_path)
    total_before    = get_downloaded_count(db_path)
    total_this_sync = 0
    failed_total    = 0

    console.rule(f"[bold]{title}[/]")
    console.print(f"[dim]Cookies: {ytdlp.cookies_source}[/]")
    console.print(f"[dim]Descargadas hasta ahora: {total_before}[/]")

    if max_tracks:
        console.print(f"[dim]Límite: solo las primeras {max_tracks} canciones de la playlist.[/]")

    if start_offset > 1:
        console.print(f"[yellow]Reanudando desde el índice {start_offset}...[/]")

    def antes_de_cada_cancion(info: dict, incomplete: bool = False) -> None:
        """match_filter: antes de escribir nada, ¿sigue la USB y hay espacio?"""
        watch.verificar()
        if incomplete:
            return None
        libre, _ = space.espacio(usb_root)
        if not space.cabe_siguiente(libre, info.get("duration")):
            raise USBLlena()
        return None

    offset = start_offset

    while True:
        watch.verificar()
        console.print(f"\n[bold cyan]Bloque {offset}–{offset + PAGE_SIZE - 1}[/] — obteniendo metadata...")

        try:
            page = ytdlp.get_playlist_page(url, start=offset, page_size=PAGE_SIZE)
        except Exception as e:
            console.print(f"[red]Error al obtener bloque: {e}[/]")
            console.print("[yellow]Guardando offset y abortando. Se reanudará en el próximo sync.[/]")
            set_sync_offset(db_path, offset)
            return False

        entries = page.get("entries", [])

        # Con límite de canciones: lo que pase de max_tracks se ignora
        if max_tracks:
            entries = [
                e for i, e in enumerate(entries)
                if (e.get("index") or offset + i) <= max_tracks
            ]

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

        durations = {e["id"]: e.get("duration") for e in entries if e.get("id")}
        size = space.estimar_total(durations.get(v) for v in pending)
        libre, _ = space.espacio(usb_root)
        console.print(
            f"[dim]{len(pending)} por descargar, ~{space.humano(size)} "
            f"({len(positions) - len(pending)} ya en la USB) · libre: {space.humano(libre)}[/]"
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

                # Si la USB ya no está, abortar (no registrar ni seguir descargando)
                watch.verificar()

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
                    # Antes de cada canción (antes de escribir nada): ¿sigue la USB? ¿hay espacio?
                    match_filter=antes_de_cada_cancion,
                    sleep_range=(2, 8),
                    concurrent=2,
                )
            except (USBDesconectada, USBLlena):
                raise
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
