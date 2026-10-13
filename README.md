# LawCodex — Paraguay (py)

Paraguayan legislation as Markdown: the **Constitución Nacional (1992)** and, from the **"Leyes Paraguayas"** collection of the
**Biblioteca y Archivo Central del Congreso de la Nación (BACN)** (https://www.bacn.gov.py):
the **laws** published there with their full text
(the codes — Código Civil, Código Penal, Código Procesal Penal, Código Laboral, etc. — are laws
in Paraguay and are included as such).

Part of [LawCodex](https://github.com/LawCodex): one public repository per jurisdiction.

Retrieved: **2026-10-13**. Language: Spanish (`es`).

Status: **full for the laws published with text by BACN (original texts, not consolidated)**

## What is covered

| Category | Directory | Files |
|---|---|---|
| Constitución Nacional de la República del Paraguay (1992) — text from the Ministerio de Justicia's PDF (BACN only has a scan of the signed original) | `constitucion/` | 1 |
| Laws (leyes), by year of promulgation | `leyes/<year>/ley-<n>.md` | 7,147 |

Each file is the HTML text published on the law's BACN page: TÍTULO/CAPÍTULO/SECCIÓN lines
become headings and each article a `######` heading; quoted articles of amended laws stay in the
text. These are the texts as enacted (original texts), not consolidated versions. The PDF of the
law offered by BACN is linked in the front matter (`source_pdf`).

Of the 12,471 BACN pages fetched, 7,147 are law pages with text; the others found by id probing
are bill records ("Fecha de sanción", "Cámara", "Presentado por") or pages without text, and are
not included. A law published in several parts (e.g. the Código Civil, Ley 1183/85) has one file
per part (the BACN id is appended to the file name).

## What is NOT covered

- Consolidated (in-force) versions: BACN publishes the enacted texts; amendments are separate laws.
- Decrees and other secondary norms.
- Laws without an HTML text on BACN (see above).

## Source

BACN, "Leyes Paraguayas": law pages `https://www.bacn.gov.py/leyes-paraguayas/<id>/<slug>`,
discovered from the site's sitemap.xml and by probing every numeric id up to the highest one
(the sitemap omits many laws). One file per law page; `source` is the page URL.

## Copyright

Paraguay's Ley N° 1328/98 de Derecho de Autor y Derechos Conexos excludes official texts of a
legislative, administrative or judicial nature from copyright protection.

## Regenerate

```
python3 -m venv .venv && .venv/bin/pip install -r scripts/requirements.txt
RAW=/path/to/scratch .venv/bin/python scripts/py_fetch.py      # sitemap + id probing + pages (~13,000 requests)
RAW=/path/to/scratch .venv/bin/python scripts/py_convert.py
```

robots.txt of www.bacn.gov.py has no restrictions; up to 3 parallel connections at 1 request/s each.
