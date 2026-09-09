# CLAUDE.md

Guidance for AI assistants working in this repo. Humans: see `README.md` and
`A_sec-edgar-insider-tracker_spec.md`.

## What this is

Automated pipeline that turns S&P 500 **Form 4** insider-transaction filings into
short, fact-checked news briefs, published as a static Astro site on GitHub Pages.

Pipeline: `fetch → write → qa → publish` (`agents/orchestrator.py`). `fetch` and
`publish` are plain deterministic code; `write` and `qa` are the LLM agents.

## Commands

```bash
# Python (repo root)
py -m pip install -r requirements.txt
for t in tests/test_*.py; do py "$t"; done          # tests (no pytest needed)
py -m agents.orchestrator --date 2026-09-08 --tickers AAPL,MSFT --limit 3 --dry-run-publish

# Site (site/)
npm ci && npm run build        # -> site/dist/ ; also `npm run dev`
```

## Layout

- `agents/` — pipeline stages + `config.py`, `sec_client.py`, `form4_parser.py`,
  `articles.py`, `llm.py`. Phase 3 drafts: `social_agent.py`, `newsletter_agent.py`
  (not wired into the orchestrator).
- `data/` — `sp500_ciks.json` (rebuild: `py data/build_sp500_ciks.py`),
  `published_index.json` (dedupe ledger, keyed by SEC filing URL).
- `site/` — Astro static site. Articles are Markdown in
  `src/content/articles/`, written by `publish_agent.py`.
- `output/<date>/` — per-day working files (git-ignored).
- `.github/workflows/daily_pipeline.yml` — runs the pipeline daily, commits new
  articles, builds `site/` and deploys to Pages (one job, then a `deploy` job).
  `ci.yml` — tests + build on code changes.

## Gotchas

- **No `slug` in article front matter.** Astro reserves it
  (`ContentSchemaContainsSlugError`). The slug is the filename; templates use
  `entry.slug`. `write_agent.py` deliberately omits it.
- **Sitemap/RSS are hand-rolled endpoints** (`site/src/pages/sitemap.xml.js`,
  `rss.xml.js`), not integrations — `@astrojs/sitemap` 3.7 needs Astro 5.
- **Deploy:** project repo `nsvmm-dev/sec-edgar-insider-tracker`, custom apex
  domain `decode-slang.com` (in `site/astro.config.mjs` `site:`,
  `site/public/CNAME`, `site/public/robots.txt`). No `base` path. Cloudflare DNS
  is **DNS-only / grey cloud** so GitHub can issue the TLS cert.
- **Secrets** (GitHub Actions): `ANTHROPIC_API_KEY`, `SEC_USER_AGENT`. Locally:
  `.env` (git-ignored; template `.env.example`).
- `SEC_USER_AGENT` must be `"<app name> <real email>"` or SEC returns 403.
- Numbers come verbatim from filings; the only arithmetic is summing/averaging
  lines within one filing. Never invent missing values (they stay `null`).
- QA body-length bounds: 200–380 words. The write prompt targets 260–340.
