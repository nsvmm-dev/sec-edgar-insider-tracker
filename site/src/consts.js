export const SITE_NAME = "EdgarHawk";
export const SITE_DESCRIPTION =
  "Plain-English news briefs on S&P 500 insider transactions (SEC Form 4).";

// Cloudflare Web Analytics beacon token. Cookieless, no consent banner needed.
// Get it from: Cloudflare dashboard -> decode-slang.com -> Analytics & Logs ->
// Web Analytics -> "Add a site" (Manual) -> copy the token from the JS snippet.
// The beacon only renders when this is non-empty.
export const CF_ANALYTICS_TOKEN = "94c4177511b64503b96ab6fbcdc53b6e";

// Google AdSense site-ownership verification (Settings -> Sites in AdSense).
// Site is pending review; this is verification only -- no ad-serving script
// yet. Once approved, decide ad placement (footer/sidebar, not mid-article)
// before adding the adsbygoogle.js loader / auto ads.
export const ADSENSE_PUBLISHER_ID = "ca-pub-9133327305052109";
