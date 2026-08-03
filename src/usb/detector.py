import os
import getpass
from pathlib import Path
from typing import List


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


def is_vidpy_usb(usb_path: Path) -> bool:
    """Verifica si la USB ya tiene una DB de vidpy."""
    for f in usb_path.iterdir():
        if f.suffix == ".db":
            return True
    return False


def get_db_path(usb_path: Path) -> Path | None:
    """Retorna el path del .db en la USB, si existe."""
    for f in usb_path.iterdir():
        if f.suffix == ".db":
            return f
    return None