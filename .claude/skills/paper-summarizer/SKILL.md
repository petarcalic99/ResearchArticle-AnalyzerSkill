---
name: paper-summarizer
description: Turn one research-article PDF — or a whole folder of them — into a polished 1-2 page summary, output as a minimalistic Markdown file and a beautiful self-contained HTML one-pager. Extracts text + figures with PyMuPDF, launches a subagent to read each paper and write the summary (with an OpenAlex author-reputation lookup), then renders academic-styled HTML. Works in any repository and can batch every PDF in a folder. Use whenever the user wants to summarize / digest / make one-pagers from a paper, a PDF, or a folder of papers.
---

# Paper Summarizer

Turns research-article PDF(s) into two deliverables each: a minimalistic **`summary.md`** (text-only) and a beautiful, self-contained **`summary.html`** (academic style, key figures embedded). Can **batch-process every PDF in a folder**.

Pipeline per paper: `extract.py` (PDF → markdown + figures) → **subagent** (reads the paper, writes the summary) → `render.py` (→ HTML).

---

## Conventions
- **`SKILL_DIR`** = this skill's own folder — the absolute path Claude Code reports as the skill's **base directory** when it loads (the directory holding this `SKILL.md`, plus `scripts/`, `prompts/`, `assets/`, `requirements.txt`). It works whether the skill is repo-local (`<repo>/.claude/skills/paper-summarizer`) or global (`~/.claude/skills/paper-summarizer`). Substitute that exact path wherever `$SKILL_DIR` appears.
- **`REPO`** = the current working directory (the repo you're in). Inputs and outputs are resolved relative to here.
- Always call the helper scripts with the **detected `$PY`** (from Phase 0) and absolute paths.

---

## Phase 0: Locate a Python that has the dependencies

```bash
SKILL_DIR="…"   # ← this skill's base directory (the path shown when the skill loaded)
PY=""
for c in "$PAPER_SUMMARIZER_PYTHON" "$SKILL_DIR/.venv/bin/python" "./.venv/bin/python" "$(command -v python3)" "/opt/homebrew/bin/python3"; do
  [ -n "$c" ] || continue
  if "$c" -c "import pymupdf4llm, fitz, markdown" 2>/dev/null; then PY="$c"; break; fi
done
if [ -n "$PY" ]; then echo "PY=$PY"; else echo "DEPS_MISSING"; fi
```

- If it prints `PY=<path>`, use that interpreter as `$PY` for every script call below.
- If it prints `DEPS_MISSING`, **STOP and tell the user to install the dependencies** (it's a one-time step — see the repo README), offering to run it for them with the real `SKILL_DIR`:
  ```bash
  python3 -m venv "$SKILL_DIR/.venv"
  "$SKILL_DIR/.venv/bin/python" -m pip install -r "$SKILL_DIR/requirements.txt"
  ```
  Do not continue until the deps import cleanly.

---

## Phase 1: Resolve the input PDF(s)

Determine the target set from the user's request:
- **A named folder** → use it.
- **A named file** → just that PDF.
- **"all" / "every paper" / "the folder" / nothing specific** → find the papers folder in `REPO`, trying in order: any folder the user mentioned, then `Research_Articles`, `articles`, `papers`, `pdfs`, `PDFs`; if none exist, scan `REPO` itself.

Collect **every `*.pdf`** in the chosen location (recursively), **excluding anything under a `Summaries/` folder**. Sort the list. Tell the user how many PDFs you found (and list them) before processing.

For each PDF compute:
- `STEM` = basename without `.pdf`, sanitized: `STEM=$(printf '%s' "$(basename "$pdf" .pdf)" | tr -c 'A-Za-z0-9._-' '-')` (use `printf`, not a pipe from `basename` directly, so the trailing newline isn't turned into a stray `-`).
- `OUT="$REPO/Summaries/$STEM"`, `WORK="$OUT/_work"`.

Then run Phases 2–4 for each PDF (this is the batch loop).

---

## Phase 2: Extract (PDF → markdown + figures)

```bash
"$PY" "$SKILL_DIR/scripts/extract.py" --pdf "<ABS_PDF>" --out "$WORK"
```

Parse the single JSON status line:
- `ok:true` → continue (note `n_figures`, `extracted_md`, `figures_json`).
- `ok:false, scanned:true` → the PDF has no text layer (scanned image). Tell the user OCR isn't installed and skip this file (suggest `ocrmypdf` or a text-based PDF).
- other `ok:false` → report `reason` and skip.

---

## Phase 3: Summarize (subagent returns text → you write the file)

Subagents may be sandboxed (no file writes, no web) in some environments, so use this robust pattern:

1. Build a **figure list** from `$WORK/figures.json` — one line per figure: `- Figure <fig_number>: <caption>`. If `[]`, use `(no figures were extracted)`.
2. Read `$SKILL_DIR/prompts/summarizer-agent.md` and substitute:
   - `{{EXTRACTED_MD_PATH}}` → `$WORK/extracted.md`
   - `{{FIGURE_LIST}}` → the list from step 1
   - `{{FIGURES_JSON_PATH}}` → `$WORK/figures.json`
   - `{{USER_EMAIL}}` → the user's email if known (OpenAlex politeness), else `none`.
3. **Launch a Task subagent** (`subagent_type: general-purpose`) with the substituted prompt. It **returns the complete summary Markdown as its final message** (it does not write a file).
4. **You write** that Markdown verbatim to `$OUT/summary.md` — strip any surrounding ``` fences or preamble so the file begins with `# `.
5. **Complete the author lookup if needed.** If the text contains a marker `[[AUTHOR_LOOKUP_NEEDED: <name> | <affiliation>]]`, do the lookup yourself with WebFetch and rewrite the *About the authors* sentence:
   `https://api.openalex.org/authors?search=<urlenc name>&per_page=5&select=display_name,works_count,cited_by_count,summary_stats,last_known_institutions,affiliations` (append `&mailto=<email>` if known).
   Disambiguate by matching the paper's affiliation; write institution + "≈N published works" + h-index/citations (hedge if uncertain), and delete the marker. If web is unavailable, just delete the marker and keep the paper-grounded sentence.
6. Verify `summary.md` starts with `# ` and contains `## What they did`, `## Key findings & results`, `## Methodology & limitations`, `## About the authors`. If something's missing, relaunch the subagent once with a corrective note.

---

## Phase 4: Render (`summary.md` → `summary.html`)

```bash
"$PY" "$SKILL_DIR/scripts/render.py" \
  --summary "$OUT/summary.md" \
  --figures "$WORK/figures.json" \
  --figdir  "$WORK/figures" \
  --css     "$SKILL_DIR/assets/style.css" \
  --out     "$OUT/summary.html"
```

`embedded_figures` in its JSON output lists which figures the summary referenced and got embedded.

---

## Phase 5: Report

Per paper, give the two deliverables and embedded figures:
- `Summaries/<STEM>/summary.md` — minimalistic, text-only
- `Summaries/<STEM>/summary.html` — self-contained academic one-pager (open in a browser)

For a **batch**, print one result line per paper plus a total. Intermediates in `Summaries/<STEM>/_work/` (extracted markdown + figure PNGs) can be deleted.
