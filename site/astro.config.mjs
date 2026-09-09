import { defineConfig } from "astro/config";

// Static output, deployed to GitHub Pages.
//
// The repo is the user site "Naka-SVMM.github.io", so the site is served from
// the domain root and no `base` path is required. The build is produced and
// deployed by .github/workflows/daily_pipeline.yml after each daily run.
//
// The sitemap and RSS feed are hand-rolled endpoints (src/pages/sitemap.xml.js,
// src/pages/rss.xml.js) rather than an integration, to avoid coupling to a
// specific Astro major version.
export default defineConfig({
  site: "https://naka-svmm.github.io",
  output: "static",
});
