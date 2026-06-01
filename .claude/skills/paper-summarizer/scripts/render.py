#!/usr/bin/env python3
"""Render summary.md into a self-contained academic HTML one-pager.

- Converts Markdown to HTML (pure-Python `markdown`, no pandoc).
- Embeds the figures the summary actually references ("Figure N") as base64
  data URIs, inserted right after the block that first mentions each one. The
  Markdown stays clean/text-only; figures live only in the HTML.
- Tags fixed sections for styling: .lead standfirst, .key-points list,
  .author-card byline.
- Emits ONE file with an inlined <style> and no external/CDN URLs.

Prints one JSON status line: {"ok":true,"out":"...","embedded_figures":[1,3]}
"""
import argparse
import base64
import html
import json
import os
import re
import sys

import markdown

FIG_MENTION = re.compile(r"\bfig(?:ure)?s?\.?\s*([\d,\s\-–and&]+)", re.IGNORECASE)


def referenced_numbers(text):
    """Ordered, unique figure numbers referenced in prose (handles 'Figures 1 and 2')."""
    nums = []
    for m in FIG_MENTION.finditer(text):
        for nm in re.findall(r"\d+", m.group(1)):
            n = int(nm)
            if n not in nums:
                nums.append(n)
    return nums


def load_title(md_text):
    m = re.search(r"^#\s+(.*)$", md_text, flags=re.MULTILINE)
    return m.group(1).strip() if m else "Paper summary"


def figure_html(fig, figdir):
    path = os.path.join(figdir, os.path.basename(fig["file"]))
    if not os.path.isfile(path):
        return ""
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    cap = html.escape(fig.get("caption") or f"Figure {fig.get('fig_number')}")
    alt = html.escape(f"Figure {fig.get('fig_number')}")
    return (f'\n<figure class="paper-figure">'
            f'<img alt="{alt}" src="data:image/png;base64,{b64}">'
            f'<figcaption>{cap}</figcaption></figure>\n')


def insert_placeholders(md_text, available):
    """Insert [[FIGURE:n]] markers after the Markdown block that first cites each figure.

    `available` maps fig_number -> figure dict. Markdown blocks are blank-line
    delimited, so a placeholder added as its own block survives conversion as a
    standalone <p> we later swap for the <figure>.
    """
    blocks = re.split(r"\n\s*\n", md_text)
    out, placed = [], set()
    for blk in blocks:
        out.append(blk)
        for n in referenced_numbers(blk):
            if n in available and n not in placed:
                out.append(f"[[FIGURE:{n}]]")
                placed.add(n)
    # Any referenced-but-unplaced figures (shouldn't normally happen) -> appended at end.
    for n in referenced_numbers(md_text):
        if n in available and n not in placed:
            out.append(f"[[FIGURE:{n}]]")
            placed.add(n)
    return "\n\n".join(out), placed


def tag_sections(html_out):
    # Standfirst: the "**Summary:**" paragraph.
    html_out = re.sub(r"<p>(<strong>\s*Summary\s*:?\s*</strong>)",
                      r'<p class="lead">\1', html_out, count=1, flags=re.IGNORECASE)
    # Key findings list -> styled callout box.
    html_out = re.sub(r"(<h2>\s*Key findings\s*&amp;\s*results\s*</h2>\s*)<ul>",
                      r'\1<ul class="key-points">', html_out, count=1, flags=re.IGNORECASE)
    # About the authors -> byline card (wraps heading + body up to next h2 / end).
    html_out = re.sub(
        r"<h2>\s*About the authors\s*</h2>(.*?)(?=<h2|\Z)",
        lambda m: '<aside class="author-card"><h2>About the authors</h2>' + m.group(1) + "</aside>",
        html_out, count=1, flags=re.IGNORECASE | re.DOTALL)
    return html_out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", required=True)
    ap.add_argument("--figures", required=True, help="path to figures.json")
    ap.add_argument("--figdir", required=True, help="dir holding the figure PNGs")
    ap.add_argument("--css", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    with open(args.summary, encoding="utf-8") as f:
        md_text = f.read()

    available = {}
    if os.path.isfile(args.figures):
        with open(args.figures, encoding="utf-8") as f:
            for fig in json.load(f):
                n = fig.get("fig_number")
                if n is not None and n not in available:
                    available[n] = fig

    md_with_marks, placed = insert_placeholders(md_text, available)

    body = markdown.markdown(
        md_with_marks,
        extensions=["extra", "sane_lists", "smarty"],
        output_format="html5",
    )

    # Swap placeholders for real <figure> blocks (markdown wraps them in <p>).
    embedded = []
    for n in sorted(placed):
        fig_markup = figure_html(available[n], args.figdir)
        for token in (f"<p>[[FIGURE:{n}]]</p>", f"[[FIGURE:{n}]]"):
            if token in body:
                body = body.replace(token, fig_markup)
                if fig_markup:
                    embedded.append(n)
                break

    body = tag_sections(body)

    with open(args.css, encoding="utf-8") as f:
        css = f.read()
    title = html.escape(load_title(md_text))

    doc = (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{title}</title>\n<style>\n{css}\n</style>\n</head>\n"
        f'<body>\n<main class="page">\n{body}\n</main>\n</body>\n</html>\n'
    )
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(doc)

    print(json.dumps({"ok": True, "out": os.path.abspath(args.out),
                      "embedded_figures": sorted(set(embedded))}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
