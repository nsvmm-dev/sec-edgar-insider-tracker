import { getCollection } from "astro:content";

// Plain sitemap at /sitemap.xml. `context.site` comes from astro.config.mjs.
const STATIC_PATHS = [
  "/",
  "/about/",
  "/disclosure/",
  "/privacy/",
  "/terms/",
  "/contact/",
];

export async function GET(context) {
  const base = context.site.href.replace(/\/$/, "");
  const articles = await getCollection("articles");

  const entries = [
    ...STATIC_PATHS.map((p) => ({ loc: `${base}${p}` })),
    ...articles.map((a) => ({
      loc: `${base}/articles/${a.slug}/`,
      lastmod: a.data.date,
    })),
  ];

  const body = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${entries
  .map(
    (e) =>
      `  <url><loc>${e.loc}</loc>${e.lastmod ? `<lastmod>${e.lastmod}</lastmod>` : ""}</url>`,
  )
  .join("\n")}
</urlset>
`;

  return new Response(body, {
    headers: { "Content-Type": "application/xml" },
  });
}
