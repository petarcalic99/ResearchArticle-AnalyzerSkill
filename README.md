# ResearchArticle-AnalyzerSkill

A **Claude Code skill** that turns research-paper PDFs into clean 1–2 page summaries: a minimalistic Markdown file and a self-contained HTML one-pager with the key figures embedded. Drop PDFs into a folder, open the repo in Claude Code, and ask — single paper or a whole folder.

> ⚠️ **Works only with [Claude Code](https://claude.com/claude-code)** (Anthropic's agentic CLI). This is a Claude *skill*, not a standalone program — it uses a Claude subagent to read each paper and look up its authors, so it won't run on its own.

## How it works

For each PDF: `extract.py` pulls clean text + figures with PyMuPDF → a Claude subagent writes the structured summary (and looks up author reputation via the free OpenAlex API) → `render.py` turns that Markdown into styled, self-contained HTML. Each summary has: title, one-line summary, problem→solution intro, a bulleted breakdown, key findings & results, methodology & limitations, and a one-line author note.

When pointed at a folder, every paper is summarized by its **own subagent running in parallel** — so papers never mix into each other's context, and a whole batch finishes in roughly the time a single paper takes.

## Files

```
.claude/skills/paper-summarizer/   # the skill — auto-discovered by Claude Code in this repo
├── SKILL.md                      # the orchestration Claude follows
├── scripts/extract.py            # PDF → Markdown + figure images (PyMuPDF)
├── scripts/render.py             # Markdown → academic HTML (figures inlined as base64)
├── prompts/summarizer-agent.md   # the summarizing subagent's instructions
├── assets/style.css              # the HTML styling (academic / clean)
└── requirements.txt              # Python deps
Research_Articles/                 # put your PDFs here
Summaries/                         # generated outputs (example results included)
```

## Setup (one-time)

The skill is already in `.claude/skills/`, so Claude Code finds it automatically when you open this repo. You only install the Python dependencies (Python 3.10+; three prebuilt wheels — `pymupdf4llm`, `PyMuPDF`, `Markdown`):

```bash
python3 -m venv .claude/skills/paper-summarizer/.venv
.claude/skills/paper-summarizer/.venv/bin/python -m pip install -r .claude/skills/paper-summarizer/requirements.txt
```

A venv keeps them isolated (Homebrew/Debian Python blocks system-wide `pip`). The skill auto-detects this venv; alternatively install the three packages into any Python and set `export PAPER_SUMMARIZER_PYTHON=/path/to/python`. _(Want it in every repo instead of just this one? Copy `.claude/skills/paper-summarizer/` into `~/.claude/skills/`.)_

## Use it

1. Put your PDFs in `Research_Articles/` (or any folder).
2. Open this repo in Claude Code and ask:
   - `summarize all the papers in Research_Articles/`
   - `summarize Research_Articles/whisperpair.pdf`
3. Find each paper's `summary.md` + `summary.html` in `Summaries/<paper>/` — open the HTML in a browser.

The `Summaries/` folder already contains example results generated from the three papers in `Research_Articles/`.