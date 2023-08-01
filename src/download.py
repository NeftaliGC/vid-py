import yt_dlp
from tqdm import tqdm
import json
from time import sleep
import os
from formater import formatTitle, title
from convert import convertTo
#############################################################
'''
Descarga un video con formato MP4 o MP3 
video = video a descargar
extension = String que define la extension del archivo
format = String que define si se descargara video o audio
path = ruta de descarga
rename = String "1" si se renombrara el archivo o "2" si no se renombrara el archivo
'''
def download(video, format, path, rename, meta):

    if(meta == "1"):
        ydl_opts = {
            'quiet': True,
            'outtmpl': path + '%(title)s.%(ext)s',
            'writethumbnail': True,
        }
    else:
        ydl_opts = {
            'quiet': True,
            'outtmpl': path + '%(title)s.%(ext)s',
        }

    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        video_info = ydl.extract_info(video, download=False)
        full_name = video_info.get('title', None)
        extesion = video_info.get('ext', None)
        thumbnail_url = video_info.get('thumbnail', None)

        print("Video: " + full_name)
        
        if(rename == "1"):
            name = title(full_name)
        else:
            name = full_name
        
        name = formatTitle(name)

    print("")
    print("Se descargara: " + full_name + " con el nombre de archivo: " + name)

    sleep(3)
    print("Descargando... Porfavor Espere.")
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video])
        filename = ydl.prepare_filename(video_info)
        full_path = os.path.join(os.getcwd(), filename)        

    if(format == "audio"):
        convertTo(full_path, path, name, "mp3")
        if(meta == "1"):
            imgPath = path + full_name + ".webp"
            metadatos(path, name, path_img=imgPath)
    elif(format == "video"):
        convertTo(full_path, path, name, "mp4")

    print("La descarga de " + name + " ha finalizado.")

############################################################
'''
Descarga una playlist completa en formato MP3
playl = playlist que se descargara
extension = String que define la extension del archivo
rename = String "1" si se renombrara el archivo o "2" si no se renombrara el archivo
'''
def downloadPlaylist(playl, extesion, rename, metadatos, nV):

    if(nV == None):
        id = 1
    else:
        id = int(nV)

    ydl_opts = {
        'quiet': True,
        'ignoreerrors': True,  # Ignorar errores y continuar descargando otros videos
        'no_warnings': True,  # No mostrar advertencias
        'playliststart': id,  # Descargar desde el video #
    }
    
    print("\nPreparando todo para descargar, esto puede tardar unos minutos...")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        
        playlist_info = ydl.extract_info(playl, download=False)
        plys_title = playlist_info.get('title')
        
    videos = playlist_info['entries'] if 'entries' in playlist_info else None

    if videos is None:
        print("La lista de reproducción no tiene videos válidos.")
        return

    videos_links = []  
    for i, video in enumerate(videos, start=id):
        if video is None:
            print(f"El video #{i} no está disponible. Se omite.")
            continue
        
        if 'webpage_url' not in video:
            print(f"El video #{i} no tiene una URL válida. Se omite.")
            continue

        video_url = video['webpage_url']
        videos_links.append(video_url)


    p = downloadPath() + plys_title + "/"

    for i in tqdm(range(len(videos_links)), desc=f"Descargando {plys_title}:"):
        download(videos_links[i], "audio", path=p, rename=rename, meta = metadatos)


#############################################################
def downloadPath():
    print("¿Deseas cambiar la ruta de descarga?")
    print("La ruta por defecto es: ./download")
    opt = input("1- Si | 2- No: ")

    if(opt == "1"):
        print("La ruta debe ser relativa al directorio donde se encuentra el programa. Eejemplo: ./download o .download/carpetadescarga")
        path = input("Escribe la ruta de descarga: ")
        return path
    else:
        return "./download/"