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