import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, Zap, LogOut } from "lucide-react";
import { supabase } from "../lib/supabase";
import { listBriefs, deleteBrief } from "../lib/api";
import HistoryList from "../components/HistoryList";

export default function Dashboard({ session }) {
  const navigate = useNavigate();
  const [briefs, setBriefs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchBriefs();
  }, [session]);

  async function fetchBriefs() {
    setLoading(true);
    setError(null);
    try {
      const data = await listBriefs(session.access_token);
      setBriefs(data);
    } catch (e) {
      setError("Failed to load briefs.");
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(id) {
    if (!confirm("Delete this brief?")) return;
    try {
      await deleteBrief(session.access_token, id);
      setBriefs((prev) => prev.filter((b) => b.id !== id));
    } catch {
      setError("Failed to delete brief.");
    }
  }

  async function handleSignOut() {
    if (supabase) await supabase.auth.signOut();
    navigate("/");
  }

  return (
    <div className="min-h-screen bg-[#0A0A0B]">
      {/* Nav */}
      <nav className="border-b border-[#1E1E24] px-6 py-4">
        <div className="mx-auto flex max-w-4xl items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate("/")}
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
          <button onClick={handleSignOut} className="btn-secondary text-sm">
            <LogOut className="h-4 w-4" />
            Sign out
          </button>
        </div>
      </nav>

      <div className="mx-auto max-w-4xl px-6 py-10">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-[#F4F4F5]">Your Briefs</h1>
            <p className="mt-1 text-sm text-[#71717A]">
              {session.user?.email} · {briefs.length} saved brief{briefs.length !== 1 ? "s" : ""}
            </p>
          </div>
          <button onClick={() => navigate("/")} className="btn-primary">
            <Zap className="h-4 w-4" />
            New Analysis
          </button>
        </div>

        {error && (
          <div className="mb-6 rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-400">
            {error}
          </div>
        )}

        <HistoryList
          briefs={briefs}
          onDelete={handleDelete}
          loading={loading}
        />
      </div>
    </div>
  );
}
