from data import meta
from time import sleep
import os
from PIL import Image
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TRCK, APIC
from formater import formatTitle

#############################################################
# funcion que agrega los metadatos de las canciones
#############################################################
def metadatos(path, name, path_img):

    try:
        thumbnail = Image.open(path_img)
        thumbnail.convert("RGB").save(path + name + ".jpg", "JPEG")
        os.remove(path_img)
    except:
        archivos = os.listdir(path)
        print("No se ha encontrado la imagen de la cancion, Intentando solucionar...")
        for archivo in archivos:
            if archivo.endswith(".webp"):
                rename = name + ".webp"
                path_img = os.path.join(path, archivo)
                path_newImg = os.path.join(path, rename)

                try:
                    os.rename(path_img, path_newImg)
                    print("Se ha renombrado la imagen problematica a: " + rename)
                    thumbnail = Image.open(path_newImg)
                    thumbnail.convert("RGB").save(path + name + ".jpg", "JPEG")
                    os.remove(path_newImg)
                except:
                    print("No se ha encontrado la imagen de la cancion, No se agregaran metadatos.")
                    return


    data = meta(name)

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
    song = MP3(path + name + ".mp3")
    song_tags = ID3()

    song_tags.add(TIT2(encoding=3, text=data[0]))
    song_tags.add(TPE1(encoding=3, text=data[1]))
    song_tags.add(TALB(encoding=3, text=data[2]))
    song_tags.add(APIC(encoding=3, mime='image/jpeg', type=3, desc=u'Cover', data=open(path + name + ".jpg", 'rb').read()))

    song_tags.save(path + name + ".mp3", v2_version=3)
    sleep(3)
    print("Agregando metadatos... Finalizado")
    os.remove(path + name + ".jpg")