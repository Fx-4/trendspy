import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Zap, ExternalLink } from "lucide-react";
import { getBriefBySlug } from "../lib/api";
import MarketBriefCard from "../components/MarketBriefCard";

export default function SharedBrief() {
  const { slug } = useParams();
  const navigate = useNavigate();
  const [brief, setBrief] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const data = await getBriefBySlug(slug);
        setBrief(data);
      } catch {
        setError("This brief doesn't exist or is no longer public.");
      } finally {
        setLoading(false);
      }
    })();
  }, [slug]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#0A0A0B]">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-[#7C3AED] border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0A0A0B]">
      <nav className="border-b border-[#1E1E24] px-6 py-4">
        <div className="mx-auto flex max-w-4xl items-center justify-between">
          <div className="flex items-center gap-2">
            <Zap className="h-5 w-5 text-[#7C3AED]" />
            <span className="font-bold text-[#F4F4F5]">TrendSpy</span>
          </div>
          <button
            onClick={() => navigate("/")}
            className="btn-secondary text-sm"
          >
            <ExternalLink className="h-4 w-4" />
            Try TrendSpy free
          </button>
        </div>
      </nav>

      <div className="mx-auto max-w-4xl px-6 py-10">
        {/* Shared badge */}
        <div className="mb-6 flex items-center gap-2 text-sm text-[#71717A]">
          <span className="rounded-full bg-[#10B981]/10 px-3 py-1 text-xs text-[#10B981]">
            Public brief
          </span>
          <span>Shared via TrendSpy</span>
        </div>

        {error && (
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-6 text-center text-sm text-red-400">
            {error}
          </div>
        )}

        {brief && (
          <MarketBriefCard
            brief={brief}
            session={null}
            shareUrl={window.location.href}
          />
        )}

        {/* CTA */}
        <div className="mt-10 card text-center">
          <h3 className="font-semibold text-[#F4F4F5] mb-2">
            Want your own market intelligence brief?
          </h3>
          <p className="text-sm text-[#71717A] mb-4">
            TrendSpy analyzes Reddit, web sources, and AI to find pain points and opportunities in any niche — in under 40 seconds.
          </p>
          <button onClick={() => navigate("/")} className="btn-primary mx-auto">
            <Zap className="h-4 w-4" />
            Try TrendSpy free
          </button>
        </div>
      </div>
    </div>
  );
}
