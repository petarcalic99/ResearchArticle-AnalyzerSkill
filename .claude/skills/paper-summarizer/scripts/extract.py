#!/usr/bin/env python3
"""Decompose a research-article PDF into a Claude-friendly form.

Outputs into <out>/:
  - extracted.md      clean Markdown (2-column reading order + tables), via pymupdf4llm
  - figures/fig-*.png figures rendered from the PDF (vector OR raster)
  - figures.json      manifest: [{id,file,page,caption,fig_number,width,height}]

Academic papers draw most figures as *vector* graphics, not embedded raster
images, so we locate each "Figure N" caption and rasterize the graphic region
directly above it (a clip render). This captures vector plots, diagrams, and
raster photos uniformly.

Prints exactly one JSON status line to stdout (diagnostics -> stderr):
  {"ok":true,"scanned":false,"text_chars":N,"n_figures":K,
   "extracted_md":"...","figures_json":"...","figures_dir":"..."}
"""
import argparse
import json
import os
import re
import statistics
import sys

# Require a separator (. : – —) after the number so block-initial *inline*
# references ("Figure 8 presents ...") are rejected and only true captions
# ("Figure 8. ...", "Figure 8: ...") match.
FIG_RE = re.compile(r"^\s*(?:figure|fig\.?|abb\.?|abbildung)\s*(\d+)\s*[.:–—]", re.IGNORECASE)
MIN_W, MIN_H = 70, 50          # minimum figure size in PDF points
CAPTION_MAX = 300             # truncate stored captions
VGAP = 52                     # vertical void (pt) that ends a figure going upward
MAX_FIG_PT = 1500            # target longest side in px after zoom
MAX_FIGURES = 16


def log(*a):
    print(*a, file=sys.stderr)


def normalize(text):
    return re.sub(r"\s+", " ", text or "").strip()


def text_blocks(page):
    """Text blocks only: (x0,y0,x1,y1,text)."""
    out = []
    for b in page.get_text("blocks"):
        if len(b) >= 5 and (len(b) < 7 or b[6] == 0):
            out.append(b)
    return out


def detect_two_column(doc):
    widths = []
    for page in doc:
        pw = page.rect.width or 1
        for b in text_blocks(page):
            if len(b[4].strip()) > 40:
                widths.append((b[2] - b[0]) / pw)
    if not widths:
        return True
    return statistics.median(widths) < 0.6


def graphic_rects(page, fitz):
    """Vector-drawing + placed-raster bounding boxes, dropping page-size backgrounds."""
    page_area = (page.rect.width * page.rect.height) or 1
    rects = []
    try:
        for d in page.get_drawings():
            r = d.get("rect")
            if r and r.width > 3 and r.height > 3 and (r.width * r.height) < 0.85 * page_area:
                rects.append(fitz.Rect(r))
    except Exception as e:                                   # noqa: BLE001
        log(f"get_drawings failed p{page.number+1}: {e}")
    try:
        for inf in page.get_image_info():
            b = inf.get("bbox")
            if b:
                r = fitz.Rect(b)
                if r.width > 3 and r.height > 3 and (r.width * r.height) < 0.85 * page_area:
                    rects.append(r)
    except Exception as e:                                   # noqa: BLE001
        log(f"get_image_info failed p{page.number+1}: {e}")
    return rects


def column_band(crect, page_rect, two_column):
    mid = (page_rect.x0 + page_rect.x1) / 2
    if not two_column or crect.width > 0.58 * page_rect.width:
        return page_rect.x0, page_rect.x1
    if (crect.x0 + crect.x1) / 2 < mid:
        return page_rect.x0, mid + 10
    return mid - 10, page_rect.x1


def figure_region(crect, graphics, caps_above_y, page_rect, two_column, fitz):
    """Cluster graphic rects directly above a caption into the figure's bbox."""
    band0, band1 = column_band(crect, page_rect, two_column)
    members = []
    for g in graphics:
        if g.y1 > crect.y0 + 2:                 # must sit above the caption
            continue
        if g.y1 <= caps_above_y - 2:            # belongs to a figure further up
            continue
        gx0, gx1 = max(g.x0, band0), min(g.x1, band1)
        if gx1 - gx0 < 3:                       # outside this column
            continue
        members.append(fitz.Rect(gx0, g.y0, gx1, g.y1))
    if not members:
        return None
    members.sort(key=lambda r: r.y1, reverse=True)   # nearest the caption first
    cluster = []
    cursor = crect.y0
    for r in members:
        if cluster and (cursor - r.y1) > VGAP:        # hit a void -> figure ended
            break
        cluster.append(r)
        cursor = min(cursor, r.y0)
    fig = fitz.Rect(cluster[0])
    for r in cluster[1:]:
        fig |= r
    fig &= page_rect
    return fig


def extract_figures(doc, fitz, figdir, two_column):
    os.makedirs(figdir, exist_ok=True)
    figures, idx = [], 0
    for pno, page in enumerate(doc):
        page_rect = page.rect
        caps = []
        for b in text_blocks(page):
            cap = normalize(b[4])
            m = FIG_RE.match(cap)
            if m:
                caps.append({"rect": fitz.Rect(b[:4]), "num": int(m.group(1)), "text": cap[:CAPTION_MAX]})
        if not caps:
            continue
        graphics = graphic_rects(page, fitz)
        if not graphics:
            continue
        caps.sort(key=lambda c: c["rect"].y0)
        for ci, cap in enumerate(caps):
            crect = cap["rect"]
            caps_above_y = page_rect.y0
            for cj in range(ci):
                caps_above_y = max(caps_above_y, caps[cj]["rect"].y1)
            fig = figure_region(crect, graphics, caps_above_y, page_rect, two_column, fitz)
            if fig is None or fig.width < MIN_W or fig.height < MIN_H:
                continue
            fig.x0 = max(page_rect.x0, fig.x0 - 4)
            fig.y0 = max(page_rect.y0, fig.y0 - 4)
            fig.x1 = min(page_rect.x1, fig.x1 + 4)
            fig.y1 = min(page_rect.y1, fig.y1 + 4)
            try:
                zoom = max(1.0, min(2.0, MAX_FIG_PT / max(fig.width, fig.height)))
                pix = page.get_pixmap(clip=fig, matrix=fitz.Matrix(zoom, zoom), alpha=False)
                idx += 1
                fid = f"fig-{idx:04d}"
                pix.save(os.path.join(figdir, f"{fid}.png"))
            except Exception as e:                          # noqa: BLE001
                log(f"render failed (fig near p{pno+1}): {e}")
                continue
            figures.append({
                "id": fid,
                "file": f"figures/{fid}.png",
                "page": pno + 1,
                "caption": cap["text"],
                "fig_number": cap["num"],
                "width": pix.width,
                "height": pix.height,
            })
            if idx >= MAX_FIGURES:
                return figures
    return figures


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    pdf = os.path.abspath(args.pdf)
    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)
    figdir = os.path.join(out, "figures")
    extracted_md = os.path.join(out, "extracted.md")
    figures_json = os.path.join(out, "figures.json")

    if not os.path.isfile(pdf):
        print(json.dumps({"ok": False, "scanned": False, "reason": f"PDF not found: {pdf}"}))
        return 0

    import fitz
    import pymupdf4llm

    try:
        doc = fitz.open(pdf)
    except Exception as e:                                  # noqa: BLE001
        print(json.dumps({"ok": False, "scanned": False, "reason": f"cannot open PDF: {e}"}))
        return 0

    # (A) Text-layer probe -> detect scanned / image-only PDFs.
    raw = "".join(page.get_text("text") for page in doc)
    text_chars = len(raw.strip())
    if text_chars < 200:
        with open(extracted_md, "w") as f:
            f.write("<!-- SCANNED_PDF: no usable text layer -->\n")
        with open(figures_json, "w") as f:
            f.write("[]")
        print(json.dumps({
            "ok": False, "scanned": True, "text_chars": text_chars,
            "reason": "no text layer (likely a scanned PDF); OCR is not installed",
        }))
        return 0

    # (B) Clean Markdown (native multi-column reading order + tables).
    try:
        md = pymupdf4llm.to_markdown(pdf, show_progress=False)
    except TypeError:
        md = pymupdf4llm.to_markdown(pdf)
    with open(extracted_md, "w") as f:
        f.write(md)

    # (C) Figures: caption-anchored region rendering.
    try:
        two_column = detect_two_column(doc)
        figures = extract_figures(doc, fitz, figdir, two_column)
    except Exception as e:                                  # noqa: BLE001
        log(f"figure extraction failed: {e}")
        figures = []
    with open(figures_json, "w") as f:
        json.dump(figures, f, indent=2)

    print(json.dumps({
        "ok": True,
        "scanned": False,
        "text_chars": text_chars,
        "n_figures": len(figures),
        "extracted_md": extracted_md,
        "figures_json": figures_json,
        "figures_dir": figdir,
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
