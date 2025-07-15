from fastapi import FastAPI, Form, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fontTools.ttLib import TTFont, newTable
from fontTools.pens.ttGlyphPen import TTGlyphPen
from PIL import Image
import potrace
import os, base64, io, time

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
    glyph_order = [".notdef"]
    glyf_table = newTable("glyf")
    hmtx = {}
    cmap = {}
    glyphs = font.getGlyphSet()

    for fname in os.listdir("glyphs"):
        if not fname.endswith(".png"): continue
        codepoint = int(fname.split(".")[0])
        img = Image.open(f"glyphs/{fname}").convert("L").resize((1000, 1000))
        bw = img.point(lambda x: 0 if x < 128 else 255, "1")

        bitmap = []
        pixels = bw.load()
        for y in range(bw.height):
            row = []
            for x in range(bw.width):
                row.append(1 if pixels[x, y] == 0 else 0)
            bitmap.append(row)

        bmp = potrace.Bitmap(bitmap)
        path = bmp.trace()
        pen = TTGlyphPen(glyphs)

        for curve in path:
            start = curve.start_point
            pen.moveTo(start)
            for segment in curve:
                if segment.is_corner:
                    pen.lineTo(segment.c)
                else:
                    pen.qCurveTo(segment.c1, segment.c2)
            pen.closePath()

        glyph_name = f"uni{codepoint:04X}"
        glyph_order.append(glyph_name)
        glyf_table[glyph_name] = pen.glyph()
        hmtx[glyph_name] = (1000, 0)
        cmap[codepoint] = glyph_name

    # テーブル構成
    font["glyf"] = glyf_table
    font["hmtx"] = newTable("hmtx"); font["hmtx"].metrics = hmtx
    font["cmap"] = newTable("cmap")
    from fontTools.ttLib.tables._c_m_a_p import CmapSubtable
    subtable = CmapSubtable.newSubtable(4)
    subtable.platformID = 3
    subtable.platEncID = 1
    subtable.language = 0
    subtable.cmap = cmap
    font["cmap"].tables = [subtable]
    font["head"] = newTable("head"); font["head"].unitsPerEm = 1000
    font["maxp"] = newTable("maxp"); font["maxp"].numGlyphs = len(glyph_order)
    font["name"] = newTable("name"); font["name"].names = []
    font["post"] = newTable("post"); font["post"].formatType = 3.0
    font.setGlyphOrder(glyph_order)
    font.save("myfont.ttf")
    return FileResponse("myfont.ttf", media_type="font/ttf", filename="myfont.ttf")
