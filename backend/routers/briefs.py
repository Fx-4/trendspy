from fastapi import APIRouter, HTTPException, Header
from models.schemas import SaveBriefRequest
from dotenv import load_dotenv
import os, secrets, string

load_dotenv()

router = APIRouter()

_supabase_url = os.getenv("SUPABASE_URL", "")
_supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

if _supabase_url and _supabase_key:
    from supabase import create_client
    supabase = create_client(_supabase_url, _supabase_key)
else:
    supabase = None


def generate_slug(length: int = 8) -> str:
    chars = string.ascii_letters + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


def require_supabase():
    if not supabase:
        raise HTTPException(status_code=503, detail="Database not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.")


def get_user_id(authorization: str | None) -> str:
    require_supabase()
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    token = authorization.replace("Bearer ", "")
    try:
        user = supabase.auth.get_user(token)
        return user.user.id
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.post("")
async def save_brief(body: SaveBriefRequest, authorization: str | None = Header(None)):
    user_id = get_user_id(authorization)
    result = body.result
    data = {
        "user_id": user_id,
        "niche_input": body.niche_input,
        "pain_points": [p.model_dump() for p in result.pain_points],
        "competitor_gaps": [g.model_dump() for g in result.competitor_gaps],
        "pricing_signals": result.pricing_signals.model_dump() if result.pricing_signals else {},
        "hot_communities": [c.model_dump() for c in result.hot_communities],
        "ai_summary": result.ai_summary,
    }
    response = supabase.table("briefs").insert(data).execute()
    return response.data[0] if response.data else {}


@router.get("")
async def list_briefs(authorization: str | None = Header(None)):
    user_id = get_user_id(authorization)
    response = supabase.table("briefs").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
    return response.data


@router.get("/{brief_id}")
async def get_brief(brief_id: str, authorization: str | None = Header(None)):
    response = supabase.table("briefs").select("*").eq("id", brief_id).single().execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Brief not found")
    brief = response.data
    if not brief.get("is_public"):
        user_id = get_user_id(authorization)
        if brief["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
    return brief


@router.delete("/{brief_id}")
async def delete_brief(brief_id: str, authorization: str | None = Header(None)):
    user_id = get_user_id(authorization)
    supabase.table("briefs").delete().eq("id", brief_id).eq("user_id", user_id).execute()
    return {"success": True}


@router.post("/{brief_id}/share")
async def share_brief(brief_id: str, authorization: str | None = Header(None)):
    user_id = get_user_id(authorization)
    slug = generate_slug()
    response = supabase.table("briefs").update({"is_public": True, "share_slug": slug}).eq("id", brief_id).eq("user_id", user_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Brief not found")
    return {"share_slug": slug, "share_url": f"/share/{slug}"}


@router.get("/share/{slug}")
async def get_by_slug(slug: str):
    response = supabase.table("briefs").select("*").eq("share_slug", slug).eq("is_public", True).single().execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Brief not found")
    return response.data
