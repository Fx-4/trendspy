/**
 * TrendSpy API client
 * Handles SSE streaming from FastAPI backend
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

/**
 * Stream market analysis via SSE
 * @param {string} nicheInput - The niche to analyze
 * @param {object} callbacks - Event handlers
 * @param {function} callbacks.onStatus - Called with status messages {message, step, total, done}
 * @param {function} callbacks.onResult - Called with each section {section, data}
 * @param {function} callbacks.onCached - Called if result comes from cache
 * @param {function} callbacks.onDone - Called when analysis completes {duration_seconds, cached}
 * @param {function} callbacks.onError - Called on error {message, code}
 * @returns {function} abort function to cancel the stream
 */
export function streamAnalysis(nicheInput, callbacks, force = false) {
  const { onStatus, onResult, onCached, onDone, onError } = callbacks;
  const controller = new AbortController();

  (async () => {
    try {
      const response = await fetch(`${API_BASE}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ niche_input: nicheInput, force }),
        signal: controller.signal,
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: "Unknown error" }));
        onError?.({ message: err.detail || "Request failed", code: "HTTP_ERROR" });
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() ?? "";

        for (const chunk of lines) {
          if (!chunk.trim()) continue;

          // Parse SSE format: "event: <name>\ndata: <json>"
          const eventMatch = chunk.match(/^event: (\w+)/m);
          const dataMatch = chunk.match(/^data: (.+)$/m);

          if (!eventMatch || !dataMatch) continue;

          const eventName = eventMatch[1];
          let data;
          try {
            data = JSON.parse(dataMatch[1]);
          } catch {
            continue;
          }

          switch (eventName) {
            case "status":
              onStatus?.(data);
              break;
            case "result":
              onResult?.(data);
              break;
            case "cached":
              onCached?.(data);
              break;
            case "done":
              onDone?.(data);
              break;
            case "error":
              onError?.(data);
              break;
          }
        }
      }
    } catch (err) {
      if (err.name !== "AbortError") {
        onError?.({ message: err.message || "Connection failed", code: "NETWORK_ERROR" });
      }
    }
  })();

  return () => controller.abort();
}

/**
 * Auth-aware API helpers (requires Supabase JWT)
 */
function authHeaders(token) {
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
  };
}

export async function saveBrief(token, nicheInput, result) {
  const res = await fetch(`${API_BASE}/briefs`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify({ niche_input: nicheInput, result }),
  });
  if (!res.ok) throw new Error("Failed to save brief");
  return res.json();
}

export async function listBriefs(token) {
  const res = await fetch(`${API_BASE}/briefs`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error("Failed to load briefs");
  return res.json();
}

export async function getBrief(id, token = null) {
  const headers = token ? authHeaders(token) : { "Content-Type": "application/json" };
  const res = await fetch(`${API_BASE}/briefs/${id}`, { headers });
  if (!res.ok) throw new Error("Brief not found");
  return res.json();
}

export async function deleteBrief(token, id) {
  const res = await fetch(`${API_BASE}/briefs/${id}`, {
    method: "DELETE",
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error("Failed to delete brief");
  return res.json();
}

export async function shareBrief(token, id) {
  const res = await fetch(`${API_BASE}/briefs/${id}/share`, {
    method: "POST",
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error("Failed to share brief");
  return res.json();
}

export async function getBriefBySlug(slug) {
  const res = await fetch(`${API_BASE}/briefs/share/${slug}`);
  if (!res.ok) throw new Error("Brief not found");
  return res.json();
}
