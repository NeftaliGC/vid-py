import os
import getpass
from pathlib import Path
from typing import List


MOUNT_ROOTS = [
    Path(f"/media/{getpass.getuser()}"),
    Path(f"/run/media/{getpass.getuser()}"),
]


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
            if entry.is_dir():
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