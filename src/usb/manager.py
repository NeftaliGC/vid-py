from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt

from src.core.download import YTDLP
from src.usb.detector import get_mounted_usbs, is_vidpy_usb, get_db_path
from src.usb import space
from src.usb.db import init_db, insert_playlist, set_max_tracks, read_status
from src.usb.sync import sync_usb, SyncEnCurso, USBDesconectada, USBLlena

console = Console()


def _select_usb() -> Path | None:
    """Muestra las USBs montadas y deja al usuario elegir una."""
    usbs = get_mounted_usbs()

    if not usbs:
        console.print("[red]No se detectaron USBs montadas.[/]")
        return None

    console.print("\n[bold]USBs detectadas:[/]")
    for i, usb in enumerate(usbs, 1):
        db_path = get_db_path(usb)
        tag = "[green](vidpy)[/]" if db_path else "[dim](nueva)[/]"
        console.print(f"  {i}. {usb.name}  {tag} — {space.describir(usb)}")
        status = read_status(db_path) if db_path else None
        if status:
            limite = f" · límite: primeras {status['max_tracks']}" if status["max_tracks"] else ""
            console.print(f"     [dim]{status['title']} · {status['tracks']} canciones{limite}[/]")
            if status["pending_count"]:
                console.print(
                    f"     [yellow]⚠ {space.plural(status['pending_count'], 'canción pendiente', 'canciones pendientes')} por falta de espacio "
                    f"(~{space.humano(status['pending_bytes'])})[/]"
                )

    choice = Prompt.ask(
        "\nSelecciona una USB",
        choices=[str(i) for i in range(1, len(usbs) + 1)]
    )

    return usbs[int(choice) - 1]


def register_usb() -> None:
    """
    Flujo para registrar una playlist en una USB nueva.
    Crea la DB, inserta la playlist y descarga desde cero.
    """
    console.rule("[bold]Registrar USB[/]")

    usb = _select_usb()
    if usb is None:
        return

    if is_vidpy_usb(usb):
        console.print("[yellow]Esta USB ya tiene una playlist registrada.[/]")
        console.print("[dim]Usa 'sync' para actualizarla.[/]")
        return

    url = Prompt.ask("\nURL de la playlist de YouTube")

    ytdlp = YTDLP()

    with console.status("[bold]Obteniendo info de la playlist...[/]"):
        try:
            info = ytdlp.get_playlist_info(url, to_db=True)
        except ValueError as e:
            console.print(f"[red]Error: {e}[/]")
            return

    playlist_id    = info["id"]
    playlist_title = info["title"]
    db_path        = usb / f"{playlist_id}.db"

    durations = [e.get("duration") for e in info["entries"]]
    total     = space.estimar_total(durations)
    libre, _  = space.espacio(usb)

    console.print(f"\n[bold]Playlist:[/] {playlist_title}")
    console.print(f"[bold]Canciones:[/] {info['entries_count']}")
    console.print(f"[bold]Tamaño estimado:[/] ~{space.humano(total)} [dim](mp3 a 192 kbps)[/]")
    console.print(f"[bold]Libre en la USB:[/] {space.describir(usb)}")
    console.print(f"[bold]DB:[/] {db_path}\n")

    max_tracks = None
    if total + space.RESERVA > libre:
        caben = space.canciones_que_caben(durations, libre)
        if caben == 0:
            console.print("[red]No hay espacio ni para una canción. Libera espacio en la USB.[/]")
            return

        size_caben = space.estimar_total(durations[:caben])
        console.print(
            f"[yellow]⚠ La playlist no cabe completa: caben aprox. {caben} de "
            f"{info['entries_count']} canciones (~{space.humano(size_caben)}).[/]"
        )
        opcion = Prompt.ask(
            f"[bold]1[/] = descargar solo las primeras {caben} (recomendado), "
            f"[bold]2[/] = registrar toda (el sync se detendrá al llenarse), [bold]0[/] = cancelar",
            choices=["1", "2", "0"], default="1",
        )
        if opcion == "0":
            console.print("[dim]Cancelado.[/]")
            return
        if opcion == "1":
            max_tracks = caben
    else:
        confirm = Prompt.ask("¿Confirmar?", choices=["s", "n"], default="s")
        if confirm != "s":
            console.print("[dim]Cancelado.[/]")
            return

    init_db(db_path)
    insert_playlist(db_path, playlist_id, url, playlist_title)
    if max_tracks:
        set_max_tracks(db_path, max_tracks)

    console.print("[green]USB registrada. Iniciando descarga inicial...[/]\n")
    try:
        sync_usb(db_path)
    except SyncEnCurso:
        console.print("[yellow]Ya hay un sync en curso para esta USB (otro proceso).[/]")
    except USBDesconectada as e:
        console.print(f"[yellow]{e.msg}[/]")  # msg de la clase (ver USBDesconectada)
    except USBLlena:
        pass  # sync_usb ya informó el espacio y los pendientes


def auto_sync_all() -> int:
    """
    Escanea todas las USBs montadas y sincroniza las que ya tienen DB vidpy.
    Modo no-interactivo, pensado para udev o alias.

    Cada USB se sincroniza aislada: si una falla (USB defectuosa, error de I/O,
    BD dañada, red...) se informa y se continúa con las demás.
    Retorna cuántas USBs fallaron o quedaron incompletas (0 = todo bien).
    """
    usbs = get_mounted_usbs()

    if not usbs:
        console.print("[dim]No se detectaron USBs.[/]")
        return 0

    ok: list[str] = []
    failed: list[tuple[str, str]] = []
    skipped: list[str] = []

    for usb in usbs:
        db_path = get_db_path(usb)
        if db_path is None:
            continue

        console.rule(f"[bold]{usb.name}[/]")
        try:
            if sync_usb(db_path):
                ok.append(usb.name)
            else:
                failed.append((usb.name, "sync incompleto, se reanudará en el próximo sync"))
        except USBDesconectada:
            console.print(f"[yellow]La USB {usb.name} se desconectó durante el sync. "
                          f"El progreso quedó guardado; se reanudará al volver a conectarla.[/]")
            failed.append((usb.name, "USB desconectada durante el sync; se reanudará al reconectarla"))
        except USBLlena:
            # sync_usb ya informó el espacio y los pendientes
            status = read_status(db_path) or {}
            if status.get("pending_count"):
                motivo = (f"USB llena: faltan {space.plural(status['pending_count'], 'canción', 'canciones')} "
                          f"(~{space.humano(status['pending_bytes'])})")
            else:
                motivo = "USB llena"
            failed.append((usb.name, motivo))
        except SyncEnCurso:
            # Otro proceso ya la está sincronizando: no es un error
            console.print("[yellow]Ya hay un sync en curso para esta USB (otro proceso). Se omite.[/]")
            skipped.append(usb.name)
        except Exception as e:
            # KeyboardInterrupt no es Exception: Ctrl+C sigue deteniendo todo
            console.print(f"[red]Error al sincronizar {usb.name}: {type(e).__name__}: {e}[/]")
            console.print("[yellow]Se continúa con la siguiente USB.[/]")
            failed.append((usb.name, f"{type(e).__name__}: {e}"))

    if not ok and not failed and not skipped:
        console.print("[dim]Ninguna USB tiene una playlist registrada.[/]")
        return 0

    # Resumen (útil en el log de systemd/journalctl)
    if len(ok) + len(failed) + len(skipped) > 1 or failed:
        console.rule("[bold]Resumen[/]")
        for name in ok:
            console.print(f"[green]✓ {name}[/]")
        for name in skipped:
            console.print(f"[yellow]- {name}[/] [dim](omitida: ya se estaba sincronizando)[/]")
        for name, reason in failed:
            console.print(f"[red]✗ {name}[/] [dim]({reason})[/]")

    return len(failed)
