import yt_dlp

from moviepy.editor import *
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TRCK, APIC
from tqdm import tqdm
from time import sleep
import os
from data import meta
from PIL import Image
import json

############################################################################
'''
Ejecuta las acciones que desea el usuario.
No se detiene hasta que el usuario lo indica.
'''
def main():

    ejecucion = True

    while(ejecucion):
        print("¿Deseas descargar en mp3 o mp4?")
        print("1- Solo audio")
        print("2- Video (.mp4 Maxima resolucion del video disponible)")
        print("3- Descargar playlist de musica completa")
        print("4- Instrucciones")
        print("5- Salir")

        opt = input("Opcion: ")

        if(opt == "1"):

            link = input("Escribe el link de la cancion: ")
            print("Descarando... Porfavor Espere.")
            meta = input("Desea agregar metadatos a la cancion? 1- Si 2- No: ")
            download(link, "audio", downloadPath(), "1", meta)
            print("")

            print("Cancion descargada con exito.")

        elif(opt == "2"):

            link = input("Escribe el link del video: ")
            print("Descarando... Porfavor Espere.")
            download(link, "video", downloadPath(), "1", "2")
            print("")

        elif(opt == "3"):

            link = input("Escribe el link de la Playlist: ")
            rename = input("¿Quieres cambiar los nombres de cada archivo? 1- Si 2- No: ")
            met = input("Desea agregar metadatos a las canciones? 1- Si 2- No: ")
            iV = input("Desea descargar desde un punto especifico? 1- Si 2- No: ")
            if iV == "1":
                iV = input("Escribe el indice de inicio: ")
                
            downloadPlaylist(link, ".mp3", rename, met, iV)
            print("")
        
        elif(opt == "4"):

            print("")
            print("Este programa puede descargar videos de youtube. \n Solo tienes que proporcionar el link del video que deseas descargar.")
            print("Existen 3 opciones de descarga. \n 1- Solo audio del video en formato MP3 \n 2- Video completo en maxima calidad formato MP4 \n 3- Descargar una playlist completa en formato MP3")
            print("Tanto los videos como listas de reproduccion deben estar publicos o no listados en youtube. Los videos marcados como privados no podran descargarse aun proporcionando el link.")
            print("-----------------------------------------------------------------")
        elif(opt == "5"):
            print("Gracias por usar el programa.")
            ejecucion = False
            break
        
        opt = input("¿Deseas realizar una accion mas?  1- Si 2- No: ")
        if(opt == "2"):
            ejecucion = False

#############################################################
'''
Descarga un video con formato MP4 o MP3 
video = video a descargar
extension = String que define la extension del archivo
format = String que define si se descargara video o audio
path = ruta de descarga
rename = String "1" si se renombrara el archivo o "2" si no se renombrara el archivo
'''
def download(video, format, path, rename, metadatos):

    if(metadatos == "1"):
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
        name = video_info.get('title', None)
        extesion = video_info.get('ext', None)
        thumbnail_url = video_info.get('thumbnail', None)

        print("Video: " + name)
        
        if(rename == "1"):
            name = title(name)
        
        name = formatTitle(name)

    print("")
    print("Se descargara: " + name)

    sleep(3)
    print("Descargando... Porfavor Espere.")
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video])
        filename = ydl.prepare_filename(video_info)
        full_path = os.path.join(os.getcwd(), filename)        

    if(format == "audio"):
        convertTo(full_path, path, name, metadatos, "mp3")
    elif(format == "video"):
        convertTo(full_path, path, name, meta, "mp4")

    print("La descarga de " + name + " ha finalizado.")

############################################################
'''
Descarga una playlist completa en formato MP3
playl = playlist que se descargara
extension = String que define la extension del archivo
rename = String "1" si se renombrara el archivo o "2" si no se renombrara el archivo
'''
def downloadPlaylist(playl, extesion, rename, metadatos, nV):

    ydl_opts = {
        'quiet': True,
        'dump_single_json': True,
        'skip_playlist_after_errors': True,
        'playliststart': nV
    }
    
    print("\nPreparando todo para descargar, esto puede tardar unos minutos...")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        
        playlist_info = ydl.extract_info(playl, download=False)
        plys_title = playlist_info.get('title')
        
    videos = playlist_info['entries']

    videos_links = [video['webpage_url'] for video in videos]


    p = downloadPath() + plys_title + "/"

    for i in tqdm(range(len(videos_links)), desc=f"Descargando {plys_title}:"):
        download(videos_links[i], "audio", path=p, rename= rename, metadatos= metadatos)


    """ print("")
    print("Descargando: " + playl.title)

    nVideos = playl.length

    for i in tqdm(range(nVideos), desc="Descargando playlist: "):

        video = playl.videos[i]

        print("")
        download(video, "audio", path=p, rename=rename, metadatos=metadatos)
        print("") """



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
#############################################################
# funcion que valida si la ruta de descarga existe
#############################################################

#############################################################
# funcion que agrega los metadatos de las canciones
#############################################################
def metadatos(p, n, path_img):

    thumbnail = Image.open(path_img)
    thumbnail.convert("RGB").save(p + n + ".jpg", "JPEG")
    os.remove(path_img)

    data = meta(n)

    print("\nLos metadatos encontrados son: ")
    print("Titulo: " + data[0])
    print("Artista: " + data[1])
    print("Album: " + data[2])

    o = input("Son correctos? 1- Si 2- No: ")
    print(" ")
    if o == "2":
        data = input("Escribe los metadatos separados por comas: ")
        data = data.split(",")
    

    print("\nAgregando metadatos...")
    song = MP3(p + n + ".mp3")
    song_tags = ID3()

    song_tags.add(TIT2(encoding=3, text=data[0]))
    song_tags.add(TPE1(encoding=3, text=data[1]))
    song_tags.add(TALB(encoding=3, text=data[2]))
    song_tags.add(APIC(encoding=3, mime='image/jpeg', type=3, desc=u'Cover', data=open(p + n + ".jpg", 'rb').read()))

    song_tags.save(p + n + ".mp3", v2_version=3)
    sleep(3)
    print("Agregando metadatos... Finalizado")
    os.remove(p + n + ".jpg")

    

#############################################################
# funcion que convierte mp4 a mp3
#############################################################
def convertTo(full_Path, path, name, meta, extension):

    if(os.path.exists(path) == False):
        print("El archivo no existe")
        return

    if(extension == "mp3"):
        print("\nConvirtiendo a mp3...")
        video = VideoFileClip(full_Path)
        video.audio.write_audiofile(path + name + ".mp3")
        print("Convirtiendo a mp3... Finalizado")
        video.close()

        print("\nEliminando archivos...")
        os.remove(full_Path)
        print("Eliminando archivos... Finalizado")

    elif(extension == "mp4"):
        print("\nConviertiendo a mp4...")
        video = VideoFileClip(full_Path)
        video.write_videofile(path + name + ".mp4")
        print("Conviertiendo a mp4... Finalizado")
        video.close()

        print("\nEliminando Archivos...")
        os.remove(full_Path)
        print("Eliminando Archivos... Finalizado")


    if(meta == "1"):
        metadatos(path, name, path_img=path + name + ".webp")

if __name__ == "__main__":
    main()