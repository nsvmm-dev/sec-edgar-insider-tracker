import { defineCollection, z } from "astro:content";

// Matches the front matter written by agents/write_agent.py.
const articles = defineCollection({
  type: "content",
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

export const collections = { articles };
