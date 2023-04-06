# Vid-Py
Vid-Py es un programa de línea de comandos y una interfaz gráfica (próximamente) escrita en Python para descargar videos de YouTube. Utiliza la biblioteca de Python ydlp para descargar videos en varios formatos y resoluciones. VidPy también incluye la capacidad de descargar sólo el audio de un video de YouTube en formato MP3.

## Características

- Descarga videos de YouTube en varios formatos y resoluciones (próximamente).
- Descarga sólo el audio de un video de YouTube en formato MP3.
- Interfaz de línea de comandos fácil de usar.
- Incrustación de metadatos para canciones.
- Búsqueda automática de los datos de las canciones a través de la API de Spotify.

## Uso

Para utilizar Vid-Py, simplemente descargue o clone este repositorio y ejecute el archivo `vidpy.py` con Python en su terminal de línea de comandos.
``` cmd
    cd vid-py
    python vidpy.py

    o

    py vidpy.py
```

Si desea agregar metadatos, necesitará una clave de API de Spotify para obtener los datos de las canciones, ya que el programa es de distribución libre y no incluye la integración directa con la API de Spotify.

Sin embargo, la integración con la API es opcional y el programa sigue funcionando sin ella. Simplemente no se agregarán los metadatos de Spotify a los archivos de audio descargados, pero pueden ser agregados manualmente siguiendo el proceso normal del programa.

Si decide utilizar la integración con la API de Spotify, puede obtener una clave API siguiendo los pasos descritos en la documentación oficial de Spotify. Una vez que tenga la clave API, puede ingresarla en el archivo de configuración del programa para habilitar la integración con la API.

1. Cree una carpeta llamada `config` en el directorio raíz del programa
2. Dentro la carpeta `config`, agregue el archivo `config.json`
3. En `config.json`, agregue su api-key de la siguiente manera:

```Json
{
    "Api_Keys": {        
        "Spotify": {
            "client-id": "your-clientID",
            "client-secret": "your-client-secret"
        }

    }
}
```

Tenga en cuenta que el uso de la API de Spotify puede estar sujeto a límites y condiciones adicionales por parte de Spotify.

## Requisitos

- Python 3.x
- ydlp biblioteca de Python instalada (solo para la linea de comandos)

## Contribuir

Siéntete libre de contribuir a Vid-Py enviando solicitudes o informando problemas en el repositorio de GitHub. ¡Todas las contribuciones son bienvenidas!
