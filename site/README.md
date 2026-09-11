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

Requires **Node.js >= 22.12.0** (Astro 7 hard-fails on older Node — `engines`
in `package.json`). All four GitHub Actions workflows that build the site pin
`node-version: "22"`.

- Articles are Markdown files in `src/content/articles/`, weekly round-ups in
  `src/content/weekly/`, both written by the agents. Collection schemas:
  `src/content.config.ts` (Astro 7 Content Layer API — `glob()` loaders,
  `entry.id`, `render(entry)`). There is **no `slug` front-matter field** —
  Astro reserves it; the slug is derived from the filename (`<slug>.md`).
- `src/pages/sitemap.xml.js` and `src/pages/rss.xml.js` are hand-rolled
  endpoints (`/sitemap.xml`, `/rss.xml`). `robots.txt` and `favicon.svg` are in
  `public/`.
- `astro.config.mjs` sets `site: https://decode-slang.com` (no `base` — served at
  the domain root). `public/CNAME` pins that domain for GitHub Pages. To switch
  domains later, see the root `README.md` for the three spots to change.
- The footer (`src/layouts/Base.astro`) carries the required "independent of the
  SEC / not investment advice" notice (spec section 8).
- Affiliate placement (brokerage sign-up links) belongs in the layout
  sidebar/footer, not the article bodies (spec section 8).

Affiliate slots are still follow-up work (spec §8: sidebar/footer only, never
the article body).
