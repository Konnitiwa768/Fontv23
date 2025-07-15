from fastapi import FastAPI, Form, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os, base64, io, time
from PIL import Image
from fontTools.ttLib import TTFont, newTable
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.svgLib.path import parse_path
import requests

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

os.makedirs("glyphs", exist_ok=True)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/save_glyph")
async def save_glyph(char: str = Form(...), image: str = Form(...)):
    codepoint = ord(char)
    img_data = base64.b64decode(image.split(",")[1])
    img = Image.open(io.BytesIO(img_data)).convert("L").resize((1000, 1000))
    img.save(f"glyphs/{codepoint}.png")
    return {"status": "ok"}

@app.get("/build_font")
def build_font():
    font = TTFont()
    font.setGlyphOrder([".notdef"])
    glyphs = font.getGlyphSet()
    pen = TTGlyphPen(glyphs)

    glyf_table = newTable('glyf')
    hmtx = {}
    cmap = {}
    glyph_order = [".notdef"]

    for fname in os.listdir("glyphs"):
        if not fname.endswith(".png"):
            continue
        codepoint = int(fname.split(".")[0])
        img = Image.open(f"glyphs/{fname}").convert("1").resize((1000, 1000))
        img_data = img.tobytes()

        pen = TTGlyphPen(glyphs)
        for y in range(1000):
            for x in range(1000):
                if img.getpixel((x, y)) == 0:
                    pen.moveTo((x, 1000 - y))
                    pen.lineTo((x + 1, 1000 - y))
                    pen.lineTo((x + 1, 999 - y))
                    pen.lineTo((x, 999 - y))
                    pen.closePath()
        glyph = pen.glyph()
        name = f"uni{codepoint:04X}"
        glyf_table[name] = glyph
        hmtx[name] = (1000, 0)
        cmap[codepoint] = name
        glyph_order.append(name)

    font["glyf"] = glyf_table
    font["hmtx"] = newTable("hmtx")
    font["hmtx"].metrics = hmtx
    font["cmap"] = newTable("cmap")
    font["cmap"].tableVersion = 0
    font["cmap"].tables = []
    from fontTools.ttLib.tables._c_m_a_p import CmapSubtable
    cmap_table = CmapSubtable.newSubtable(4)
    cmap_table.platformID = 3
    cmap_table.platEncID = 1
    cmap_table.language = 0
    cmap_table.cmap = cmap
    font["cmap"].tables.append(cmap_table)

    font["head"] = newTable("head")
    font["head"].unitsPerEm = 1000
    font["maxp"] = newTable("maxp")
    font["maxp"].numGlyphs = len(glyph_order)
    font["name"] = newTable("name")
    font["name"].names = []
    font["post"] = newTable("post")
    font["post"].formatType = 3.0
    font.setGlyphOrder(glyph_order)

    font.save("myfont.ttf")
    return FileResponse("myfont.ttf", media_type="application/x-font-ttf", filename="myfont.ttf")

@app.post("/upload_font")
def upload_font():
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    REPO = "yourusername/yourrepo"  # 変更！
    PATH = f"fonts/myfont-{int(time.time())}.ttf"
    url = f"https://api.github.com/repos/{REPO}/contents/{PATH}"

    with open("myfont.ttf", "rb") as f:
        content = base64.b64encode(f.read()).decode("utf-8")

    res = requests.put(url, headers={
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }, json={
        "message": "upload font",
        "content": content
    })

    try:
        return {"url": res.json()["content"]["html_url"]}
    except:
        return {"error": res.text}
