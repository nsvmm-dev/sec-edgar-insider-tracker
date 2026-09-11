# SEC EDGAR Insider-Trading Tracker

Automated pipeline that turns S&P 500 **Form 4** insider-transaction filings into
short, fact-checked, plain-English news briefs for retail investors. Published
as **EdgarHawk** at [decode-slang.com](https://decode-slang.com) (the repo/project
keeps its descriptive engineering name; `SITE_NAME` in `site/src/consts.js` is
the public brand).

Full product spec: [`A_sec-edgar-insider-tracker_spec.md`](A_sec-edgar-insider-tracker_spec.md).
This README covers the implementation and how to run it.

---

## Pipeline

```
fetch ──► write ──► qa ──► publish
(1)       (2)       (3)     (4)
```

| Stage | File | LLM? | What it does |
|-------|------|------|--------------|
| **fetch** | `agents/fetch_agent.py` | no | Collect the day's S&P 500 Form 4 open-market trades (codes **P**/**S**) → `output/<date>/filings.json` |
| **write** | `agents/write_agent.py` | yes | One 200-400 word brief per record → `output/<date>/articles/*.md` |
| **qa** | `agents/qa_agent.py` | yes | Fact-check each brief against its record → `output/<date>/qa.json` |
| **publish** | `agents/publish_agent.py` | no | Copy approved, non-duplicate briefs into `site/src/content/articles/` |
| weekly | `agents/weekly_agent.py` | no | Rank the week's biggest published trades → `site/src/content/weekly/*.md` (spec template 2). Own workflow: `weekly_summary.yml` (Sat cron) |
| social *(Phase 3)* | `agents/social_agent.py` | yes | Draft neutral X posts for the biggest trades |
| newsletter *(Phase 3)* | `agents/newsletter_agent.py` | yes | Draft the weekly Beehiiv digest |

Each stage reads the previous stage's file from `OUTPUT_DIR/<date>/`, so stages
can run independently or be re-run.

---

## Setup

```bash
py -m pip install -r requirements.txt      # Windows: use `py`; elsewhere `python`
cp .env.example .env                        # then edit .env
```

Required in `.env`:

- `ANTHROPIC_API_KEY` — for the write/QA agents.
- `SEC_USER_AGENT` — **must** be `"<app name> <your real email>"`. SEC returns
  403 without a real one.

Optional: `ANTHROPIC_MODEL` (default `claude-opus-5`; set `claude-sonnet-5` to
cut cost for high volume), `MIN_TOTAL_VALUE_USD` (default `100000` — skip small
trades), `SEC_REQUEST_DELAY_SEC`.

### S&P 500 list

`data/sp500_ciks.json` ships with ~45 megacaps so the pipeline runs immediately.
For the full list:

```bash
py data/build_sp500_ciks.py
```

---

## Running

```bash
# Whole pipeline for one date
py -m agents.orchestrator --date 2026-09-03

# Fast smoke test: a few tickers, cap articles, don't touch the site
py -m agents.orchestrator --date 2026-09-03 --tickers AAPL,MSFT,MA --limit 3 --dry-run-publish

# Individual stages
py -m agents.fetch_agent   --date 2026-09-03
py -m agents.write_agent   --date 2026-09-03
py -m agents.qa_agent      --date 2026-09-03
py -m agents.publish_agent --date 2026-09-03 --commit
```

`--strategy` (fetch / orchestrator):

- `submissions` *(default)* — reads each S&P 500 company's
  `data.sec.gov/submissions/CIK*.json`. ~500 requests/day, bounded, issuer known
  from the index.
- `daily-index` — the flow in spec §2: pull the day's `form.idx`, keep Form 4
  rows, fetch each to read its issuer CIK, match the S&P 500 list. Heavier
  (one request per Form 4 filed nationwide).

Tests:

```bash
py tests/test_form4_parser.py       # no pytest needed
```

---

## Phase mapping (spec §9)

- **Phase 1** — stages 1-4, run locally via `orchestrator.py`. ✅ implemented.
- **Phase 2** — `.github/workflows/daily_pipeline.yml` runs it daily after the US
  close, commits new articles, then builds `site/` and deploys it to GitHub
  Pages. See **Deployment** below.
- **Phase 3** — `social_agent.py` / `newsletter_agent.py` (drafts only).
- **Phase 4** — ads / paid tier: not started.

---

## Deployment (GitHub Pages + custom domain)

The site is a static Astro build hosted on **GitHub Pages** from the **project
repo** `nsvmm-dev/sec-edgar-insider-tracker`, served on the **custom apex domain
`decode-slang.com`**. Because it's a custom domain the site sits at the domain
root and `astro.config.mjs` needs no `base`.

> To move to a different domain later, update all three —
> `site/astro.config.mjs` (`site:`), `site/public/CNAME`,
> `site/public/robots.txt` (`Sitemap:` line) — then change it in *Settings →
> Pages* and update DNS.

One-time setup:

1. Push this repo to `nsvmm-dev/sec-edgar-insider-tracker` (**public** — free
   Pages + free Actions minutes). *(done)*
2. *Settings → Pages → Build and deployment → Source* = **GitHub Actions**.
3. *Settings → Pages → Custom domain* → `decode-slang.com`, save, then tick
   **Enforce HTTPS** once the cert is issued. (`site/public/CNAME` keeps the
   setting from being wiped on redeploy.)
4. DNS at the `decode-slang.com` provider — apex `A` records to GitHub Pages:
   `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`
   (optionally the matching `AAAA` records for IPv6). Add
   `CNAME www → nsvmm-dev.github.io` too so `www` redirects to the apex.
5. *Settings → Secrets and variables → Actions*:
   - Secrets: `ANTHROPIC_API_KEY`, `SEC_USER_AGENT`
   - Variables (optional): `ANTHROPIC_MODEL`, `MIN_TOTAL_VALUE_USD`

After that, every scheduled run (and every manual *Run workflow*) regenerates and
redeploys the site. `daily_pipeline.yml` builds the site in the same job that
runs the pipeline — it does **not** rely on the push triggering a second
workflow (a `GITHUB_TOKEN` push doesn't, by design).

The sitemap (`/sitemap.xml`) and RSS feed (`/rss.xml`) are hand-rolled endpoints
in `site/src/pages/`, not integrations, to avoid Astro-major-version coupling.
Article pages carry `NewsArticle` JSON-LD.

### Analytics (optional)

Cloudflare Web Analytics (cookieless, no consent banner). In the Cloudflare
dashboard: *decode-slang.com → Analytics & Logs → Web Analytics → Add a site*
(manual), copy the token from the JS snippet, and paste it into
`CF_ANALYTICS_TOKEN` in `site/src/consts.js`. The beacon only renders when that
value is non-empty. (Automatic injection needs the domain proxied, which it
isn't — the manual beacon works with DNS-only.)

---

## Deviations from the spec (and why)

1. **Archives host** — daily-index, full submissions and Form 4 XML are served
   from `www.sec.gov/Archives/...`, not `data.sec.gov` (which serves the JSON
   APIs). Both hosts are used accordingly.
2. **fetch & publish are plain code, not LLM agents** — Form 4 is structured XML
   and dedupe/copy is mechanical; deterministic code is more reliable, free, and
   auditable. The write and QA agents are the LLM agents.
3. **Default strategy `submissions`** — bounded request budget vs. fetching every
   Form 4 filed nationwide. `daily-index` implements the literal spec flow.
4. **`total_value`** — Form 4 XML has shares and price per share but not the
   product; the fetch layer computes `shares × price` (and a share-weighted
   average price when a filing has multiple lines). This is arithmetic on filed
   values, not the estimation the spec forbids. If any line lacks a price,
   `total_value` and `price_per_share` are `null`.
5. **MVP transaction scope** — only non-derivative codes **P** (purchase) and
   **S** (sale). Grants, gifts, tax withholding and option exercises are ignored
   for now. A filing with both purchases and sales yields two records.
6. **Disclaimer** — appended to every article by code (byte-exact), then still
   verified by the QA agent.

---

## Layout

```
agents/         pipeline (see table above) + config.py, sec_client.py,
                form4_parser.py, articles.py, llm.py
data/           sp500_ciks.json, build_sp500_ciks.py, published_index.json (ledger)
site/           Astro static site (see site/README.md)
tests/          parser tests + fixtures
output/         per-day working files (git-ignored)
.github/workflows/daily_pipeline.yml
```
