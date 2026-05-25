import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { LogIn, LogOut, LayoutDashboard, Zap, Shield, Clock } from "lucide-react";
import { supabase } from "../lib/supabase";
import { streamAnalysis, saveBrief } from "../lib/api";
import { sanitizeBrief } from "../lib/utils";
import InputForm from "../components/InputForm";
import LoadingState from "../components/LoadingState";
import MarketBriefCard from "../components/MarketBriefCard";

export default function Home({ session }) {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [statusMessages, setStatusMessages] = useState([]);
  const [brief, setBrief] = useState(null);
  const [nicheInput, setNicheInput] = useState("");
  const [error, setError] = useState(null);
  const [isSaving, setIsSaving] = useState(false);
  const [savedId, setSavedId] = useState(null);
  const [shareUrl, setShareUrl] = useState(null);
  const [abortFn, setAbortFn] = useState(null);
  const [isCached, setIsCached] = useState(false);
  const [cachedAt, setCachedAt] = useState(null);

  async function handleAnalyze(niche, force = false) {
    setLoading(true);
    setError(null);
    setBrief(null);
    setStatusMessages([]);
    setNicheInput(niche);
    setSavedId(null);
    setShareUrl(null);
    setIsCached(false);
    setCachedAt(null);

    const sections = {};

    const abort = streamAnalysis(niche, {
      onStatus(data) {
        setStatusMessages((prev) => [...prev, data]);
      },
      onResult({ section, data }) {
        sections[section] = data;
        setBrief(sanitizeBrief({ ...sections, niche_input: niche }));
      },
      onCached(data) {
        setBrief(sanitizeBrief({ ...data, niche_input: niche }));
        setIsCached(true);
      },
      onDone(data) {
        setLoading(false);
        if (data?.cached && data?.cached_at) {
          setCachedAt(data.cached_at);
        }
      },
      onError(data) {
        setError(data.message || "Analysis failed. Please try again.");
        setLoading(false);
      },
    }, force);

    setAbortFn(() => abort);
  }

  function handleReanalyze() {
    handleAnalyze(nicheInput, true);
  }

  function handleStop() {
    abortFn?.();
    setLoading(false);
  }

  async function handleSave() {
    if (!session || !brief) return;
    setIsSaving(true);
    try {
      const token = session.access_token;
      const saved = await saveBrief(token, nicheInput, brief);
      setSavedId(saved.id);
    } catch (e) {
      setError("Failed to save brief. Please try again.");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleSignIn() {
    if (!supabase) return;
    await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: window.location.origin },
    });
  }

  async function handleSignOut() {
    if (!supabase) return;
    await supabase.auth.signOut();
    setBrief(null);
    setNicheInput("");
  }

  return (
    <div className="min-h-screen bg-[#0A0A0B]">
      {/* Nav */}
      <nav className="border-b border-[#1E1E24] px-6 py-4">
        <div className="mx-auto flex max-w-5xl items-center justify-between">
          <div className="flex items-center gap-2">
            <Zap className="h-5 w-5 text-[#7C3AED]" />
            <span className="font-bold text-[#F4F4F5]">TrendSpy</span>
          </div>
          <div className="flex items-center gap-3">
            {session ? (
              <>
                <button
                  onClick={() => navigate("/dashboard")}
                  className="btn-secondary text-sm"
                >
                  <LayoutDashboard className="h-4 w-4" />
                  Dashboard
                </button>
                <button onClick={handleSignOut} className="btn-secondary text-sm">
                  <LogOut className="h-4 w-4" />
                  Sign out
                </button>
              </>
            ) : (
              <button onClick={handleSignIn} className="btn-secondary text-sm">
                <LogIn className="h-4 w-4" />
                Sign in
              </button>
            )}
          </div>
        </div>
      </nav>

      {/* Hero */}
      {!brief && !loading && (
        <div className="mx-auto max-w-5xl px-6 pt-20 pb-12 text-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-[#7C3AED]/30 bg-[#7C3AED]/10 px-4 py-1.5 text-sm text-[#7C3AED] mb-6">
            <Zap className="h-3.5 w-3.5" />
            AI-powered market intelligence
          </div>
          <h1 className="text-4xl font-bold text-[#F4F4F5] sm:text-5xl leading-tight">
            Market research that used to{" "}
            <span className="text-[#7C3AED]">take 2 weeks</span>
            <br />
            now takes{" "}
            <span className="text-[#10B981]">2 minutes</span>
          </h1>
          <p className="mt-5 text-lg text-[#71717A] max-w-xl mx-auto">
            Enter any niche. Get real pain points from Reddit, competitor gaps,
            pricing signals, and hot communities — powered by AI.
          </p>

          <div className="mt-10">
            <InputForm onSubmit={handleAnalyze} loading={loading} />
          </div>

          {/* Features */}
          <div className="mt-16 grid grid-cols-1 sm:grid-cols-3 gap-4 text-left">
            {[
              { icon: Zap, title: "Real-time streaming", desc: "Watch results appear live as AI analyzes Reddit, Tavily, and Exa simultaneously" },
              { icon: Shield, title: "100% free stack", desc: "Reddit JSON API + Tavily + Exa + Groq — no hidden costs, all genuinely free tiers" },
              { icon: Clock, title: "Save & share", desc: "Save any brief to your account and share a public link with your team" },
            ].map((f) => (
              <div key={f.title} className="card">
                <f.icon className="h-5 w-5 text-[#7C3AED] mb-3" />
                <h3 className="font-semibold text-[#F4F4F5] mb-1">{f.title}</h3>
                <p className="text-sm text-[#71717A]">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="mx-auto max-w-5xl px-6 pt-16 pb-12 flex flex-col items-center gap-6">
          <LoadingState statusMessages={statusMessages} />
          <button onClick={handleStop} className="btn-secondary text-sm">
            Cancel
          </button>
        </div>
      )}

      {/* Error */}
      {error && !loading && (
        <div className="mx-auto max-w-xl px-6 pt-8">
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-400">
            {error}
          </div>
          <div className="mt-6">
            <InputForm onSubmit={handleAnalyze} loading={false} />
          </div>
        </div>
      )}

      {/* Result */}
      {brief && !loading && (
        <div className="mx-auto max-w-5xl px-6 pt-8 pb-16 space-y-6">
          {/* Back button */}
          <div className="flex justify-center">
            <button
              onClick={() => { setBrief(null); setError(null); }}
              className="btn-secondary"
            >
              ← Analyze another niche
            </button>
          </div>

          <MarketBriefCard
            brief={{ ...brief, id: savedId }}
            isCached={isCached}
            cachedAt={cachedAt}
            onReanalyze={handleReanalyze}
            session={session}
            onSave={handleSave}
            isSaving={isSaving}
            shareUrl={shareUrl}
          />
        </div>
      )}
    </div>
  );
}
