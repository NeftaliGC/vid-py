from yt_dlp import YoutubeDL
from typing import Dict, Any, List
import json
from pathlib import Path
import os
from src.core.formater import formatTitle, formatDescription, set_metadata

class YTDLP:
    def __init__(self, outtmpl: str = './temp/%(title)s-[%(id)s].%(ext)s', quiet: bool = True, cookies_file: str | None = None) -> None:
        self.base_opts: Dict[str, Any] = {
            'quiet': quiet,
            'no_warnings': True,
            'ignoreerrors': True,
            'outtmpl': outtmpl,
        }

        # Si se pasa un archivo de cookies, se inyecta en todos los opts.
        # Exportar desde el navegador con la extensión "Get cookies.txt LOCALLY".
        # Reemplazar simplemente apuntando a un nuevo archivo .txt
        resolved_cookies = cookies_file or os.environ.get('YTDLP_COOKIES')
        if resolved_cookies:
            self.base_opts['cookiefile'] = resolved_cookies

    def _build_opts(self, extra_opts: Dict[str, Any]) -> Dict[str, Any]:
        opts = self.base_opts.copy()
        opts.update(extra_opts)
        return opts
    
    def get_info(self, url: str, to_db:bool = False) -> Dict[str, Any]:
        with YoutubeDL(self.base_opts) as ydl: # type: ignore
            info = ydl.extract_info(url, download=False)

        if info is None:
            return {
                'id': '',
                'title': 'Unknown',
            }

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
    ):
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
            'progress_hooks':prog_hooks,
            'postprocessor_hooks': [self._music_hook],
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': quality,
            }],
        })

        with YoutubeDL(opts) as ydl:  # type: ignore
            ydl.download(playlist)

    def download_audio_mp3(self, url: str, quality: str = '192'):
        opts = self._build_opts({
            'format': 'bestaudio/best',
            'writethumbnail': True,
            'extract_flat': True,
            'postprocessor_hooks': [self._music_hook],
            'progress_hooks': [self._rename_hook],
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': quality,
            }],
        })

        with YoutubeDL(opts) as ydl: # type: ignore
            ydl.download([url])

    def download_audio_playlist(self, playlist: List[str], output_dir: str, quality: str = '192', extra_hooks: List = []):
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
            ydl.download(playlist)

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
