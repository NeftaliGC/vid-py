from yt_dlp import YoutubeDL
from typing import Dict, Any, List
import json
from pathlib import Path
import os
from src.core.formater import formatTitle, formatDescription, set_metadata

# cookies.txt por defecto: en la raíz del repo (junto a src/)
DEFAULT_COOKIES_FILE = Path(__file__).resolve().parents[2] / 'cookies.txt'


def resolve_cookies_file(cookies_file: str | None = None) -> Path | None:
    """
    Devuelve la ruta ABSOLUTA del archivo de cookies a usar, o None.

    Orden: `cookies_file` -> variable de entorno YTDLP_COOKIES -> <repo>/cookies.txt
    Exportar el archivo con la extensión "Get cookies.txt LOCALLY" (formato Netscape).

    yt-dlp ignora EN SILENCIO un cookiefile que no existe, así que aquí se valida
    y se avisa: si la ruta indicada no sirve, no se usan cookies de archivo.
    """
    explicit = cookies_file or os.environ.get('YTDLP_COOKIES')

    if explicit:
        path = Path(explicit).expanduser().resolve()
        if path.is_file() and os.access(path, os.R_OK):
            return path
        print(f"[cookies] No se puede leer el archivo de cookies: {path} (se ignora)")
        return None

    if DEFAULT_COOKIES_FILE.is_file() and os.access(DEFAULT_COOKIES_FILE, os.R_OK):
        return DEFAULT_COOKIES_FILE

    return None


class YTDLP:
    def __init__(self, outtmpl: str = './temp/%(title)s-[%(id)s].%(ext)s', quiet: bool = True, cookies_file: str | None = None, cookies_from_browser: str | tuple | None = None) -> None:
        self.base_opts: Dict[str, Any] = {
            'quiet': quiet,
            'no_warnings': True,
            'ignoreerrors': True,
            'outtmpl': outtmpl,
        }

        # Cookies: ver resolve_cookies_file(). Un archivo .txt tiene prioridad sobre el navegador.
        self.cookies_source = 'sin cookies'
        cookie_path = resolve_cookies_file(cookies_file)
        browser = cookies_from_browser or os.environ.get('YTDLP_COOKIES_FROM_BROWSER')

        if cookie_path:
            self.base_opts['cookiefile'] = str(cookie_path)
            self.cookies_source = f'archivo {cookie_path}'
        elif browser:
            # yt-dlp acepta ('firefox',) o una tupla (navegador, perfil, keyring, contenedor)
            self.base_opts['cookiesfrombrowser'] = (browser,) if isinstance(browser, str) else tuple(browser)
            self.cookies_source = f'navegador {browser}'

    def _build_opts(self, extra_opts: Dict[str, Any]) -> Dict[str, Any]:
        opts = self.base_opts.copy()
        opts.update(extra_opts)
        return opts
    
    def get_info(self, url: str, to_db:bool = False) -> Dict[str, Any]:
        """
        Info de UN video. Lanza ValueError si no se puede obtener o si la URL es una playlist.
        Con un link `watch?v=...&list=...` toma solo el video (noplaylist).
        """
        opts = self._build_opts({'noplaylist': True})

        with YoutubeDL(opts) as ydl: # type: ignore
            info = ydl.extract_info(url, download=False, process=False)
            # Sin procesar primero: así una playlist se detecta sin extraer cada video
            if info and info.get('_type') in ('playlist', 'multi_video'):
                raise ValueError('La URL es una playlist: usa la opción de playlist.')
            if info:
                info = ydl.process_ie_result(info, download=False)

        # Con ignoreerrors=True, yt-dlp devuelve None en vez de lanzar la excepción
        if info is None:
            raise ValueError('No se pudo obtener la información del video. Revisa el link o las cookies.')

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
            'extract_flat': 'in_playlist',
            'ignoreerrors': True,
            'skip_download': True,

        })

        with YoutubeDL(opts) as ydl: # type: ignore
            info = ydl.extract_info(url, download=False)

        # Con ignoreerrors=True, yt-dlp devuelve None en vez de lanzar la excepción
        if info is None:
            raise ValueError('No se pudo obtener la playlist. Revisa el link, que sea pública, o las cookies.')

        if info.get('_type') != 'playlist':
            raise ValueError('La URL no es una playlist')

        entries: List[Dict[str, Any]] = []

        for e in info.get('entries', []):
            if not e:
                continue

            entries.append({
                'id': e.get('id'),
                'title': e.get('title'),
                'duration': e.get('duration'),
                'uploader': e.get('uploader'),
                'url': e.get('url') or e.get('webpage_url'),
            })

        if not entries:
            raise ValueError('La playlist está vacía o no tiene videos disponibles.')

        return {
            'id': info.get('id'),
            'title': info.get('title'),
            'uploader': info.get('uploader'),
            'entries_count': len(entries),
            'entries': entries,
        }
    
    def get_playlist_page(self, url: str, start: int, page_size: int = 50) -> Dict[str, Any]:
        """
        Extrae un bloque de `page_size` entradas desde el índice `start` (1-based).
        Usa playlist_items para no pedir toda la playlist de una sola vez.
        """
        end = start + page_size - 1
        opts = self._build_opts({
            'quiet': True,
            'extract_flat': 'in_playlist',
            'ignoreerrors': True,
            'skip_download': True,
            'playlist_items': f'{start}-{end}',
        })

        with YoutubeDL(opts) as ydl:  # type: ignore
            info = ydl.extract_info(url, download=False)

        if not info or info.get('_type') != 'playlist':
            return {'id': None, 'title': None, 'entries': []}

        entries: List[Dict[str, Any]] = []
        for e in (info.get('entries') or []):
            if not e:
                continue
            entries.append({
                'id':       e.get('id'),
                'title':    e.get('title'),
                'duration': e.get('duration'),
                'uploader': e.get('uploader'),
                'index':    e.get('playlist_index'),  # posición real (1-based) en la playlist
            })

        return {
            'id':    info.get('id'),
            'title': info.get('title'),
            'entries': entries,
        }
    
    def download_audio_playlist_usb(
        self,
        playlist: List[str],
        output_dir: str,
        quality: str = '192',
        extra_hooks: List = [],
        sleep_range: tuple = (2, 8),
        concurrent: int = 2,
        extra_pp_hooks: List = [],
    ) -> int:
        """
        Versión USB-safe de download_audio_playlist.
        - Throttle de velocidad por descarga
        - Sleep aleatorio entre canciones
        - Menos concurrencia
        """
        prog_hooks = [self._rename_hook] + extra_hooks
        opts = self._build_opts({
            'format': 'bestaudio/best',
            'writethumbnail': True,
            'ignoreerrors': True,
            'concurrent_fragment_downloads': concurrent,
            'ratelimit': 2 * 1024 * 1024,
            'sleep_interval': sleep_range[0],
            'max_sleep_interval': sleep_range[1],
            'outtmpl': f'{output_dir}/%(title)s-[%(id)s].%(ext)s',
            # Con final_ext yt-dlp reconoce el .mp3 ya existente y no lo vuelve a bajar
            'final_ext': 'mp3',
            'progress_hooks': prog_hooks,
            # Los hooks extra van primero: registran la canción en cuanto el .mp3 existe,
            # aunque luego falle la incrustación de la portada en _music_hook
            'postprocessor_hooks': extra_pp_hooks + [self._music_hook],
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': quality,
            }],
        })

        with YoutubeDL(opts) as ydl:  # type: ignore
            # 0 = todo bien; != 0 = algún error (con ignoreerrors no se lanza excepción)
            return ydl.download(playlist)

    def download_audio_mp3(self, url: str, quality: str = '192') -> int:
        opts = self._build_opts({
            'noplaylist': True,  # un link watch?v=...&list=... baja solo ese video
            'format': 'bestaudio[ext=m4a]/bestaudio/best',
            'writethumbnail': True,
            'postprocessor_hooks': [self._music_hook],
            'progress_hooks': [self._rename_hook],
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': quality,
            }],
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web_embedded', 'mweb'],
                }
            },
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
            },
        })

        with YoutubeDL(opts) as ydl: # type: ignore
            # 0 = todo bien; != 0 = algún error (con ignoreerrors no se lanza excepción)
            return ydl.download([url])

    def download_audio_playlist(self, playlist: List[str], output_dir: str, quality: str = '192', extra_hooks: List = []) -> int:
        hooks = [self._rename_hook] + extra_hooks
        opts = self._build_opts({
            'format': 'bestaudio/best',
            'writethumbnail': True,
            'ignoreerrors': True,
            'concurrent_fragment_downloads': 8,
            'outtmpl': f'{output_dir}/%(title)s-[%(id)s].%(ext)s',
            'progress_hooks': hooks,
            'postprocessor_hooks': [self._music_hook],
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': quality,
            }],

        })

        with YoutubeDL(opts) as ydl: # type: ignore
            # 0 = todo bien; != 0 = algún error (con ignoreerrors no se lanza excepción)
            return ydl.download(playlist)

    def _music_hook(self, d):
        # Se llama en cada post-proceso ('started' y 'finished'); solo interesa el
        # momento en que el .mp3 final ya existe.
        if d.get('status') != 'finished':
            return

        info = d.get('info_dict', {})
        path = info.get('filepath') or ''
        if not path.endswith('.mp3'):
            return

        # Un error en la metadata no debe marcar como fallida una descarga que ya terminó
        try:
            metadata = formatDescription(info)
            metadata['cover'] = self._thumbnail_path(info)
            set_metadata(metadata)
        except Exception as e:
            print(f"[metadata] No se pudo escribir la metadata de {path}: {e}")

    @staticmethod
    def _thumbnail_path(info: Dict[str, Any]) -> str | None:
        """Ruta real de la miniatura escrita por yt-dlp (puede ser .webp, .jpg, .png...)."""
        for thumb in reversed(info.get('thumbnails') or []):
            path = thumb.get('filepath')
            if path and os.path.exists(path):
                return path
        return None

    def _rename_hook(self, d):
        if d["status"] != "finished":
            return

        info = d["info_dict"]

        filepath = info.get("filepath")
        if not filepath:
            return

        old_path = Path(filepath)

        title = formatTitle(info.get("title", "Unknown"))
        video_id = info.get("id", "")

        new_path = old_path.with_name(
            f"{title}-[{video_id}]{old_path.suffix}"
        )

        if new_path != old_path:
            old_path.rename(new_path)
            info["filepath"] = str(new_path)

    @staticmethod
    def _video_format(resolution: int | str = 'best', preset: str = 'mp4_compat') -> Dict[str, str]:
        """
        Arma el selector de formato de yt-dlp para un video.

        `resolution` es la altura máxima: 720, "720" o "720p" (o 'best' para no limitar).
        IMPORTANTE: el filtro debe ser numérico. yt-dlp interpreta `height<=720p` como
        "720 petabytes" (720pB) y el filtro deja pasar cualquier resolución.
        """
        res = str(resolution).strip().lower().removesuffix('p')
        if res in ('', 'best'):
            h = ''
        elif res.isdigit():
            h = f'[height<={int(res)}]'
        else:
            raise ValueError(f'Resolución inválida: {resolution!r}')

        presets = {
            'mp4_compat': {
                'format': f'bestvideo[vcodec^=avc1]{h}+bestaudio[acodec^=mp4a]/'
                          f'best[vcodec^=avc1]{h}',
                'merge_output_format': 'mp4',
            },
            'mkv_4k': {
                'format': f'bestvideo{h}+bestaudio/best{h}',
                'merge_output_format': 'mkv',
            },
        }
        return presets.get(preset, presets['mp4_compat'])

    def download_video_mp4(self, url: str, resolution: int | str = 'best', preset: str = 'mp4_compat') -> int:
        opts = self._build_opts({
            **self._video_format(resolution, preset),
            'noplaylist': True,  # un link watch?v=...&list=... baja solo ese video
        })

        with YoutubeDL(opts) as ydl: # type: ignore
            # 0 = todo bien; != 0 = algún error (con ignoreerrors no se lanza excepción)
            return ydl.download([url])


if __name__ == "__main__":
    ytdlp = YTDLP()
    video_url = 'https://youtu.be/fUo25zA5xrA?si=ItHj_sODrYmTW3k7'
    info = ytdlp.get_info(video_url)
    print(json.dumps(info, indent=4, ensure_ascii=False))
    
    ytdlp.download_audio_mp3(video_url, quality='192')
    #ytdlp.download_video_mp4(video_url, resolution='1080')
