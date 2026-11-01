from typing import Dict, Any
from mutagen.mp3 import MP3
from mutagen.id3 import ID3
from mutagen.id3._frames import TIT2, TPE1, TALB, TDRC, APIC
from PIL import Image
import io
import os
import re
import unicodedata

INVALID_CHARS = r'[<>:"/\\|?*;.]'

############################################################
'''
Reformatea el nombre del archivo para evitar caracteres incompatibles
title = nombre del archivo

return Titulo reformateado sin caracteres incompatibles
'''
def formatTitle(title: str) -> str:
    # Elimina acentos y cualquier carácter no ASCII (emojis incluidos)
    title = (
        unicodedata.normalize("NFKD", title)
        .encode("ascii", "ignore")
        .decode("ascii")
    )

    #Mantener únicamente ASCII imprimible
    title = re.sub(r"[^\x20-\x7E]", " ", title)

    # Reemplazar caracteres inválidos para nombres de archivo
    title = re.sub(r'[<>:"/\\|?*;.]', " ", title)

    # Colapsar espacios
    title = re.sub(r"\s+", " ", title).strip()
    
    return title

############################################################
'''
Permite escribir un nombre a los archivos que descarga el usuario
rot = nombre del video
'''
def title(rot):

    print("¿Deseas cambiar el nombre del archivo?")
    opt = input("1- Si | 2- No: ")

    tit = rot

    if(opt == "1"):

        print("")
        tit = input("Escribe el nombre del archivo: ")

        return tit
    else:
        return tit
    

############################################################
# Sufijos típicos de títulos de YouTube que no forman parte del nombre de la canción:
# (Official Music Video), [Lyrics], (Audio), (Video Oficial), (Visualizer), [HD]...
_TITLE_NOISE = re.compile(
    r'\s*[\(\[][^\)\]]*\b(official|oficial|video|vídeo|audio|lyrics?|letra|'
    r'visuali[sz]er|hd|4k|mv|m/v)\b[^\)\]]*[\)\]]',
    re.IGNORECASE,
)
_YEAR = re.compile(r'\b(19|20)\d{2}\b')


def _extract_year(text: Any) -> str:
    """Primer año (19xx/20xx) que aparezca en el texto, o ''."""
    m = _YEAR.search(str(text or ''))
    return m.group(0) if m else ''


def _year_from_date(date: Any) -> str:
    """Año de una fecha de yt-dlp en formato YYYYMMDD ('20260925' -> '2026'), o ''."""
    date = str(date or '')
    return date[:4] if len(date) >= 4 and date[:4].isdigit() else ''


def _clean_uploader(uploader: str) -> str:
    """'Artista - Topic' / 'ArtistaVEVO' -> 'Artista'."""
    uploader = re.sub(r'\s*-\s*Topic$', '', uploader or '')
    uploader = re.sub(r'\s*VEVO$', '', uploader)
    return uploader.strip()


def _split_title(title: str) -> tuple[str, str]:
    """
    'Artista - Canción (Official Music Video)' -> ('Artista', 'Canción').
    Si no hay separador, regresa ('', título limpio).
    """
    clean = _TITLE_NOISE.sub('', title or '').strip()
    for sep in (' - ', ' – ', ' — '):
        if sep in clean:
            artista, titulo = clean.split(sep, 1)
            return artista.strip(), titulo.strip()
    return '', clean


def _parse_provided(desc: str) -> Dict[str, str]:
    """
    Parsea las descripciones autogeneradas de YouTube Music:

        Provided to YouTube by <sello>
        Canción · Artista1 · Artista2
        Álbum
        ℗ 2026 <sello>
        Released on: 2026-09-25
    """
    lines = [l.strip() for l in desc.splitlines() if l.strip()]
    titulo = artista = album = año = ''

    for i, line in enumerate(lines):
        if ' · ' in line:
            parts = [p.strip() for p in line.split(' · ')]
            titulo = parts[0]
            artista = ', '.join(parts[1:])
            # La línea siguiente suele ser el álbum
            if i + 1 < len(lines):
                album = lines[i + 1]
            break

    # "Released on:" es más precisa que ℗ (año de copyright)
    for prefix in ('Released on:', '℗'):
        for line in lines:
            if line.startswith(prefix):
                año = _extract_year(line)
                if año:
                    break
        if año:
            break

    return {'titulo': titulo, 'artista': artista, 'album': album, 'año': año}


def formatDescription(inf: Dict[str, Any]) -> Dict[str, str]:
    """
    Arma los tags ID3 de una canción a partir del info_dict de yt-dlp.

    Prioridad por campo:
      1. Campos de música que extrae yt-dlp (track, artists, album, release_year);
         vienen en canciones de YouTube Music / canales "- Topic".
      2. Descripción autogenerada "Provided to YouTube by ...".
      3. Respaldo: "Artista - Canción" del título del video (sin "(Official Video)", etc.)
         y el uploader como artista. El álbum queda vacío en vez de repetir el título.
    Nunca lanza excepción por campos faltantes o None.
    """
    desc = inf.get('description') or ''

    artists = inf.get('artists') or ([inf['artist']] if inf.get('artist') else [])
    titulo = inf.get('track') or ''
    artista = ', '.join(str(a) for a in artists if a)
    album = inf.get('album') or ''
    año = _extract_year(inf.get('release_year'))

    if desc.startswith('Provided to YouTube'):
        p = _parse_provided(desc)
        titulo = titulo or p['titulo']
        artista = artista or p['artista']
        album = album or p['album']
        año = año or p['año']

    if not titulo or not artista:
        t_artista, t_titulo = _split_title(inf.get('title') or '')
        titulo = titulo or t_titulo
        artista = artista or t_artista or _clean_uploader(inf.get('uploader') or inf.get('channel') or '')

    año = año or _year_from_date(inf.get('release_date')) or _year_from_date(inf.get('upload_date'))

    return {
        'titulo': titulo,
        'artista': artista,
        'album': album,
        'año': año,
        'filepath': inf.get('filepath') or '',
    }


def set_metadata(metadata: Dict[str, str]):
    
    path = metadata.get('filepath', '')
    
    if not path.endswith('.mp3'):
        return

    audio = MP3(path, ID3=ID3)

    try:
        audio.add_tags()
    except Exception:
        pass

    audio.tags.add(TIT2(encoding=3, text=metadata.get('titulo', ''))) # type: ignore
    audio.tags.add(TPE1(encoding=3, text=metadata.get('artista', ''))) # type: ignore
    audio.tags.add(TALB(encoding=3, text=metadata.get('album', ''))) # type: ignore
    audio.tags.add(TDRC(encoding=3, text=metadata.get('año', ''))) # type: ignore

    cover = find_cover(path, metadata.get('cover'))

    # Si no hay portada (p. ej. el mp3 ya existía), se guardan los tags sin ella
    if cover:
        try:
            data = crop_to_square(cover)
        except Exception as e:
            # Formato que Pillow no sabe abrir u otro error: la canción se queda sin portada
            print(f"No se pudo procesar la portada {cover}: {e}")
        else:
            audio.tags.add( # type: ignore
                APIC(
                    encoding=3,          # UTF-8
                    mime="image/jpeg",   # siempre se re-codifica a JPEG
                    type=3,              # 3 = portada frontal
                    desc="Cover",
                    data=data
                )
            )
            os.remove(cover)

    audio.save()

# Formatos en los que yt-dlp puede guardar la miniatura (writethumbnail)
COVER_EXTS = ('.webp', '.jpg', '.jpeg', '.png', '.avif', '.gif')

def find_cover(mp3_path: str, hint: str | None = None) -> str | None:
    """
    Busca la portada de un mp3.
    1. `hint`: ruta exacta que reportó yt-dlp (info_dict['thumbnails'][*]['filepath']).
    2. Si no existe, `<base del mp3>.<ext>` para cada formato conocido.
    """
    if hint and os.path.exists(hint):
        return hint

    base = os.path.splitext(mp3_path)[0]
    for ext in COVER_EXTS:
        candidate = base + ext
        if os.path.exists(candidate):
            return candidate

    return None

def crop_to_square(input_path: str) -> bytes:
    """Recorta la imagen a cuadrado (centrado) y la devuelve como JPEG en memoria."""
    with Image.open(input_path) as img:
        # Importante: JPG no soporta alpha
        if img.mode != "RGB":
            img = img.convert("RGB")

        w, h = img.size
        size = min(w, h)

        left = (w - size) // 2
        top = (h - size) // 2

        buf = io.BytesIO()
        img.crop((left, top, left + size, top + size)).save(
            buf,
            format="JPEG",
            quality=95,
            subsampling=0
        )

    return buf.getvalue()