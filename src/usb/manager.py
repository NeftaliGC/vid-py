from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt

from src.core.download import YTDLP
from src.usb.detector import get_mounted_usbs, is_vidpy_usb, get_db_path
from src.usb.db import init_db, insert_playlist
from src.usb.sync import sync_usb

console = Console()


def _select_usb() -> Path | None:
    """Muestra las USBs montadas y deja al usuario elegir una."""
    usbs = get_mounted_usbs()

    if not usbs:
        console.print("[red]No se detectaron USBs montadas.[/]")
        return None

    console.print("\n[bold]USBs detectadas:[/]")
    for i, usb in enumerate(usbs, 1):
        tag = "[green](vidpy)[/]" if is_vidpy_usb(usb) else "[dim](nueva)[/]"
        console.print(f"  {i}. {usb.name}  {tag}")

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

    console.print(f"\n[bold]Playlist:[/] {playlist_title}")
    console.print(f"[bold]Canciones:[/] {info['entries_count']}")
    console.print(f"[bold]DB:[/] {db_path}\n")

    confirm = Prompt.ask("¿Confirmar?", choices=["s", "n"], default="s")
    if confirm != "s":
        console.print("[dim]Cancelado.[/]")
        return

    init_db(db_path)
    insert_playlist(db_path, playlist_id, url, playlist_title)

    console.print("[green]USB registrada. Iniciando descarga inicial...[/]\n")
    sync_usb(db_path)


def auto_sync_all() -> None:
    """
    Escanea todas las USBs montadas y sincroniza las que ya tienen DB vidpy.
    Modo no-interactivo, pensado para udev o alias.
    """
    usbs = get_mounted_usbs()

    if not usbs:
        console.print("[dim]No se detectaron USBs.[/]")
        return

    synced = 0
    for usb in usbs:
        db_path = get_db_path(usb)
        if db_path is None:
            continue

        console.rule(f"[bold]{usb.name}[/]")
        sync_usb(db_path)
        synced += 1

    if synced == 0:
        console.print("[dim]Ninguna USB tiene una playlist registrada.[/]")