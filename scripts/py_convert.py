#!/usr/bin/env python3
"""Convert BACN law pages (cached by py_fetch.py) to Markdown: leyes/<year>/ley-<n>.md,
constitucion/, codes kept with the laws (Paraguayan codes are laws)."""
import os
import re
import sys
import unicodedata
from datetime import date

import yaml
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import py_textmd as T  # noqa: E402

RAW = os.environ.get("RAW", "/Users/magicaltux/projects/lawcodex/_raw/py")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://www.bacn.gov.py"
TODAY = date.today().isoformat()
BLOCKS = ("p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr")


def _cp1252_fallback(err):
    """Pages are UTF-8 but some contain stray single-byte (cp1252) characters."""
    bad = err.object[err.start:err.end]
    return bad.decode("cp1252", "replace"), err.end


import codecs  # noqa: E402
codecs.register_error("cp1252fallback", _cp1252_fallback)


def decode(raw):
    return raw.decode("utf-8", "cp1252fallback")


def slug(t, n=70):
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:n].rstrip("-")


def dmy(x):
    m = re.search(r"(\d{2})-(\d{2})-(\d{4})", x or "")
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None


def blocks_of(el):
    """Text blocks: split on <br> and block elements, keep order."""
    for br in el.find_all("br"):
        br.replace_with("\n")
    out = []
    for t in el.find_all(BLOCKS):
        if t.find(BLOCKS):
            continue
        txt = t.get_text(" ")
        for part in txt.split("\n"):
            part = re.sub(r"\s+", " ", part.replace("\xa0", " ")).strip()
            if part:
                out.append(part)
    if not out:
        out = [re.sub(r"\s+", " ", l).strip() for l in el.get_text("\n").split("\n") if l.strip()]
    return out


def parse(raw):
    soup = BeautifulSoup(decode(raw), "lxml")
    h = soup.select_one("h1.entry-title, h1.page-title, article h1, h1")
    title = re.sub(r"\s+", " ", h.get_text(" ", strip=True)) if h else ""
    ec = soup.select_one("div.entry-content")
    if ec is None:
        return None
    meta = {}
    for li in ec.select("ol.breadcrumb li"):
        t = li.get_text(" ", strip=True)
        if "Promulgación" in t:
            meta["promulgacion"] = dmy(t)
        if "Publicación" in t:
            meta["publicacion"] = dmy(t)
    a = ec.find("a", href=re.compile(r"/descarga/"))
    meta["pdf"] = a["href"] if a else None
    meta["record"] = " ".join(li.get_text(" ", strip=True) for li in ec.select("ol.breadcrumb li"))
    for t in ec.select("div.row, iframe, h4, hr, audio, ol.breadcrumb"):
        t.decompose()
    blocks = blocks_of(ec)
    return title, meta, blocks


CONST_PDF = "https://ministeriodejusticia.gov.py/wp-content/uploads/2024/03/1.Constitucion-Nacional.pdf"


def constitution():
    """BACN only offers the signed original as a scanned PDF; the text comes from the PDF
    published by the Ministerio de Justicia (layout-mode extraction avoids split words)."""
    import logging
    import pypdf
    import requests
    logging.disable(logging.WARNING)
    d = os.path.join(RAW, "const")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, "m.pdf")
    if not T.pdf_ok(p):
        open(p, "wb").write(requests.get(CONST_PDF, headers={"User-Agent": "LawCodex/1.0 (+https://github.com/LawCodex)"}, timeout=300).content)
    pages = [pg.extract_text(extraction_mode="layout") or "" for pg in pypdf.PdfReader(p).pages]
    pages = ["\n".join(l.rstrip() for l in t.split("\n")) for t in pages]
    md = T.lines_to_md(T.clean_pages(pages))
    front = {"title": "Constitución Nacional de la República del Paraguay", "identifier": "Constitución de 1992",
             "type": "constitution", "jurisdiction": "py", "language": "es", "date": "1992-06-20", "status": "in_force",
             "source": CONST_PDF, "retrieved": TODAY}
    fm = yaml.safe_dump(front, allow_unicode=True, sort_keys=False, width=1000).strip()
    path = os.path.join(REPO, "constitucion", "constitucion-nacional-1992.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write("\n".join(["---", fm, "---", "", f"# {front['title']}", "",
        "> Texto publicado por el Ministerio de Justicia (PDF). El original firmado está en la BACN: "
        "https://www.bacn.gov.py/CONSTITUCION_ORIGINAL_FIRMADA.pdf (imagen escaneada).", "", md, ""]))
    print("constitution", md.count("###### "))


def main():
    d = os.path.join(RAW, "html")
    st = {}
    urls = dict(l.rstrip("\n").split("\t") for l in open(os.path.join(RAW, "urls.tsv")))
    used = set()
    for f in sorted(os.listdir(d), key=lambda x: (len(x), x)):
        if not f.endswith(".html"):
            continue
        key = f[:-5]
        res = parse(open(os.path.join(d, f), "rb").read())
        if not res:
            continue
        title, meta, blocks = res
        body = " ".join(blocks)
        # pages found by id probing include bill records ("Fecha de sanción", "Camara", "Presentado por")
        is_law = key == "constitucion" or "Promulgación" in meta.get("record", "") or re.search(
            r"CONGRESO DE LA NACI[ÓO]N PARAGUAYA|SANCIONA CON FUERZA DE", body[:3000], re.I)
        if not is_law:
            st["not_law"] = st.get("not_law", 0) + 1
            continue
        if len(body) < 100:
            st["empty"] = st.get("empty", 0) + 1
            continue
        if key == "constitucion":
            folder, typ, num = "constitucion", "constitution", None
            title = title or "Constitución Nacional de la República del Paraguay"
            fn = "constitucion/constitucion-nacional-1992.md"
        else:
            m = re.match(r"(?:Ley|LEY)\s*N[º°o]?\.?\s*([\d.]+)", title)
            num = m.group(1).replace(".", "") if m else None
            date_ = meta.get("promulgacion") or meta.get("publicacion")
            # undated pages are sharded by BACN id (GitHub lists <= 1,000 entries per directory)
            year = date_[:4] if date_ else f"sin-fecha/{int(key) // 1000 * 1000:05d}"
            folder = "leyes"
            typ = "code" if re.search(r"/\s*C[ÓO]DIGO\b|\bQUE APRUEBA EL C[ÓO]DIGO\b", title, re.I) else "act"
            fn = f"leyes/{year}/ley-{num}.md" if num else f"leyes/{year}/{slug(title)}-{key}.md"
        if fn in used:  # same number (e.g. a code published in several parts): add the BACN id
            fn = fn[:-3] + f"-{key}.md"
        used.add(fn)
        md = T.blocks_to_md(blocks)
        src = urls.get(key, f"{SITE}/constitucion-nacional-de-la-republica-del-paraguay")
        if src.endswith("/x"):
            src = f"{SITE}/leyes-paraguayas/{key}/"
        front = {"title": title, "identifier": f"Ley N° {num}" if num else None, "type": typ, "jurisdiction": "py",
                 "language": "es", "date": meta.get("promulgacion"), "published": meta.get("publicacion"),
                 "status": "unknown", "source": src, "source_pdf": meta.get("pdf"), "retrieved": TODAY}
        fm = yaml.safe_dump(front, allow_unicode=True, sort_keys=False, width=1000).strip()
        path = os.path.join(REPO, fn)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w", encoding="utf-8").write("\n".join(["---", fm, "---", "", f"# {title}", "",
            "> Texto publicado por la Biblioteca y Archivo Central del Congreso de la Nación (BACN); texto original.", "", md, ""]))
        st[folder] = st.get(folder, 0) + 1
    print(st)


if __name__ == "__main__":
    main()
    constitution()
