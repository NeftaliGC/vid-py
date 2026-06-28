from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from core.download import getResolutions
import os

web_path = os.path.dirname(os.path.abspath(__file__))
webtemplates_path = os.path.join(web_path, "templates")
webstatic_path = os.path.join(web_path, "static")

app = FastAPI()

# Static files and templates
app.mount("/static", StaticFiles(directory=webstatic_path), name="static")
templates = Jinja2Templates(directory=webtemplates_path)

@app.get("/", response_class=HTMLResponse)
async def root():
    return templates.TemplateResponse("index.html", {"request": {}})

@app.get("/descargar-video/", response_class=HTMLResponse)
async def video(request: Request, id_video: str | None = None):
    if id_video == None:
        return templates.TemplateResponse("video.html", {"request": request})

    resolutions = getResolutions(id_video)
    return templates.TemplateResponse("video.html", {"request": request, "id_video": id_video, "resolutions": resolutions})
