import { useState } from "react";
import { Copy, Check, Share2, Bookmark, Trash2, ExternalLink } from "lucide-react";
import { copyToClipboard, activityColor, formatDate } from "../lib/utils";

function PainPointsSection({ data }) {
  if (!Array.isArray(data)) return null;
  return (
    <div className="space-y-3">
      {data.map((item, i) => (
        <div key={i} className="flex items-start gap-3 rounded-lg bg-[#0A0A0B] p-3">
          <span className="flex-shrink-0 flex h-6 w-6 items-center justify-center rounded-full bg-red-500/10 text-xs font-bold text-red-400">
            {i + 1}
          </span>
          <div className="flex-1 min-w-0">
            <p className="text-sm text-[#F4F4F5]">{item.text}</p>
            <div className="mt-1 flex items-center gap-2">
              {item.frequency && (
                <span className="text-xs text-[#71717A]">~{item.frequency} mentions</span>
              )}
              {item.source && (
                <span className="rounded-full bg-[#1E1E24] px-2 py-0.5 text-xs text-[#71717A]">
                  {item.source}
                </span>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function CompetitorGapsSection({ data }) {
  if (!Array.isArray(data)) return null;
  return (
    <div className="space-y-3">
      {data.map((item, i) => (
        <div key={i} className="rounded-lg border border-[#1E1E24] p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="font-medium text-[#F4F4F5]">{item.competitor}</span>
            <span className="text-xs text-[#71717A] bg-[#1E1E24] px-2 py-0.5 rounded-full">
              competitor
            </span>
          </div>
          <p className="text-sm text-[#71717A] mb-2">❌ {item.gap}</p>
          <p className="text-sm text-[#10B981]">✓ {item.opportunity}</p>
        </div>
      ))}
    </div>
  );
}

function PricingSection({ data }) {
  if (!data || typeof data !== "object") return null;
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        {data.competitor_range && (
          <div className="rounded-lg bg-[#0A0A0B] p-4">
            <p className="text-xs text-[#71717A] mb-1">Competitor Pricing</p>
            <p className="text-xl font-bold text-[#F4F4F5]">{data.competitor_range}</p>
          </div>
        )}
        {data.willingness_to_pay && (
          <div className="rounded-lg bg-[#10B981]/5 border border-[#10B981]/20 p-4">
            <p className="text-xs text-[#71717A] mb-1">Users Will Pay</p>
            <p className="text-xl font-bold text-[#10B981]">{data.willingness_to_pay}</p>
          </div>
        )}
      </div>
      {data.insights && Array.isArray(data.insights) && data.insights.length > 0 && (
        <ul className="space-y-2">
          {data.insights.map((insight, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-[#71717A]">
              <span className="text-[#7C3AED] flex-shrink-0">•</span>
              {insight}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function CommunitiesSection({ data }) {
  if (!Array.isArray(data)) return null;
  return (
    <div className="space-y-3">
      {data.map((item, i) => (
        <div key={i} className="flex items-center justify-between rounded-lg bg-[#0A0A0B] p-3">
          <div>
            <p className="text-sm font-medium text-[#F4F4F5]">{item.name}</p>
            {item.members && (
              <p className="text-xs text-[#71717A]">{item.members} members</p>
            )}
          </div>
          {item.activity && (
            <span className={`section-tag ${activityColor(item.activity)}`}>
              {item.activity}
            </span>
          )}
        </div>
      ))}
    </div>
  );
}

function AISummarySection({ data }) {
  if (!data) return null;
  const text = typeof data === "string" ? data : JSON.stringify(data);
  return (
    <div className="rounded-lg bg-[#7C3AED]/5 border border-[#7C3AED]/20 p-4">
      <p className="text-sm leading-relaxed text-[#F4F4F5]">{text}</p>
    </div>
  );
}

const SECTIONS = [
  { key: "pain_points", emoji: "🔥", label: "Top Pain Points", Component: PainPointsSection },
  { key: "competitor_gaps", emoji: "🕳️", label: "Competitor Gaps", Component: CompetitorGapsSection },
  { key: "pricing_signals", emoji: "💰", label: "Pricing Signals", Component: PricingSection },
  { key: "hot_communities", emoji: "🗺️", label: "Hot Communities", Component: CommunitiesSection },
  { key: "ai_summary", emoji: "🧠", label: "AI Summary", Component: AISummarySection },
];

export default function MarketBriefCard({
  brief,
  session,
  onSave,
  onShare,
  onDelete,
  isSaving,
  shareUrl,
}) {
  const [copied, setCopied] = useState(false);
  const [activeSection, setActiveSection] = useState(null);

  async function handleCopyShare() {
    const url = shareUrl || window.location.href;
    const ok = await copyToClipboard(url);
    if (ok) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }

  const sections = SECTIONS.filter((s) => brief[s.key] !== undefined);

  return (
    <div className="w-full max-w-3xl mx-auto animate-slide-up space-y-4">
      {/* Header */}
      <div className="card">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold text-[#F4F4F5]">
              Market Intelligence Brief
            </h2>
            {brief.niche_input && (
              <p className="mt-1 text-sm text-[#71717A]">
                Niche: <span className="text-[#7C3AED]">{brief.niche_input}</span>
              </p>
            )}
            {brief.created_at && (
              <p className="text-xs text-[#71717A] mt-0.5">{formatDate(brief.created_at)}</p>
            )}
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-2 flex-shrink-0">
            {session && !brief.id && (
              <button
                onClick={onSave}
                disabled={isSaving}
                className="btn-secondary"
              >
                <Bookmark className="h-4 w-4" />
                {isSaving ? "Saving…" : "Save"}
              </button>
            )}
            {brief.id && onShare && (
              <button onClick={onShare} className="btn-secondary">
                <Share2 className="h-4 w-4" />
                Share
              </button>
            )}
            {shareUrl && (
              <button onClick={handleCopyShare} className="btn-secondary">
                {copied ? (
                  <Check className="h-4 w-4 text-[#10B981]" />
                ) : (
                  <Copy className="h-4 w-4" />
                )}
                {copied ? "Copied!" : "Copy link"}
              </button>
            )}
            {brief.id && onDelete && (
              <button
                onClick={() => onDelete(brief.id)}
                className="btn-secondary text-red-400 hover:border-red-400"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>

        {/* Section nav tabs */}
        <div className="mt-4 flex flex-wrap gap-2 border-t border-[#1E1E24] pt-4">
          {sections.map((s) => (
            <button
              key={s.key}
              onClick={() => setActiveSection(activeSection === s.key ? null : s.key)}
              className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-all ${
                activeSection === s.key || activeSection === null
                  ? "bg-[#7C3AED]/10 text-[#7C3AED]"
                  : "text-[#71717A] hover:text-[#F4F4F5]"
              }`}
            >
              {s.emoji} {s.label}
            </button>
          ))}
        </div>
      </div>

      {/* Sections */}
      {sections.map((s) => {
        if (activeSection && activeSection !== s.key) return null;
        return (
          <div key={s.key} className="card animate-fade-in">
            <h3 className="text-base font-semibold text-[#F4F4F5] mb-4">
              {s.emoji} {s.label}
            </h3>
            <s.Component data={brief[s.key]} />
          </div>
        );
      })}
    </div>
  );
}
