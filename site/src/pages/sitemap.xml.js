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

  const urls = [
    ...STATIC_PATHS.map((p) => `${base}${p}`),
    ...articles.map((a) => `${base}/articles/${a.slug}/`),
  ];

  const body = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls.map((u) => `  <url><loc>${u}</loc></url>`).join("\n")}
</urlset>
`;

  return new Response(body, {
    headers: { "Content-Type": "application/xml" },
  });
}
