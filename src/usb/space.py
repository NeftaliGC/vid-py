"""
Espacio libre en la USB y estimaciones de tamaño de las canciones.

Las canciones se guardan como mp3 a 192 kbps (24 KB por segundo de audio) más la
portada incrustada, así que el tamaño se puede estimar con la duración que ya
viene en la info "plana" de la playlist, sin descargar nada.
"""
import shutil
from pathlib import Path
from typing import Iterable, Optional

BYTES_POR_SEGUNDO    = 192_000 // 8       # mp3 a 192 kbps
EXTRA_POR_CANCION    = 150 * 1024         # portada incrustada + tags ID3 (aprox.)
DURACION_DESCONOCIDA = 240                # si no se conoce la duración: 4 min

# Durante la conversión conviven el audio original (m4a/opus) y el mp3:
# se pide el doble del tamaño estimado antes de empezar cada canción.
FACTOR_TEMPORAL = 2

RESERVA            = 50 * 1024**2         # margen que nunca se llena (FAT/BD/sistema)
UMBRAL_AVISO_BYTES = 200 * 1024**2        # aviso de "poco espacio" por debajo de esto...
UMBRAL_AVISO_PCT   = 0.10                 # ...o por debajo del 10 % de la USB


def estimar_cancion(duration: Optional[float]) -> int:
    """Tamaño aproximado del mp3 final de una canción, en bytes."""
    segundos = duration if duration and duration > 0 else DURACION_DESCONOCIDA
    return int(segundos * BYTES_POR_SEGUNDO) + EXTRA_POR_CANCION


def estimar_total(durations: Iterable[Optional[float]]) -> int:
    return sum(estimar_cancion(d) for d in durations)


def espacio(path: Path) -> tuple[int, int]:
    """(bytes libres, bytes totales) del sistema de archivos donde está `path`."""
    uso = shutil.disk_usage(path)
    return uso.free, uso.total


def canciones_que_caben(durations: Iterable[Optional[float]], libre: int) -> int:
    """
    Cuántas canciones, en orden, se pueden descargar con `libre` bytes.
    Usa el mismo criterio que el sync (cabe_siguiente): cada canción necesita
    espacio temporal extra mientras se convierte, sin tocar la RESERVA.
    """
    n = 0
    for d in durations:
        if not cabe_siguiente(libre, d):
            break
        libre -= estimar_cancion(d)
        n += 1
    return n


def cabe_siguiente(libre: int, duration: Optional[float]) -> bool:
    """¿Hay espacio para descargar y convertir una canción más sin tocar la RESERVA?"""
    return libre - estimar_cancion(duration) * FACTOR_TEMPORAL >= RESERVA


def humano(n: Optional[int]) -> str:
    """1234567 -> '1.2 MB'."""
    if n is None:
        return "?"
    valor = float(n)
    for unidad in ("B", "KB", "MB", "GB", "TB"):
        if abs(valor) < 1024 or unidad == "TB":
            return f"{valor:.0f} {unidad}" if unidad in ("B", "KB") else f"{valor:.1f} {unidad}"
        valor /= 1024
    return f"{valor:.1f} TB"


def nivel(libre: int, total: int) -> str:
    """'critico' (casi llena), 'bajo' (poco espacio) u 'ok'."""
    if libre < RESERVA * 2:
        return "critico"
    if libre < max(UMBRAL_AVISO_BYTES, total * UMBRAL_AVISO_PCT):
        return "bajo"
    return "ok"


COLOR_NIVEL = {"ok": "green", "bajo": "yellow", "critico": "red"}


def describir(path: Path) -> str:
    """'3.2 GB libres de 14.9 GB' con color según el nivel (markup de Rich)."""
    try:
        libre, total = espacio(path)
    except OSError:
        return "[dim]espacio desconocido[/]"
    color = COLOR_NIVEL[nivel(libre, total)]
    return f"[{color}]{humano(libre)} libres[/] de {humano(total)}"


def canciones_mas(libre: int, duracion_promedio: Optional[float] = None) -> int:
    """Cuántas canciones más (aprox.) caben en el espacio libre (mismo criterio que el sync)."""
    return canciones_que_caben(iter(lambda: duracion_promedio, object()), libre)


def plural(n: int, singular: str, plural_: str) -> str:
    """plural(1, 'canción', 'canciones') -> '1 canción'."""
    return f"{n} {singular if n == 1 else plural_}"
