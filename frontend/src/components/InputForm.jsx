import { useState } from "react";
import { Search, Sparkles } from "lucide-react";

const EXAMPLES = [
  "AI writing tool for legal professionals",
  "Freelance scheduling app",
  "Pet health tracker for seniors",
  "Remote team async standup tool",
  "Sustainable fashion marketplace",
];

export default function InputForm({ onSubmit, loading }) {
  const [value, setValue] = useState("");

  function handleSubmit(e) {
    e.preventDefault();
    const trimmed = value.trim();
    if (trimmed.length < 3) return;
    onSubmit(trimmed);
  }

  function handleExample(example) {
    setValue(example);
  }

  return (
    <div className="w-full max-w-2xl mx-auto">
      <form onSubmit={handleSubmit} className="relative">
        <div className="flex gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-[#71717A]" />
            <input
              type="text"
              value={value}
              onChange={(e) => setValue(e.target.value)}
              placeholder="Describe your niche idea..."
              className="input-field pl-12 pr-4 h-14 text-base"
              disabled={loading}
              minLength={3}
              maxLength={200}
              autoFocus
            />
          </div>
          <button
            type="submit"
            disabled={loading || value.trim().length < 3}
            className="btn-primary h-14 px-6 text-base whitespace-nowrap"
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                Analyzing
              </span>
            ) : (
              <span className="flex items-center gap-2">
                <Sparkles className="h-4 w-4" />
                Analyze
              </span>
            )}
          </button>
        </div>

        {value.length > 0 && (
          <p className="mt-2 text-right text-xs text-[#71717A]">
            {value.length}/200
          </p>
        )}
      </form>

      {/* Example chips */}
      {!loading && (
        <div className="mt-4 flex flex-wrap gap-2">
          <span className="text-xs text-[#71717A] self-center">Try:</span>
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              onClick={() => handleExample(ex)}
              className="rounded-full border border-[#1E1E24] bg-[#111113] px-3 py-1.5 text-xs text-[#71717A] transition-all hover:border-[#7C3AED] hover:text-[#F4F4F5]"
            >
              {ex}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
