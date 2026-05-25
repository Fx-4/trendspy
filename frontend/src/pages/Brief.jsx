import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Zap } from "lucide-react";
import { getBrief, shareBrief, deleteBrief } from "../lib/api";
import MarketBriefCard from "../components/MarketBriefCard";

export default function Brief({ session }) {
  const { id } = useParams();
  const navigate = useNavigate();
  const [brief, setBrief] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [shareUrl, setShareUrl] = useState(null);

  useEffect(() => {
    fetchBrief();
  }, [id]);

  async function fetchBrief() {
    setLoading(true);
    try {
      const token = session?.access_token ?? null;
      const data = await getBrief(id, token);
      setBrief(data);
      if (data.share_slug) {
        setShareUrl(`${window.location.origin}/share/${data.share_slug}`);
      }
    } catch (e) {
      setError("Brief not found or access denied.");
    } finally {
      setLoading(false);
    }
  }

  async function handleShare() {
    if (!session || !brief) return;
    try {
      const result = await shareBrief(session.access_token, id);
      const url = `${window.location.origin}${result.share_url}`;
      setShareUrl(url);
      setBrief((prev) => ({ ...prev, is_public: true, share_slug: result.share_slug }));
    } catch {
      setError("Failed to generate share link.");
    }
  }

  async function handleDelete() {
    if (!session || !brief) return;
    if (!confirm("Delete this brief permanently?")) return;
    try {
      await deleteBrief(session.access_token, id);
      navigate("/dashboard");
    } catch {
      setError("Failed to delete brief.");
    }
  }

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
        <div className="mx-auto flex max-w-4xl items-center gap-3">
          <button
            onClick={() => navigate(session ? "/dashboard" : "/")}
            className="btn-secondary text-sm"
          >
            <ArrowLeft className="h-4 w-4" />
            Back
          </button>
          <div className="flex items-center gap-2">
            <Zap className="h-5 w-5 text-[#7C3AED]" />
            <span className="font-bold text-[#F4F4F5]">TrendSpy</span>
          </div>
        </div>
      </nav>

      <div className="mx-auto max-w-4xl px-6 py-10">
        {error && (
          <div className="mb-6 rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-400">
            {error}
          </div>
        )}
        {brief && (
          <MarketBriefCard
            brief={brief}
            session={session}
            onShare={handleShare}
            onDelete={handleDelete}
            shareUrl={shareUrl}
          />
        )}
      </div>
    </div>
  );
}
