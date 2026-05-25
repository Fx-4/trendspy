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
