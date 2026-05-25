import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/** Merge Tailwind classes safely */
export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

/** Format a date to human-readable string */
export function formatDate(iso) {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

/** Truncate text to a given length */
export function truncate(str, maxLen = 100) {
  if (!str || str.length <= maxLen) return str;
  return str.slice(0, maxLen).trimEnd() + "…";
}

/** Copy text to clipboard, returns success boolean */
export async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}

/** Convert section key to display label */
export const SECTION_LABELS = {
  pain_points: "Pain Points",
  competitor_gaps: "Competitor Gaps",
  pricing_signals: "Pricing Signals",
  hot_communities: "Hot Communities",
  ai_summary: "AI Summary",
};

/** Activity level to color */
export function activityColor(activity) {
  switch (activity) {
    case "high": return "text-[#10B981] bg-[#10B981]/10";
    case "medium": return "text-yellow-400 bg-yellow-400/10";
    case "low": return "text-[#71717A] bg-[#71717A]/10";
    default: return "text-[#71717A] bg-[#71717A]/10";
  }
}

// ─── Brief Sanitizer ─────────────────────────────────────────────────────────
// Runs client-side on every result so hallucinated data never reaches the UI,
// regardless of backend model behavior.

const _VALID_SOURCES = new Set(["Tavily", "Exa", "Hacker News", "Reddit"]);

const _KNOWN_PLATFORMS = new Set([
  "hacker news", "news.ycombinator.com", "product hunt",
  "indie hackers", "indiehackers.com", "dev.to",
]);

const _FAKE_FRAGMENTS = [
  "startuptribunal", "usereviews", "productivityapps", "saasreviews",
  "freelanceforum", "upworkcommunity", "fiverrforum", "fiverr forum",
  "stackoverflowsfreelancing", "stack overflow", "freelancersunion",
  "toolreviews", "appreviews", "startupwatch", "startupinsights",
];

/**
 * Sanitize a brief object returned from the API.
 * Filters fake communities, removes "key insight X" pricing placeholders,
 * and normalizes source labels on pain points.
 */
export function sanitizeBrief(brief) {
  if (!brief || typeof brief !== "object") return brief;
  const result = { ...brief };

  // 1. Pain points — fix hallucinated source labels
  if (Array.isArray(result.pain_points)) {
    result.pain_points = result.pain_points.map((p) => ({
      ...p,
      source: _VALID_SOURCES.has(p.source) ? p.source : "Web",
    }));
  }

  // 2. Hot communities — only allow exact r/name or known platforms
  if (Array.isArray(result.hot_communities)) {
    const valid = result.hot_communities.filter((c) => {
      const name = (c.name || "").trim();
      const lower = name.toLowerCase().replace(/[\s']/g, "");
      const isFake = _FAKE_FRAGMENTS.some((f) => lower.includes(f.replace(/[\s']/g, "")));
      if (isFake) return false;
      const isCleanSub = /^r\/[A-Za-z0-9_]{2,25}$/.test(name);
      const isKnown = _KNOWN_PLATFORMS.has(name.toLowerCase());
      return isCleanSub || isKnown;
    });

    // Always ensure at least 3 communities. Fill gaps with reliable defaults.
    const defaults = [
      { name: "r/entrepreneur", members: "3.5M", activity: "high" },
      { name: "r/SaaS", members: "200K+", activity: "high" },
      { name: "Hacker News", members: "400K+", activity: "high" },
      { name: "r/startups", members: "600K+", activity: "high" },
    ];
    const existingNames = new Set(valid.map((c) => c.name.toLowerCase()));
    for (const def of defaults) {
      if (valid.length >= 4) break;
      if (!existingNames.has(def.name.toLowerCase())) {
        valid.push(def);
        existingNames.add(def.name.toLowerCase());
      }
    }

    result.hot_communities = valid.slice(0, 5);
  }

  // 3. Pricing insights — remove "key insight X:" placeholder lines
  if (result.pricing_signals && typeof result.pricing_signals === "object") {
    const insights = result.pricing_signals.insights;
    if (Array.isArray(insights)) {
      const real = insights.filter(
        (i) => i && !/^key\s+insight/i.test(i.trim()) && i.trim().length > 20
      );
      result.pricing_signals = {
        ...result.pricing_signals,
        insights:
          real.length > 0
            ? real
            : [
                "Pricing varies by plan — most competitors offer free + paid tiers",
                "Free plan availability is a strong differentiator in this niche",
              ],
      };
    }
  }

  return result;
}
