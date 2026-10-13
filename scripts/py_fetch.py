#!/usr/bin/env python3
"""Paraguay: download the law pages ("Leyes Paraguayas") of the Biblioteca y Archivo Central
del Congreso de la Nación (BACN, https://www.bacn.gov.py) — each page carries the full text of
the law in HTML — plus the Constitution page. URLs come from the site's sitemap.xml and the
"leyes por año" listings. One request at a time, >= 1 s apart. Raw HTML cached in $RAW/html/.

Usage: py_fetch.py [urls|pages]
"""
import os
import re
import sys
import time

import requests

RAW = os.environ.get("RAW", "/Users/magicaltux/projects/lawcodex/_raw/py")
UA = "LawCodex/1.0 (+https://github.com/LawCodex)"
SITE = "https://www.bacn.gov.py"
s = requests.Session()
s.headers["User-Agent"] = UA
_last = [0.0]


def get(url):
    for k in range(5):
        w = 1.0 - (time.time() - _last[0])
        if w > 0:
            time.sleep(w)
        _last[0] = time.time()
        try:
            r = s.get(url, timeout=(30, 180))
            if r.status_code == 200:
                return r.content
            if r.status_code == 404:
                return None
            print("HTTP", r.status_code, url, file=sys.stderr, flush=True)
        except requests.RequestException as e:
            print("ERR", url, e, file=sys.stderr, flush=True)
        time.sleep(10 * (k + 1))
    return None


def urls():
    sm = get(SITE + "/sitemap.xml").decode("utf-8", "replace")
    found = {}
    for u in re.findall(r"<loc>([^<]+)</loc>", sm):
        m = re.match(re.escape(SITE) + r"/leyes-paraguayas/(\d+)/", u)
        if m:
            found[int(m.group(1))] = u
    # the sitemap omits many laws: probe every other numeric id up to the highest one seen
    top = max(found) + 200
    for i in range(1, top):
        if i not in found:
            found[i] = f"{SITE}/leyes-paraguayas/{i}/x"
    with open(os.path.join(RAW, "urls.tsv"), "w") as f:
        for i in sorted(found):
            f.write(f"{i}\t{found[i]}\n")
    print("urls", len(found))


def pages(workers=3):
    """Law pages; up to 3 parallel connections, each paced at 1 request/s."""
    import threading
    from concurrent.futures import ThreadPoolExecutor
    d = os.path.join(RAW, "html")
    os.makedirs(d, exist_ok=True)
    todo = [l.rstrip("\n").split("\t") for l in open(os.path.join(RAW, "urls.tsv"))]
    todo.append(("constitucion", SITE + "/constitucion-nacional-de-la-republica-del-paraguay"))
    local = threading.local()

    def worker(item):
        i, u = item
        p = os.path.join(d, f"{i}.html")
        if (os.path.exists(p) and os.path.getsize(p) > 2000) or os.path.exists(p + ".none"):
            return
        if not hasattr(local, "s"):
            local.s = requests.Session()
            local.s.headers["User-Agent"] = UA
            local.last = 0.0
        for k in range(5):
            w = 1.0 - (time.time() - local.last)
            if w > 0:
                time.sleep(w)
            local.last = time.time()
            try:
                r = local.s.get(u, timeout=(30, 180))
                if r.status_code == 200:
                    if b"lo que estas buscando no existe" in r.content:
                        open(p + ".none", "w").close()
                    else:
                        open(p, "wb").write(r.content)
                    return
                if r.status_code == 404:
                    open(p + ".none", "w").close()
                    return
                print("HTTP", r.status_code, u, file=sys.stderr, flush=True)
            except requests.RequestException as e:
                print("ERR", u, e, file=sys.stderr, flush=True)
            time.sleep(10 * (k + 1))

    n = 0
    with ThreadPoolExecutor(workers) as ex:
        for _ in ex.map(worker, todo):
            n += 1
            if n % 500 == 0:
                print("pages", n, len(todo), flush=True)
    print("done", n)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd in ("urls", "all"):
        urls()
    if cmd in ("pages", "all"):
        pages()
