import { useNavigate } from "react-router-dom";
import { ChevronRight, Trash2, Clock } from "lucide-react";
import { formatDate, truncate } from "../lib/utils";

export default function HistoryList({ briefs, onDelete, loading }) {
  const navigate = useNavigate();

  if (loading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="card animate-pulse">
            <div className="h-4 w-3/4 rounded bg-[#1E1E24]" />
            <div className="mt-2 h-3 w-1/2 rounded bg-[#1E1E24]" />
          </div>
        ))}
      </div>
    );
  }

  if (!briefs || briefs.length === 0) {
    return (
      <div className="card text-center py-12">
        <Clock className="h-10 w-10 text-[#1E1E24] mx-auto mb-3" />
        <p className="text-[#71717A]">No briefs saved yet.</p>
        <p className="text-sm text-[#71717A] mt-1">Analyze a niche to get started.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {briefs.map((brief) => (
        <div
          key={brief.id}
          className="card flex items-center justify-between gap-4 cursor-pointer hover:border-[#7C3AED]/50 transition-all group"
          onClick={() => navigate(`/brief/${brief.id}`)}
        >
          <div className="flex-1 min-w-0">
            <p className="font-medium text-[#F4F4F5] truncate">{brief.niche_input}</p>
            <div className="mt-1 flex items-center gap-3">
              <span className="text-xs text-[#71717A]">{formatDate(brief.created_at)}</span>
              {brief.ai_summary && (
                <span className="text-xs text-[#71717A] truncate hidden sm:block">
                  {truncate(
                    typeof brief.ai_summary === "string"
                      ? brief.ai_summary
                      : "View brief →",
                    80
                  )}
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2 flex-shrink-0">
            {brief.is_public && (
              <span className="rounded-full bg-[#10B981]/10 px-2 py-0.5 text-xs text-[#10B981]">
                Public
              </span>
            )}
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete(brief.id);
              }}
              className="p-1.5 rounded-lg text-[#71717A] hover:text-red-400 hover:bg-red-400/10 transition-all opacity-0 group-hover:opacity-100"
            >
              <Trash2 className="h-4 w-4" />
            </button>
            <ChevronRight className="h-5 w-5 text-[#71717A] group-hover:text-[#7C3AED] transition-all" />
          </div>
        </div>
      ))}
    </div>
  );
}
