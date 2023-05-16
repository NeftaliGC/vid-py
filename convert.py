import os
from moviepy.editor import *

#############################################################
# funcion que convierte mp4 a mp3
#############################################################
def convertTo(full_Path, path, name, extension):

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