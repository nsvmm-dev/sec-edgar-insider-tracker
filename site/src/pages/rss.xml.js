import rss from "@astrojs/rss";
import { getCollection } from "astro:content";

// RSS 2.0 feed at /rss.xml. `context.site` comes from `site` in astro.config.mjs.
export async function GET(context) {
  const articles = (await getCollection("articles")).sort(
    (a, b) => Date.parse(b.data.date) - Date.parse(a.data.date),
  );

  return rss({
    title: "Insider Trades",
    description:
      "Plain-English news briefs on S&P 500 insider transactions (SEC Form 4).",
    site: context.site,
    items: articles.map((a) => ({
      title: a.data.title,
      link: `/articles/${a.slug}/`,
      pubDate: new Date(a.data.date),
      description: `${a.data.filer ?? ""} — ${a.data.company ?? ""} (${a.data.ticker ?? ""})`,
    })),
  });
}
