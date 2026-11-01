import os
import getpass
from pathlib import Path
from typing import List

from src.usb.db import is_vidpy_db


MOUNT_ROOTS = [
    Path("/mnt"),
    Path(f"/media/{getpass.getuser()}"),
    Path(f"/run/media/{getpass.getuser()}"),
]

def _is_mounted(path: Path) -> bool:
    """Verifica que el path sea un mountpoint real, no una carpeta vacía huérfana."""
    try:
        with open('/proc/mounts') as f:
            return any(line.split()[1] == str(path) for line in f)
    except OSError:
        return False

def get_mounted_usbs() -> List[Path]:
    """
    Escanea los mount points comunes de Linux y retorna
    las USBs actualmente montadas.
    """
    usbs: List[Path] = []
    for root in MOUNT_ROOTS:
        if not root.exists():
            continue
        for entry in root.iterdir():
            if not entry.is_dir():
                continue
            # en /mnt solo considerar carpetas usb-*
            if root == Path("/mnt") and not entry.name.startswith("usb-"):
                continue
            if not _is_mounted(entry):
                continue
            usbs.append(entry)
    return usbs


def get_db_path(usb_path: Path) -> Path | None:
    """
    Retorna el `.db` de vidpy en la raíz de la USB, o None.

    Solo cuenta un `.db` con el esquema de vidpy (`is_vidpy_db`): un `.db` de otra
    aplicación o un Thumbs.db ya no hacen que la USB parezca registrada. Si hubiera
    varios válidos, se toma el primero en orden alfabético (determinista).
    """
    try:
        candidates = sorted(
            f for f in usb_path.iterdir()
            if f.suffix == ".db" and f.is_file()
        )
    except OSError:
        return None

    for f in candidates:
        if is_vidpy_db(f):
            return f
    return None


def is_vidpy_usb(usb_path: Path) -> bool:
    """Verifica si la USB ya tiene una DB de vidpy."""
    return get_db_path(usb_path) is not None
