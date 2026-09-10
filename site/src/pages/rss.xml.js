import rss from "@astrojs/rss";
import { getCollection } from "astro:content";
import { SITE_NAME, SITE_DESCRIPTION } from "../consts.js";
import { titleCaseCompany } from "../lib/format.js";

// RSS 2.0 feed at /rss.xml. `context.site` comes from `site` in astro.config.mjs.
export async function GET(context) {
  const articles = (await getCollection("articles")).sort(
    (a, b) => Date.parse(b.data.date) - Date.parse(a.data.date),
  );

  return rss({
    title: SITE_NAME,
    description: SITE_DESCRIPTION,
    site: context.site,
    items: articles.map((a) => {
      const filer = a.data.title?.includes(" (")
        ? a.data.title.split(" (")[0]
        : a.data.filer;
      return {
        title: a.data.title,
        link: `/articles/${a.slug}/`,
        pubDate: new Date(a.data.date),
        description: `${filer ?? ""} — ${titleCaseCompany(a.data.company) ?? ""} (${a.data.ticker ?? ""})`,
      };
    }),
  });
}
