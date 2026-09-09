import { defineConfig } from "astro/config";

// Static output, deployed to GitHub Pages from the project repo
// "nsvmm-dev/sec-edgar-insider-tracker".
//
// A custom apex domain is used, so the site is served from the domain root and
// no `base` path is needed. `site/public/CNAME` pins the domain for the Pages
// deployment.
//
// To switch to a different domain later, update all three:
//   - `site` below
//   - site/public/CNAME
//   - site/public/robots.txt  (the Sitemap: line)
// ...then set the new domain in Settings -> Pages and update DNS.
//
// The build is produced and deployed by .github/workflows/daily_pipeline.yml
// after each daily run. The sitemap and RSS feed are hand-rolled endpoints
// (src/pages/sitemap.xml.js, src/pages/rss.xml.js), not integrations, to avoid
// coupling to a specific Astro major version.
export default defineConfig({
  site: "https://decode-slang.com",
  output: "static",
});
