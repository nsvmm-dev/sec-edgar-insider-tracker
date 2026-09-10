// Display helpers for the site templates. Purely cosmetic — the pipeline keeps
// the verbatim filed values; this only affects how they are shown.

const KEEP_UPPER = new Set([
  "NVIDIA", "IBM", "AMD", "HP", "UPS", "PNC", "KKR", "MSCI", "ADP", "CDW", "DXC",
  "AON", "EOG", "PPG", "MMM", "AES", "APA", "CME", "ICE", "FMC", "BXP", "WEC",
  "DTE", "AEP", "CMS", "NRG", "EQT", "HES", "LKQ", "GEHC", "AT&T", "USA", "US",
  "AI", "TV", "IT",
]);

const WORD_MAP = {
  CORP: "Corp", "CORP.": "Corp.", CORPORATION: "Corporation",
  INC: "Inc", "INC.": "Inc.", CO: "Co", "CO.": "Co.",
  LTD: "Ltd", "LTD.": "Ltd.", PLC: "plc", LLC: "LLC", LP: "LP",
  HOLDINGS: "Holdings", HOLDING: "Holding", GROUP: "Group",
  COMPANIES: "Companies", COMPANY: "Company", INTERNATIONAL: "International",
  TECHNOLOGIES: "Technologies", TECHNOLOGY: "Technology", SYSTEMS: "Systems",
  THE: "the", AND: "and", OF: "of",
};

/**
 * Title-case an ALL-CAPS company name from EDGAR (e.g. "ZIMMER BIOMET HOLDINGS"
 * -> "Zimmer Biomet Holdings"). Names that already have lower-case letters are
 * returned unchanged.
 */
export function titleCaseCompany(name) {
  if (!name || name !== name.toUpperCase()) return name;
  return name
    .split(/\s+/)
    .map((w, i) => {
      if (KEEP_UPPER.has(w)) return w;
      if (WORD_MAP[w]) return i === 0 ? cap(WORD_MAP[w]) : WORD_MAP[w];
      if (/^[0-9]+$/.test(w)) return w;
      if (/^[A-Z]&[A-Z]$/.test(w)) return w; // S&P, AT&T style
      return cap(w);
    })
    .join(" ");
}

function cap(w) {
  return w.charAt(0).toUpperCase() + w.slice(1).toLowerCase();
}

const ACTOR_RE =
  /^(.*?)(?:\s+\([^)]*\))?\s+(?:Buys?|Sells?|Bought|Sold|Purchases?|Acquires?)\b/i;

/**
 * Pull the person/entity name from a "<Name> (<role>) Sells ..." headline.
 * Falls back to `fallback` (the raw EDGAR filer field) when it doesn't match.
 */
export function filerFromTitle(title, fallback) {
  const m = ACTOR_RE.exec(title || "");
  return (m && m[1].trim()) || fallback;
}
