# Site (Astro, static)

Minimal static site that renders the articles produced by the agent pipeline.
Deployed to **GitHub Pages** by `.github/workflows/daily_pipeline.yml` (see the
root `README.md` → *Deployment*).

```bash
cd site
npm ci           # uses package-lock.json (npm install to update it)
npm run dev      # local preview
npm run build    # -> site/dist/ (uploaded to Pages by the workflow)
```

- Articles are Markdown files in `src/content/articles/`, written by
  `agents/publish_agent.py`. Front-matter schema: `src/content/config.ts`.
  There is **no `slug` front-matter field** — Astro reserves it; the slug is
  derived from the filename (`<slug>.md`).
- `src/pages/sitemap.xml.js` and `src/pages/rss.xml.js` are hand-rolled
  endpoints (`/sitemap.xml`, `/rss.xml`). `robots.txt` and `favicon.svg` are in
  `public/`.
- `astro.config.mjs` sets `site` to the custom apex domain (no `base` — served
  at the domain root). `public/CNAME` pins that domain for GitHub Pages. The
  domain is currently the placeholder `example.com`; see the root `README.md`
  for the three spots to update once it's chosen.
- The footer (`src/layouts/Base.astro`) carries the required "independent of the
  SEC / not investment advice" notice (spec section 8).
- Affiliate placement (brokerage sign-up links) belongs in the layout
  sidebar/footer, not the article bodies (spec section 8).

Still bare: visual styling, the weekly-summary template, and affiliate slots are
follow-up work.
