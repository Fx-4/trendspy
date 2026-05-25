"""
Data quality & relevance validation — shared utilities for all data sources.

Every piece of data fed to the AI must pass these checks.
Principle: community engagement = crowd-sourced truth verification.
High votes/reactions mean real users found it valuable/accurate.
"""
import re
from datetime import datetime, timezone

# ─── Spam & Low-Quality Signals ──────────────────────────────────────────────

_SPAM_PATTERNS = [
    r'\bbuy now\b', r'\bclick here\b', r'\blimited (time )?offer\b',
    r'\bdiscount\b', r'\baffiliate\b', r'\bsponsored\b', r'\bad\b',
    r'\bpromo code\b', r'\bfree trial.*sign up\b', r'\b100% (free|guaranteed)\b',
    r'\bmake money (fast|online|now)\b', r'\bpassive income\b',
]
_SPAM_RE = re.compile('|'.join(_SPAM_PATTERNS), re.IGNORECASE)

_CLICKBAIT_PATTERNS = [
    r'^\d+ (reasons|ways|tips|tricks|hacks|things)',
    r'you (won\'t believe|need to know)',
    r'the (ultimate|complete|definitive) guide',
    r'everything you need to know',
]
_CLICKBAIT_RE = re.compile('|'.join(_CLICKBAIT_PATTERNS), re.IGNORECASE)


# ─── Core Validators ─────────────────────────────────────────────────────────

def relevance_score(text: str, niche: str) -> float:
    """
    Score 0.0–1.0 how relevant text is to the niche.
    Uses keyword overlap: niche words appearing in content = relevance signal.
    """
    if not text or not niche:
        return 0.0
    niche_words = {w for w in niche.lower().split() if len(w) > 3}
    if not niche_words:
        return 0.5
    text_lower = text.lower()
    matched = sum(1 for w in niche_words if w in text_lower)
    return min(1.0, matched / len(niche_words))


def is_spam(text: str) -> bool:
    """Return True if content looks like spam or promotional material."""
    if not text:
        return False
    return bool(_SPAM_RE.search(text))


def is_clickbait(title: str) -> bool:
    """Return True if title looks like clickbait with no real signal."""
    if not title:
        return False
    return bool(_CLICKBAIT_RE.match(title.strip()))


def is_recent(iso_date: str, max_years: int = 3) -> bool:
    """Return True if the date string is within max_years of today."""
    if not iso_date:
        return True  # unknown date = don't reject
    try:
        dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        age_years = (now - dt).days / 365
        return age_years <= max_years
    except Exception:
        return True


def has_substance(text: str, min_chars: int = 60) -> bool:
    """Return True if text has enough content to be meaningful."""
    if not text:
        return False
    cleaned = text.strip()
    # Must be long enough
    if len(cleaned) < min_chars:
        return False
    # Must have actual words (not just links or code)
    word_count = len(cleaned.split())
    return word_count >= 8


# ─── Per-Item Quality Gate ────────────────────────────────────────────────────

def passes_quality_gate(
    title: str,
    content: str,
    niche: str,
    min_relevance: float = 0.2,
) -> bool:
    """
    Master quality gate for any data item.
    Returns True only if all checks pass.

    Checks:
    1. Has substance (title + content not empty/trivial)
    2. Not spam
    3. Title not pure clickbait
    4. Relevant to niche (keyword overlap)
    """
    full_text = f"{title} {content}"

    if not has_substance(title, min_chars=10):
        return False
    if is_spam(full_text):
        return False
    if is_clickbait(title):
        return False
    if relevance_score(full_text, niche) < min_relevance:
        return False

    return True


# ─── Batch Filter ────────────────────────────────────────────────────────────

def filter_items(
    items: list[dict],
    niche: str,
    title_key: str = "title",
    content_key: str = "content",
    score_key: str | None = None,
    min_score: int = 0,
    date_key: str | None = None,
    max_years: int = 3,
    min_relevance: float = 0.2,
    limit: int = 10,
) -> list[dict]:
    """
    Filter a list of dicts through the full quality pipeline:
    score threshold → recency → quality gate → relevance sort → limit.
    """
    results = []
    for item in items:
        # Score threshold
        if score_key and item.get(score_key, 0) < min_score:
            continue
        # Recency
        if date_key and not is_recent(item.get(date_key, ""), max_years):
            continue
        # Quality gate
        title = item.get(title_key, "")
        content = item.get(content_key, "")
        if not passes_quality_gate(title, content, niche, min_relevance):
            continue
        results.append(item)

    # Sort by relevance descending (most relevant first)
    results.sort(
        key=lambda x: relevance_score(
            f"{x.get(title_key, '')} {x.get(content_key, '')}", niche
        ),
        reverse=True,
    )

    return results[:limit]
