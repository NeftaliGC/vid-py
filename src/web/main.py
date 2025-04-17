from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
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

