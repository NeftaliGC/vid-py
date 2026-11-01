# Correcciones que deben hacerse en el programa

# Pendiente

## Del backlog original
---

- [ ] Agregar espacios al seleccionar una opcion del menu
- [ ] Mejorar barra de progreso en la descarga de una playlist
- [ ] Agregar una interfas intuitiva
- [ ] Bloqueo de API
- [ ] Mejorar manejo de rutas → ver **C13**

## Derivados de correcciones ya hechas
---

- [ ] **Regenerar `requirements.txt`** con `pip-compile ./requirements.in`: todavía fija `yt-dlp==2026.3.17` (la versión que daba HTTP 403).
- [ ] **Cambiar o quitar el límite de canciones (`max_tracks`) desde la CLI** (B10): hoy hay que editar la BD a mano.
- [ ] **mp3 truncado al desconectar la USB** (B9): si se desconecta justo mientras ffmpeg escribe el `.mp3`, el siguiente sync lo daría por descargado. Arreglo posible: convertir a un archivo temporal y renombrar al final.
- [ ] **Verificar el lock de B8 en una USB FAT/exFAT real** (en Linux `flock` lo implementa la capa VFS, así que debería funcionar).

## C. Consistencia y código muerto (prioridad media) — se deja para otra ocasión
---

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

## D. Documentación y herramientas (prioridad media/baja)
---

- [ ] **D16. `README.md` obsoleto**
  - **Qué pasa:** indica `python vidpy.py` (no funciona; es `python -m src.cli.vidpy`), describe una integración con Spotify que no existe y no menciona el sync USB, las cookies ni ffmpeg.
  - **Arreglo propuesto:** reescribirlo: instalación, ffmpeg, cookies, uso de la CLI, sync USB y un ejemplo de regla udev + servicio systemd.

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

---

# Hecho

Auditoría del 2026-11-01. Detalle completo de cada punto en el mensaje de su commit.

| Punto | Qué se corrigió | Commit |
|---|---|---|
| — | BD del sync: registro al existir el mp3, offset real, reintento de fallos | `7b22d6a` |
| — | Portada en cualquier formato (`.webp`, `.jpg`, `.png`…), recorte en memoria | `7b22d6a` |
| — | Cookies desde `cookies.txt` (antes nunca se usaban); fuente visible | `7b22d6a` |
| — | HTTP 403: `requirements.in` pide `yt-dlp[default]>=2026.10.26` | `5ab8daa` |
| A1 | La opción 2 ignoraba la resolución (`height<=720p` = 720 petabytes) | `5ab8daa` |
| A2 | Errores por `None` en la metadata; tags de YouTube Music y títulos limpios | `33f066b` |
| A3 | URLs inválidas/privadas sin traceback ni bloqueos; `&list=` ya no baja la playlist completa | `b9bccd6` |
| A4 | La CLI informa el resultado real de cada descarga | `b9bccd6` |
| A5 | Índice de la playlist validado (antes `0` bajaba solo la última); mensajes de Rich en español | `ce15d1c` |
| B6 | Solo un `.db` con el esquema de vidpy marca la USB | `0e641b1` |
| B7 | Un error en una USB no detiene a las demás; resumen y código de salida 1 | `1eb3176` |
| B8 | Lock por USB (`flock` sobre el `.db`) contra syncs simultáneos | `b324bef` |
| B9 | USB desconectada: se detiene sin escribir fuera de la USB ni crear BDs vacías | `7369039` |
| B10 | Falta de espacio: estimación al registrar, "solo lo que quepa", listado, corte al llenarse, pendientes y resumen | `2378bb4` |
| D17 | Este archivo, actualizado con la auditoría | `5ab8daa` |

Del backlog original también quedaron resueltos: la portada al cambiar el nombre del archivo, saltar videos no disponibles en una playlist, separar el código, mejorar la inserción de metadatos (A2), obtener portadas en cualquier formato, playlists no disponibles (A3) y el manejo de la selección en el menú (A5).
