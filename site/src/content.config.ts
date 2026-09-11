import { defineCollection } from "astro:content";
import { z } from "astro/zod";
import { glob } from "astro/loaders";

// Matches the front matter written by agents/write_agent.py.
const articles = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/articles" }),
  schema: z.object({
    title: z.string(),
    date: z.string(), // YYYY-MM-DD (transaction date)
    company: z.string().nullable().optional(),
    ticker: z.string().nullable().optional(),
    filer: z.string().nullable().optional(),
    filer_title: z.string().nullable().optional(),
    transaction_type: z.enum(["purchase", "sale"]).nullable().optional(),
    shares: z.number().nullable().optional(),
    price_per_share: z.number().nullable().optional(),
    total_value: z.number().nullable().optional(),
    source_url: z.string().url(),
    template: z.string().optional(),
    generated_by: z.string().optional(),
  }),
});

// Weekly Top-N round-up, written by agents/weekly_agent.py.
const weekly = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/weekly" }),
  schema: z.object({
    title: z.string(),
    week_start: z.string(),
    week_end: z.string(),
    count: z.number().optional(),
    generated: z.string().optional(),
  }),
});

export const collections = { articles, weekly };
