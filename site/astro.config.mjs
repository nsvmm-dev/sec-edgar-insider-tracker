import { defineConfig } from "astro/config";

// Static output — deploys to Vercel's free tier as plain files.
export default defineConfig({
  site: "https://example.com",
  output: "static",
});
