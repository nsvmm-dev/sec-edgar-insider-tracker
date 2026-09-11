import rss from "@astrojs/rss";
import { getCollection } from "astro:content";
import { SITE_NAME, SITE_DESCRIPTION } from "../consts.js";
import { titleCaseCompany, filerFromTitle } from "../lib/format.js";

// RSS 2.0 feed at /rss.xml. `context.site` comes from `site` in astro.config.mjs.
export async function GET(context) {
  const [articles, weekly] = await Promise.all([
    getCollection("articles"),
    getCollection("weekly"),
  ]);

  const items = [
    ...articles.map((a) => {
      const filer = filerFromTitle(a.data.title, a.data.filer);
      return {
        title: a.data.title,
        link: `/articles/${a.id}/`,
        pubDate: new Date(a.data.date),
        description: `${filer ?? ""} — ${titleCaseCompany(a.data.company) ?? ""} (${a.data.ticker ?? ""})`,
      };
    }),
    ...weekly.map((w) => ({
      title: w.data.title,
      link: `/weekly/${w.id}/`,
      pubDate: new Date(w.data.generated ?? w.data.week_end),
      description: `Weekly round-up: the biggest S&P 500 insider trades, ${w.data.week_start} to ${w.data.week_end}.`,
    })),
  ].sort((a, b) => b.pubDate - a.pubDate);

  return rss({
    title: SITE_NAME,
    description: SITE_DESCRIPTION,
    site: context.site,
    items,
  });
}
