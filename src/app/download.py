from yt_dlp import YoutubeDL
from typing import Dict, Any, List
from tqdm import tqdm
import json
from time import sleep
import os
from formater import formatTitle, title, formatDescription, set_metadata

class YTDLP:
    def __init__(self, outtmpl: str = './temp/%(title)s.%(ext)s', quiet: bool = True) -> None:
        self.base_opts = {
            'quiet': quiet,
            'no_warnings': True,
            'ignoreerrors': True,
            'outtmpl': outtmpl,
        }

    def _build_opts(self, extra_opts: Dict[str, Any]) -> Dict[str, Any]:
        opts = self.base_opts.copy()
        opts.update(extra_opts)
        return opts
    
    def get_info(self, url: str, to_db:bool = False) -> Dict[str, Any]:
        with YoutubeDL(self.base_opts) as ydl: # type: ignore
            info = ydl.extract_info(url, download=False)

        info_raw = {
            'id': info['id'],
            'title': info['title'], # type: ignore
        }

        if not to_db:
            info_raw.update({
                'duration': info.get('duration'),
                'uploader': info.get('uploader'),
                'upload_date': info.get('upload_date'),
                'description': info.get('description'),
                'thumbnail': info.get('thumbnail'),
                'resolutions': sorted({fmt['height'] for fmt in info.get('formats', []) if fmt.get('height') is not None}), # type: ignore
            })

        
        return info_raw

    def get_playlist_info(self, url: str, to_db: bool = False) -> Dict[str, Any]:
        opts = self._build_opts({
            'quiet': True,
            'extract_flat': True,
            'skip_download': True,

        })

        with YoutubeDL(opts) as ydl: # type: ignore
            info = ydl.extract_info(url, download=False)

        if info.get('_type') != 'playlist':
            raise ValueError('La URL no es una playlist')

        entries: List[Dict[str, Any]] = []

        for e in info.get('entries', []):
            if not e:
                continue

            entries.append(self.get_info(e['url'], to_db=to_db))

        return {
            'id': info.get('id'),
            'title': info.get('title'),
            'uploader': info.get('uploader'),
            'entries_count': len(entries),
            'entries': entries,
        }

    def download_audio_mp3(self, url: str, quality: str = '192'):
        opts = self._build_opts({
            'format': 'bestaudio/best',
            'writethumbnail': True,
            'extract_flat': True,
            'postprocessor_hooks': [self._music_hook],
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': quality,
            }],
        })

        with YoutubeDL(opts) as ydl: # type: ignore
            ydl.download([url])

    def download_audio_playlist(self, playlist: List[str], quality: str = '192'):
        opts = self._build_opts({
            'format': 'bestaudio/best',
            'writethumbnail': True,
            'postprocessor_hooks': [self._music_hook],
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': quality,
            }],

        })
        
        for url in playlist:
            with YoutubeDL(opts) as ydl: # type: ignore
                ydl.download([url])

    def _music_hook(self, d):
        info = d.get('info_dict', {})
        filename = info.get('filepath')

        info = {
            'id': info.get('id'),
            'title': info.get('title'),
            'duration': info.get('duration'),
            'uploader': info.get('uploader'),
            'upload_date': info.get('upload_date'),
            'description': info.get('description'),
            'thumbnail_url': info.get('thumbnail'),
            'filepath': filename,
        }

        metadata = formatDescription(info)

        if d['status'] == 'finished':
            set_metadata(metadata)
            

    def download_video_mp4(self, url: str, resolution: str = 'best', preset: str = 'mp4_compat'):
        PRESETS = {
            'mp4_compat': {
                'format': f'bestvideo[vcodec^=avc1][height<={resolution}]'
                            f'+bestaudio[acodec^=mp4a]/'
                            f'best[vcodec^=avc1]',
                'merge_output_format': 'mp4',
            },
            'mkv_4k': {
                'format': f'bestvideo[height<={resolution}]+bestaudio/best',
                'merge_output_format': 'mkv',
            },
        }

        opts = self._build_opts({
            'format': (
                PRESETS.get(preset, PRESETS['mp4_compat'])['format']
            ),
            'merge_output_format': (
                PRESETS.get(preset, PRESETS['mp4_compat'])['merge_output_format']
            ),
        })

        with YoutubeDL(opts) as ydl: # type: ignore
            ydl.download([url])


if __name__ == "__main__":
    ytdlp = YTDLP()
    video_url = 'https://youtu.be/fUo25zA5xrA?si=ItHj_sODrYmTW3k7'
    info = ytdlp.get_info(video_url)
    print(json.dumps(info, indent=4, ensure_ascii=False))
    
    ytdlp.download_audio_mp3(video_url, quality='192')
    #ytdlp.download_video_mp4(video_url, resolution='1080')

#############################################################
""" '''
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
        if video_info is None:
            print("No se pudo obtener la información del video.")
            return
        full_name = video_info.get('title', None)
        extesion = video_info.get('ext', None)
        thumbnail_url = video_info.get('thumbnail', None)

        print("Video: " + str(full_name))
        
        if(rename == "1"):
            name = title(full_name)
        else:
            name = full_name
        
        name = formatTitle(name)

    print("")
    print("Se descargara: " + str(full_name) + " con el nombre de archivo: " + str(name))

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
        if playlist_info is None:
            print("No se pudo obtener la información de la lista de reproducción.")
            return
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


    safe_title = plys_title if plys_title is not None else "playlist"
    p = downloadPath() + safe_title + "/"

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
    
def getResolutions(video):
    ydl_opts = {
        'quiet': True,
        'format': 'bestvideo+bestaudio/best',
        'noplaylist': True,
        'extract_flat': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        video_info = ydl.extract_info(video, download=False)
        if video_info is None:
            print("No se pudo obtener la información del video.")
            return []
        
        formats = video_info.get('formats', [])
        resolutions = set()
        
        for fmt in formats:
            if 'height' in fmt and fmt['height'] is not None:
                resolutions.add(fmt['height'])
        
        return sorted(resolutions) """