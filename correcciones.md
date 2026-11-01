# Correcciones que deben hacerse en el programa

## Errores particulares
---

- [X] No encuentra la portada de la cancion al cambiar nombre de archivo desde el menu
- [X] Saltar la descarga de un video no disponible en una lista de reproduccion

## Errores generales
---

- [ ] Mejorar manejo de rutas → ver auditoría, punto **C13**
- [ ] Buscar un metodo para obtener portadas → la portada ya se toma en cualquier formato (ver "Corregido recientemente")
- [X] Mejorar la inserccion de metadatos → ver auditoría, punto **A2**

## Estetica
--- 

- [ ] Agregar espacios al seleccionar una opcion del menu
- [ ] Mejorar barra de progreso en la descarga de una playlist
- [ ] Agregar una interfas intuitiva
- [X] Separar codigo

## Manejo de excepciones en: 
---

- [X] Playlist no disponibles → ver auditoría, puntos **A3** y **B10** (en la CLI ya se maneja; falta validar el espacio libre en B10)
- [ ] Manejo de seleccion (Menu) → ver auditoría, punto **A5**
- [ ] Bloqueo de API

### Errores no listados que fueron corregidos durante la correccion de otros errores:
---

- Al descargar una playlist y decidir no cambiar nombres de archivo el programa se rompia.
- No se encontraba la portada al tener en el titulo del video caracteres invalidos.

---

## Corregido recientemente (commit `7b22d6a`)
---

- **BD del sync USB**: la canción se registra en `tracks` solo cuando el `.mp3` ya existe (hook de post-proceso `MoveFiles`). `sync_offset` usa la posición real en la playlist. Se omiten los IDs ya registrados y los fallos se reintentan en el siguiente sync. Las conexiones a SQLite se cierran siempre.
- **Portada en cualquier formato**: se usa la ruta real de la miniatura que reporta yt-dlp (`.webp`, `.jpg`, `.png`…). El recorte se hace en memoria (ya no escribe `cover_cropped.jpg` en el CWD) y, si no hay portada, la canción se guarda sin ella en lugar de fallar.
- **HTTP 403 al descargar** (2026-11-01): yt-dlp 2026.3.17 ya no podía descargar algunos videos (por ejemplo los musicales) porque YouTube fuerza SABR en el cliente web. Se resolvió actualizando a 2026.10.26; `requirements.in` ahora pide `yt-dlp[default]>=2026.10.26` (incluye `yt-dlp-ejs`). **Pendiente:** regenerar `requirements.txt` con `pip-compile ./requirements.in`.
- **Cookies desde archivo**: antes el `cookies.txt` nunca se usaba. Ahora `resolve_cookies_file()` busca, en orden, `cookies_file=`, la variable `YTDLP_COOKIES` y `<repo>/cookies.txt`, valida la ruta y muestra la fuente activa en el menú y en el sync.

---

## Auditoría (2026-11-01)
---

Revisión completa de `src/`. Los bugs marcados como **verificado** se reprodujeron con yt-dlp 2026.03.17 (la versión del `.venv`).

### A. Bugs (prioridad alta)

- [X] **A1. La opción 2 (video) ignora la resolución elegida** — ✅ corregido: `YTDLP._video_format()` usa la altura numérica (verificado con `mw3kSNIxjqo`: 360p → 640×360, 1440p → 2560×1440) — `src/cli/vidpy.py` (opción 2) y `src/core/download.py` (`download_video_mp4`).
  - **Bug:** la CLI pasa la resolución como texto con sufijo (`"720p"`), y `download_video_mp4` arma el formato `bestvideo[height<=720p]`. yt-dlp acepta ese filtro sin error, pero no lo aplica, porque `720p` no es un número.
  - **Comportamiento actual:** se elija la resolución que se elija, se descarga la máxima disponible (por ejemplo 4K). **Esperado:** como máximo la resolución elegida.
  - **Verificado:** con formatos de 360/720/1080/2160, `bestvideo[height<=720p]` elige `2160` y `bestvideo[height<=720]` elige `720`.
  - **Por qué mejorar:** la opción de resolución no sirve para nada y se descargan archivos mucho más pesados de lo pedido.
  - **Arreglo propuesto:** pasar `int(res.rstrip('p'))` a `download_video_mp4`.

- [X] **A2. Crashes por valores `None` al armar la metadata** — `src/core/formater.py` (`formatDescription`) y `src/core/download.py` (`_music_hook`). ✅ Corregido.
  - **Bug:** `inf.get('description', '')` devuelve `None` si la clave existe con valor `None` (videos sin descripción), y entonces `desc.startswith(...)` lanza `AttributeError`. Lo mismo pasa con `inf.get('upload_date', '')[:4]` (`TypeError`). En la rama "Provided to YouTube", una línea que es solo `℗` hace que `line.split()[1]` lance `IndexError`, y `℗2020 Sello` (sin espacio) guardaba **año = "Sello"**.
  - **Comportamiento anterior:** la excepción ocurría dentro de `_music_hook` (que además corría en cada evento `started`/`finished` de cada post-proceso). Se perdía la metadata de la canción y yt-dlp marcaba la descarga como error. **Esperado:** tags vacíos o parciales, sin excepción.
  - **Metadata pobre (mejora incluida):** yt-dlp ya extrae `track`, `artists`, `album` y `release_year` en canciones de YouTube Music, pero se descartaban. En videos oficiales el álbum repetía el título completo del video.
  - **Arreglo aplicado:**
    - `formatDescription` usa, en orden: (1) los campos de yt-dlp; (2) el parseo de "Provided to YouTube"; (3) `Artista - Canción` desde el título, sin `(Official Music Video)`, `[Lyrics]`, etc., con el uploader sin `- Topic`/`VEVO` como artista y el álbum vacío. Nunca lanza excepción por campos faltantes.
    - `_music_hook` solo actúa con `finished` sobre el `.mp3`, y un error de metadata se muestra como aviso sin marcar la descarga como fallida.
  - **Verificado:** `V-uIp-WuD60` (YouTube Music) → `Patient Zero` / `Taylor Swift` / `The Life of a Showgirl: The Encore` / 2026. `mw3kSNIxjqo` (video oficial) → `Patient Zero` / `Taylor Swift` / sin álbum / 2026. Ambos con portada.

- [X] **A3. `get_info` / `get_playlist_info` truenan si yt-dlp devuelve `None`** — `src/core/download.py`. ✅ Corregido.
  - **Bug:** con `ignoreerrors=True`, `extract_info` devuelve `None` en lugar de lanzar una excepción (URL inválida, playlist privada, HTTP 403 sin cookies). `get_playlist_info` hacía `info.get(...)` sobre `None` y lanzaba `AttributeError`. `get_info` devolvía `{'title': 'Unknown'}` sin resoluciones, y en la opción 2 `Prompt.ask(choices=[])` repetía "Please select one of the available options" para siempre. Además, `get_info` con un link de playlist se colgaba (más de 40 s) extrayendo cada video, y el `ValueError("La URL no es una playlist")` no se capturaba en la opción 3.
  - **Bug relacionado:** un link de video copiado desde una playlist (`watch?v=…&list=…`) en las opciones 1 o 2 descargaba **la playlist completa** (verificado: 150 videos en lugar de 1).
  - **Comportamiento anterior:** traceback (opciones 3 y 5), menú bloqueado (opción 2) o descargas masivas no pedidas. **Esperado:** un mensaje claro y volver al menú.
  - **Arreglo aplicado:**
    - `get_info` usa `noplaylist`, detecta playlists antes de procesarlas y lanza `ValueError` si no hay info.
    - `get_playlist_info` lanza `ValueError` si no hay info o si la playlist está vacía.
    - `download_audio_mp3` y `download_video_mp4` usan `noplaylist`.
    - La CLI captura los errores en las opciones 2 y 3 y avisa si no hay resoluciones. `register_usb` ya capturaba `ValueError`.
  - **Verificado:** video inexistente, URL ajena, texto basura, link de playlist en la opción 2 (1 s, sin colgarse), link de video en la opción 3, y `&list=` en la opción 1 (baja un solo mp3).

- [X] **A4. La CLI siempre dice "descargada con éxito"** — `src/cli/vidpy.py` (opciones 1, 2 y 3). ✅ Corregido.
  - **Bug:** `ignoreerrors=True` hace que `ydl.download()` no lance excepciones; solo devuelve un código distinto de 0, y los métodos `download_*` lo descartaban.
  - **Comportamiento anterior:** si la descarga fallaba (403, video privado, sin ffmpeg), igual se mostraba "Cancion descargada con exito". En la opción 3, el mensaje se borraba al instante al volver al menú. **Esperado:** avisar del fallo.
  - **Arreglo aplicado:** los `download_*` devuelven el código de yt-dlp y la nueva función `informar_resultado()` muestra el éxito (con cuenta regresiva) o el error (esperando Enter). En la opción 3, un código distinto de 0 se muestra como aviso amarillo de que al menos una canción falló.
  - **Verificado:** opción 1 con un video inexistente → mensaje de error. Opciones 1 y 2 con videos válidos → "con éxito" (mp3, y mp4 a 240p según `ffprobe`).

- [ ] **A5. El índice de inicio de la playlist no se valida** — `src/cli/vidpy.py` (opción 3).
  - **Bug:** `int(input(...))` lanza `ValueError` si se escribe texto, y un índice fuera de rango produce una lista vacía sin aviso.
  - **Comportamiento actual:** traceback y la CLI se cierra. **Esperado:** volver a pedir el número.
  - **Por qué mejorar:** un error de escritura no debería cerrar el programa (relacionado con "Manejo de seleccion (Menu)").
  - **Arreglo propuesto:** usar `IntPrompt.ask` de Rich validando `1 <= n <= len(ids)`.

### B. Robustez del sync USB (prioridad alta)

El sync está pensado para correr desatendido (udev/systemd), así que cualquier error ahí pasa desapercibido.

- [ ] **B6. Cualquier archivo `.db` marca la USB como "vidpy"** — `src/usb/detector.py` (`is_vidpy_usb`, `get_db_path`).
  - **Bug:** basta con cualquier `.db` en la raíz (de otra aplicación, o un `Thumbs.db`) para que la USB se trate como registrada. Después `get_playlist` lanza `sqlite3.OperationalError: no such table: playlist`. Con varios `.db`, se toma uno arbitrario según el orden de `iterdir()`.
  - **Por qué mejorar:** rompe el sync automático y la opción 5 se niega a registrar la USB ("ya tiene una playlist").
  - **Arreglo propuesto:** que `get_db_path` solo acepte `.db` con las tablas `playlist` y `tracks`, y que `is_vidpy_usb` reutilice `get_db_path`.

- [ ] **B7. Un error en una USB detiene el sync de todas** — `src/usb/manager.py` (`auto_sync_all`).
  - **Qué pasa:** el ciclo no tiene `try/except`; si una USB falla (por B6, I/O o red), las siguientes no se sincronizan.
  - **Por qué mejorar:** con varias USBs conectadas, una defectuosa bloquea a las demás.
  - **Arreglo propuesto:** usar `try/except` por USB, mostrar el error y continuar.

- [ ] **B8. Nada impide dos syncs simultáneos sobre la misma USB** — `src/usb/sync.py`.
  - **Qué pasa:** udev puede disparar la regla dos veces, o el usuario puede usar la opción 6 mientras corre el servicio. Dos procesos descargarían el mismo archivo a la vez y escribirían en la misma BD.
  - **Por qué mejorar:** archivos corruptos, `database is locked` y descargas duplicadas.
  - **Arreglo propuesto:** un lock con `fcntl.flock` sobre `<usb>/.vidpy.lock` al inicio de `sync_usb`. Si ya está tomado, avisar y salir.

- [ ] **B9. Si la USB se desconecta a mitad del sync, salen errores de I/O crudos** — `src/usb/sync.py`.
  - **Qué pasa:** los `OSError` y `sqlite3.OperationalError` no se capturan y se muestra un traceback largo.
  - **Por qué mejorar:** el progreso ya queda guardado (offset y `tracks`); solo falta un mensaje claro ("USB desconectada, se reanudará en el próximo sync").
  - **Arreglo propuesto:** capturar esas excepciones en `sync_usb` y salir limpio.

- [ ] **B10. `register_usb` no valida la playlist ni el espacio libre** — `src/usb/manager.py`.
  - **Qué pasa:** una playlist privada o vacía produce un traceback (por A3) o crea una BD vacía. Tampoco se verifica que quepa en la USB.
  - **Por qué mejorar:** se registra una USB que nunca va a sincronizar bien, o se llena a medias.
  - **Arreglo propuesto:** validar `entries_count > 0` y mostrar el espacio libre (`shutil.disk_usage`) antes de confirmar.

### C. Consistencia y código muerto (prioridad media)

- [ ] **C11. Opciones de descarga de audio duplicadas y divergentes** — `src/core/download.py`.
  - **Qué pasa:** `download_audio_mp3`, `download_audio_playlist` y `download_audio_playlist_usb` repiten `format`, `writethumbnail` y `postprocessors`, cada uno con diferencias: `player_client=['android', …]` y un `User-Agent` fijo solo en audio suelto, `final_ext` solo en USB.
  - **Por qué mejorar:** un arreglo hecho en un método no llega a los otros, y el comportamiento cambia según la opción del menú. Además, `player_client=android` no soporta cookies (yt-dlp lo descarta cuando hay cookies) y el `User-Agent` fijo puede no coincidir con el de las cookies exportadas, lo que favorece los 403.
  - **Arreglo propuesto:** un único `_audio_opts(quality, output_dir, extra)` que usen los tres, sin `User-Agent` ni `player_client` fijos (o configurables).

- [ ] **C12. `_rename_hook` es código muerto** — `src/core/download.py`.
  - **Qué pasa:** en el hook de progreso, `info_dict` es una copia que todavía no tiene `filepath` (yt-dlp lo asigna después, en `post_process`), así que el hook sale sin renombrar nada. Verificado: `filepath` llega como `None`.
  - **Por qué mejorar:** confunde (parece que los nombres se sanean y no es así) y obliga a mantener `formatTitle`. Los nombres que genera yt-dlp ya son seguros para FAT/exFAT: verificado que `sanitize_filename` convierte `: ? " < > * | /` a equivalentes de ancho completo.
  - **Arreglo propuesto:** eliminar `_rename_hook` (y `formatTitle` si queda sin uso), o reimplementarlo como post-proceso si de verdad se quieren nombres ASCII.

- [ ] **C13. La carpeta de la playlist usa el título sin sanear** — `src/cli/vidpy.py` (opción 3: `f'{cwd}/{playlist["title"]}'`).
  - **Bug:** un título con `/` crea subcarpetas inesperadas (`AC/DC` → `AC` y dentro `DC`). En FAT/exFAT, caracteres como `:` o `?` hacen fallar la creación de la carpeta.
  - **Por qué mejorar:** es el pendiente "Mejorar manejo de rutas".
  - **Arreglo propuesto:** `Path(cwd) / sanitize_filename(playlist['title'])` usando `yt_dlp.utils.sanitize_filename`.

- [ ] **C14. Código y dependencias sin uso**
  - **Qué pasa:** la función `title()` de `formater.py` no se usa. `tqdm`, `moviepy` y `spotipy` están en `requirements.in` pero nadie los importa (la integración con Spotify no existe). `requirements.txt` fue compilado para Python 3.12, mientras que el `.venv` usa 3.14.
  - **Por qué mejorar:** instalación más lenta y pesada (`moviepy` arrastra muchas dependencias) y confusión sobre lo que hace el programa.
  - **Arreglo propuesto:** borrar el código muerto, limpiar `requirements.in` y regenerar con `pip-compile ./requirements.in`. `fastapi` se queda mientras exista `src/web`.

- [ ] **C15. `cookies_from_browser='firefox'` fijo en la CLI** — `src/cli/vidpy.py`.
  - **Qué pasa:** si no hay `cookies.txt`, la CLI siempre intenta leer las cookies de Firefox, aunque el usuario use otro navegador o Firefox no esté instalado. El sync no lo hace, así que la CLI y el sync se comportan distinto.
  - **Por qué mejorar:** comportamiento implícito y distinto entre los dos modos.
  - **Arreglo propuesto:** usar solo `YTDLP_COOKIES_FROM_BROWSER`, o documentar Firefox como respaldo y aplicarlo igual en el sync.

### D. Documentación y herramientas (prioridad media/baja)

- [ ] **D16. `README.md` obsoleto**
  - **Qué pasa:** indica `python vidpy.py` (no funciona; es `python -m src.cli.vidpy`), describe una integración con Spotify que no existe y no menciona el sync USB, las cookies ni ffmpeg.
  - **Arreglo propuesto:** reescribirlo: instalación, ffmpeg, cookies, uso de la CLI, sync USB y un ejemplo de regla udev + servicio systemd.

- [X] **D17. Este archivo (`correcciones.md`) estaba desactualizado** — ✅ actualizado con la auditoría
  - **Qué pasa:** había marcas `[X]`/`[ ]` que no reflejaban el estado real.
  - **Arreglo propuesto:** mantenerlo al día al cerrar cada punto (marcar `[X]` e indicar el commit).

- [ ] **D18. `src/web` está roto (se deja como WIP)**
  - **Qué pasa:** `main.py` importa `from core.download import getResolutions`, una función que ya no existe (ahora es `src.core.download.YTDLP`). Faltan `jinja2` y `uvicorn` en los requirements, y las plantillas apuntan a rutas no implementadas (`/descargar-audio`).
  - **Decisión:** dejarlo como está por ahora. Si se retoma, el primer paso es usar `YTDLP` e implementar las rutas.

- [ ] **D19. No hay tests**
  - **Por qué mejorar:** cada cambio en `sync.py` o `formater.py` se verifica a mano con descargas reales.
  - **Arreglo propuesto:** `pytest` para las partes que no necesitan red:
    - `formatDescription` (incluido el caso de A2)
    - `find_cover` / `set_metadata` (con un mp3 generado con ffmpeg)
    - `db.py`
    - `get_db_path` (con un `.db` válido y uno ajeno, caso B6)
    - la lógica de `sync_usb` con un `YTDLP` falso (`get_playlist_page` y `download_audio_playlist_usb` simulados)

    Opcional: `ruff` como linter.

- [ ] **D20. Hay que ejecutarlo desde la raíz del repo**
  - **Qué pasa:** sin empaquetado, `python -m src.cli.vidpy` solo funciona con el repo en el CWD. Además, la CLI descarga en el CWD, así que para descargar en otra carpeta hay que hacer malabares con `PYTHONPATH`.
  - **Arreglo propuesto:** un `pyproject.toml` mínimo con un script `vidpy = "src.cli.vidpy:main"` y `pip install -e .`.
