from typing import Dict, Any
from mutagen.mp3 import MP3
from mutagen.id3 import ID3
from mutagen.id3._frames import TIT2, TPE1, TALB, TDRC, APIC
from PIL import Image
import os

############################################################
'''
Reformatea el nombre del archivo para evitar caracteres incompatibles
title = nombre del archivo

return Titulo reformateado sin caracteres incompatibles
'''
def formatTitle(title):
    titleFormat = ""
    add = ""

    for char in title:
        for c in {"<", ">", ":", '"', "|", "?", "*", "/", ";", "."}:
            if(char != c):
                add = char
            else:
                add = " "
                break
                
        titleFormat += add
        add = ""

    return titleFormat

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
def formatDescription(inf: Dict[str, Any]) -> Dict[str, str]:


    if inf['description'].startswith('Provided'):
        d = inf['description'].split('\n\n')
        d.pop(0)
        d.pop(4)
        td = d[0].split('·')
        titulo = td[0]
        artista = td[1]
        album = d[1]
        año = d[3].split(': ')[1].split('-')[0]

        data = {
            'titulo': titulo,
            'artista': artista,
            'album': album,
            'año': año,
            'filepath': inf.get('filepath', '')
        }
    else:
        data = {
            'titulo': inf.get('title', ''),
            'artista': inf.get('uploader', ''),
            'album': inf.get('title', ''),
            'año': inf.get('upload_date', '')[:4],
            'filepath': inf.get('filepath', '')
        }

    return data

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

    crop_to_square(path.split(".mp3")[0] + ".webp", "cover_cropped.jpg")

    with open("cover_cropped.jpg", "rb") as img:
        audio.tags.add( # type: ignore
            APIC(
                encoding=3,          # UTF-8
                mime="image/jpeg",   # image/png si es PNG
                type=3,              # 3 = portada frontal
                desc="Cover",
                data=img.read()
            )
    )
        
    # Elimina la imagen temporal
    
    os.remove("cover_cropped.jpg")
    audio.save()

def crop_to_square(input_path, output_path):
    img = Image.open(input_path)

    # Importante: JPG no soporta alpha
    if img.mode != "RGB":
        img = img.convert("RGB")

    w, h = img.size
    size = min(w, h)

    left = (w - size) // 2
    top = (h - size) // 2
    right = left + size
    bottom = top + size

    img.crop((left, top, right, bottom)).save(
        output_path,
        format="JPEG",
        quality=95,
        subsampling=0
    )
    os.remove(input_path)