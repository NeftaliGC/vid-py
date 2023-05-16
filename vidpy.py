from metadata import metadatos
from download import download, downloadPlaylist, downloadPath

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
# funcion que valida si la ruta de descarga existe
#############################################################


if __name__ == "__main__":
    main()