# Site (Astro, static)

Minimal static site that renders the articles produced by the agent pipeline.

```bash
cd site
npm install
npm run dev      # local preview
npm run build    # -> site/dist/ (deploy target for Vercel free tier)
```

- Articles are Markdown files in `src/content/articles/`, written by
  `agents/publish_agent.py`. Front-matter schema: `src/content/config.ts`.
- The footer (`src/layouts/Base.astro`) carries the required "independent of the
  SEC / not investment advice" notice (spec section 8).
- Affiliate placement (brokerage sign-up links) belongs in the layout
  sidebar/footer, not the article bodies (spec section 8).

This scaffold is intentionally bare — styling, SEO, feeds, the weekly-summary
template and affiliate slots are Phase 2+ work.
